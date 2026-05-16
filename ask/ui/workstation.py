from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.console import Group, RenderableType
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Input, Static

from ask.app.chat import inject_memory_snippets
from ask.app.session_manager import ChatSessionManager, SessionInfo, derive_session_title
from ask.config import Settings
from ask.files import (
    ContextSummary,
    FileFindResult,
    LocalFileAccessError,
    LocalFileContext,
)
from ask.memory import ChatMemory
from ask.models import OllamaChatBackend
from ask.models.router import ModelRouter
from ask.plugins import GitPlugin, PluginRegistry
from ask.rag import Retriever, augment_user_message
from ask.streaming import iter_ollama_text_deltas
from ask.tools import (
    FileAnalysisMode,
    build_file_analysis_prompt,
    build_file_read_panel,
    detect_language,
)

AMBER = "#c49a52"
GREEN = "#7f9f6b"
BEIGE = "#d6c6a8"
MUTED = "#837a62"
DIM = "#5f6b52"
BG = "#090b08"
PANE = "#10130d"
PANE_ALT = "#15170f"
ERROR = "#c16b5c"


@dataclass
class ChatLine:
    role: Literal["user", "assistant", "system"]
    content: str
    streaming: bool = False
    renderable: RenderableType | None = None


class FocusStatic(Static, can_focus=True):
    def on_focus(self) -> None:
        self.add_class("active")

    def on_blur(self) -> None:
        self.remove_class("active")


class FocusVerticalScroll(VerticalScroll, can_focus=True):
    def on_focus(self) -> None:
        self.add_class("active")

    def on_blur(self) -> None:
        self.remove_class("active")


class AskWorkstationApp(App[None]):
    """Textual shell for local AI chat without changing backend ownership."""

    CSS = f"""
    Screen {{
        background: {BG};
        color: {BEIGE};
    }}

    #topbar {{
        dock: top;
        height: 1;
        background: {PANE_ALT};
        color: {AMBER};
        content-align: left middle;
        padding: 0 1;
    }}

    #workspace {{
        height: 1fr;
    }}

    .pane {{
        height: 100%;
        background: {PANE};
        color: {BEIGE};
        border: solid {DIM};
        padding: 0 1;
    }}

    .pane.active {{
        border: solid {AMBER};
    }}

    #sessions-pane {{
        width: 31;
    }}

    #chat-pane {{
        width: 1fr;
    }}

    #settings-pane {{
        width: 36;
    }}

    #chat-content {{
        width: 100%;
    }}

    #status-bar {{
        dock: bottom;
        height: 1;
        background: {PANE_ALT};
        color: {GREEN};
        padding: 0 1;
    }}

    #command-input {{
        dock: bottom;
        height: 3;
        background: {BG};
        color: {BEIGE};
        border-top: solid {DIM};
        border-bottom: none;
        border-left: none;
        border-right: none;
        padding: 0 1;
    }}

    #command-input:focus {{
        border-top: solid {AMBER};
    }}
    """

    BINDINGS = [
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+s", "save_session", "Save Session"),
        Binding("ctrl+y", "copy_last_response", "Copy Last Response"),
        Binding("tab", "focus_next_pane", "Switch Pane"),
        Binding("ctrl+c", "quit", "Exit"),
    ]

    TITLE = "ask.ai workstation"
    SUB_TITLE = "local neural shell"
    ENABLE_COMMAND_PALETTE = False

    def __init__(
        self,
        *,
        settings: Settings,
        backend: OllamaChatBackend,
        session_manager: ChatSessionManager,
        file_context: LocalFileContext,
        retriever: Retriever,
        plugins: PluginRegistry,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._backend = backend
        self._session_manager = session_manager
        self._file_context = file_context
        self._retriever = retriever
        self._plugins = plugins
        self._active_chat_model = settings.chat_model
        self._memory: ChatMemory | None = None
        self._session_id = "default"
        self._chat_lines: list[ChatLine] = []
        self._displayed_sessions: list[SessionInfo] = []
        self._installed_models: list[tuple[str, str]] = []
        self._ollama_status = "checking"
        self._ollama_error: str | None = None
        self._streaming = False
        self._status_message = "ready"
        self._focus_order = ["sessions-pane", "chat-pane", "settings-pane", "command-input"]
        self._focus_index = 3
        self._router = ModelRouter(
            enabled=settings.router_enabled,
            default_model=settings.router_default_model,
            coding_model=settings.router_coding_model,
            chat_model=settings.router_chat_model,
            summary_model=settings.router_summary_model,
        )
        self._git = GitPlugin(max_diff_lines=settings.git_max_diff_lines)

    def compose(self) -> ComposeResult:
        yield Static("ASK.AI // LOCAL WORKSTATION // OLLAMA TERMINAL OS", id="topbar")
        with Horizontal(id="workspace"):
            yield FocusStatic(id="sessions-pane", classes="pane")
            with FocusVerticalScroll(id="chat-pane", classes="pane"):
                yield Static(id="chat-content")
            yield FocusStatic(id="settings-pane", classes="pane")
        yield Static(id="status-bar")
        yield Input(
            placeholder="command or message  /read  /explain  /summarize  /review",
            id="command-input",
        )

    def on_mount(self) -> None:
        self._session_id = self._session_manager.initial_session_id()
        self._open_session(self._session_id, announce=False)
        self.query_one("#command-input", Input).focus()
        self._refresh_ollama_status()
        self.set_interval(30, self._refresh_ollama_status)

    def on_unmount(self) -> None:
        lines = self._format_exit_transcript()
        self._close_current_memory()
        out = sys.__stdout__
        try:
            out.write("\n")
            for line in lines:
                out.write(line)
            out.write("\n")
            out.flush()
        except OSError:
            pass

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        self.query_one("#command-input", Input).value = ""
        if not value:
            return
        if value.startswith("/"):
            self._handle_command(value)
            return
        self._submit_user_message(value)

    def action_focus_next_pane(self) -> None:
        self._focus_index = (self._focus_index + 1) % len(self._focus_order)
        widget_id = self._focus_order[self._focus_index]
        self.query_one(f"#{widget_id}").focus()

    def action_new_session(self) -> None:
        if self._streaming:
            self._notice("stream active; finish current response before creating a session")
            return
        session = self._session_manager.create_session()
        self._open_session(session.id, announce=True)

    def action_save_session(self) -> None:
        self._save_current_session()

    def _handle_command(self, command_line: str) -> None:
        parts = command_line.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command in ("/help", "/?"):
            self._add_system_line(
                "\n".join(
                    [
                        "── workspace ──",
                        "/workspace <dir>   load project folder as context",
                        "/context           show current context summary",
                        "/clear-context     clear loaded workspace context",
                        "/read <file>       display raw file with syntax highlighting",
                        "/explain <file>    explain file architecture and logic",
                        "/summarize <file>  short file overview",
                        "/review <file>     code review for risks and improvements",
                        "/find <pattern>    search active context and attach matches",
                        "── git ──",
                        "/git-status        show working tree status",
                        "/git-diff [file]   show unstaged diff",
                        "/git-log [n]       show recent commits (default: 10)",
                        "/explain-commit    AI explanation of staged changes",
                        "/generate-commit   AI-generated commit message from diff",
                        "── sessions ──",
                        "/new               create a new session",
                        "/save [title]      mark current session saved",
                        "/sessions          list saved sessions",
                        "/session <id|num>  switch to a session",
                        "/resume <id|num>   alias for /session",
                        "/clear             clear current session transcript",
                        "── export ──",
                        "/save-file <path>  save last response to a file",
                        "/export            export full session as markdown",
                        "/copy              copy last AI response to clipboard",
                        "/print             print last response to terminal (selectable)",
                        "── model ──",
                        "/model <name>      switch active Ollama model",
                        "/models            refresh installed model list",
                        "keys: Ctrl+N new, Ctrl+S save, Ctrl+Y copy, Tab panes, Ctrl+C exit",
                    ]
                )
            )
            return
        if command == "/model":
            if not arg:
                self._add_system_line(f"current model: {self._active_chat_model}")
                return
            self._active_chat_model = arg
            self._status_message = f"model switched to {arg}"
            self._refresh_status()
            self._refresh_settings()
            return
        if command == "/models":
            self._add_system_line("refreshing Ollama model list")
            self._refresh_ollama_status()
            return
        if command == "/new":
            self.action_new_session()
            return
        if command == "/save":
            self._save_current_session(title=arg or None)
            return
        if command == "/sessions":
            self._add_system_line("\n".join(self._format_session_lines()))
            return
        if command == "/session":
            if not arg:
                self._add_system_line("usage: /session <id|number>")
                return
            self._switch_session_from_arg(arg)
            return
        if command in ("/context", "/workspace"):
            self._handle_context_command(arg)
            return
        if command in ("/clear-context", "/clear-workspace"):
            self._file_context.clear()
            self._add_system_line("workspace context cleared")
            return
        if command == "/read":
            self._handle_read_command(arg)
            return
        if command == "/explain":
            self._handle_file_analysis_command("explain", arg)
            return
        if command == "/summarize":
            self._handle_file_analysis_command("summarize", arg)
            return
        if command == "/review":
            self._handle_file_analysis_command("review", arg)
            return
        if command == "/find":
            self._handle_find_command(arg)
            return
        if command == "/git-status":
            self._handle_git_status()
            return
        if command == "/git-diff":
            self._handle_git_diff(arg)
            return
        if command == "/git-log":
            self._handle_git_log(arg)
            return
        if command == "/explain-commit":
            self._handle_git_explain_commit()
            return
        if command == "/generate-commit":
            self._handle_git_generate_commit()
            return
        if command in ("/save-file", "/save-response"):
            self._handle_save_response(arg)
            return
        if command == "/export":
            self._handle_export_session()
            return
        if command == "/resume":
            if not arg:
                self._add_system_line("usage: /resume <id|number>")
                return
            self._switch_session_from_arg(arg)
            return
        if command == "/clear":
            if self._memory is not None:
                self._memory.clear()
            self._chat_lines.clear()
            self._status_message = "session transcript cleared"
            self._refresh_all()
            return
        if command in ("/copy", "/copy-last"):
            self.action_copy_last_response()
            return
        if command == "/print":
            self._print_last_response()
            return
        self._add_system_line(f"unknown command: {command}")

    def _handle_git_status(self) -> None:
        if not self._settings.git_enabled:
            self._notice("git integration is disabled in config")
            return
        if not self._git.is_available:
            self._notice("git is not installed on this system")
            return
        try:
            out = self._git.status()
        except Exception as exc:
            self._notice(f"git status failed: {exc}")
            return
        self._add_system_line("working tree status:" if out else "clean working tree")
        if out:
            self._add_system_line(out)

    def _handle_git_diff(self, pathspec: str) -> None:
        if not self._settings.git_enabled:
            self._notice("git integration is disabled in config")
            return
        if not self._git.is_available:
            self._notice("git is not installed on this system")
            return
        try:
            out = self._git.diff(pathspec=pathspec or None)
        except Exception as exc:
            self._notice(f"git diff failed: {exc}")
            return
        self._add_system_line("diff:" if out else "no unstaged changes")
        if out:
            self._add_system_line(out)

    def _handle_git_log(self, arg: str) -> None:
        if not self._settings.git_enabled:
            self._notice("git integration is disabled in config")
            return
        try:
            n = int(arg) if arg.isdigit() and int(arg) > 0 else 10
            out = self._git.log_pretty(max_count=n)
        except Exception as exc:
            self._notice(f"git log failed: {exc}")
            return
        self._add_system_line("recent commits:" if out else "no commits found")
        if out:
            self._add_system_line(out)

    def _handle_git_explain_commit(self) -> None:
        if self._streaming:
            self._notice("stream active; wait for the assistant to finish")
            return
        if not self._settings.git_enabled:
            self._notice("git integration is disabled in config")
            return
        try:
            diff_text = self._git.diff(staged=True, pathspec=None)
        except Exception as exc:
            diff_text = ""
            self._notice(f"git diff failed: {exc}")
        if not diff_text or diff_text == "no unstaged changes":
            try:
                diff_text = self._git.diff(staged=False, pathspec=None)
            except Exception as exc:
                self._notice(f"no staged changes and unstaged diff failed: {exc}")
                return
            if not diff_text or diff_text == "no unstaged changes":
                self._notice("no changes to explain")
                return
        prompt = (
            "Explain the following code changes in a concise way. "
            "Describe what each change does and why it might be needed.\n\n"
            f"```diff\n{diff_text}\n```"
        )
        self._submit_file_analysis(
            user_label="explain-commit",
            prompt=prompt,
            status="explaining git changes …",
        )

    def _handle_git_generate_commit(self) -> None:
        if self._streaming:
            self._notice("stream active; wait for the assistant to finish")
            return
        if not self._settings.git_enabled:
            self._notice("git integration is disabled in config")
            return
        try:
            diff_text = self._git.diff(staged=False, pathspec=None)
        except Exception as exc:
            self._notice(f"git diff failed: {exc}")
            return
        if not diff_text or diff_text == "no unstaged changes":
            self._notice("no unstaged changes to commit")
            return
        prompt = (
            "Generate a concise git commit message based on the following diff. "
            "Use conventional commits format (type: description). "
            "Keep the message under 72 characters.\n\n"
            f"```diff\n{diff_text}\n```"
        )
        self._submit_file_analysis(
            user_label="generate-commit",
            prompt=prompt,
            status="generating commit message …",
        )

    def _handle_save_response(self, arg: str) -> None:
        if not arg:
            self._notice("usage: /save-file <path>")
            return
        last = self._last_assistant_response()
        if last is None:
            self._notice("no completed assistant response to save")
            return
        path = Path(arg).expanduser().resolve()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(last, encoding="utf-8")
        except OSError as exc:
            self._notice(f"save failed: {exc}")
            return
        self._notice(f"saved {len(last)} chars to {path}")

    def _handle_export_session(self) -> None:
        lines: list[str] = []
        lines.append("# ask.ai session transcript\n\n")
        for line in self._chat_lines:
            if line.role == "user":
                lines.append(f"## User\n\n{line.content}\n\n")
            elif line.role == "assistant" and line.content:
                lines.append(f"## Assistant\n\n{line.content}\n\n")
            elif line.role == "system" and line.content:
                lines.append(f"> {line.content}\n\n")
        text = "".join(lines)
        path = Path.cwd() / f"ask-export-{self._session_id}.md"
        try:
            path.write_text(text, encoding="utf-8")
        except OSError as exc:
            self._notice(f"export failed: {exc}")
            return
        self._notice(f"exported {len(lines)} messages to {path.name}")

    def _handle_context_command(self, arg: str) -> None:
        try:
            summary = self._file_context.set_context(arg) if arg else self._file_context.summarize()
        except LocalFileAccessError as exc:
            self._notice(f"context denied: {exc}")
            return
        self._add_system_line(self._format_context_summary(summary))

    def _handle_read_command(self, arg: str) -> None:
        try:
            result = self._file_context.read_file(arg)
        except LocalFileAccessError as exc:
            self._notice(f"read denied: {exc}")
            return
        self._add_system_line(
            f"read-only file: {result.display_path}",
            renderable=build_file_read_panel(result),
        )

    def _handle_file_analysis_command(self, mode: FileAnalysisMode, arg: str) -> None:
        if self._streaming:
            self._notice("stream active; wait for the assistant to finish")
            return
        try:
            result = self._file_context.read_file(arg)
        except LocalFileAccessError as exc:
            self._notice(f"{mode} denied: {exc}")
            return
        language = detect_language(result.path)
        suffix = " [truncated]" if result.truncated else ""
        self._submit_file_analysis(
            user_label=f"{mode} {result.display_path}",
            prompt=build_file_analysis_prompt(result, mode),
            status=f"{mode}: {result.display_path} ({language}){suffix}",
        )

    def _handle_find_command(self, arg: str) -> None:
        try:
            result = self._file_context.find(arg)
        except LocalFileAccessError as exc:
            self._notice(f"find denied: {exc}")
            return
        self._add_system_line(self._format_find_result(result))

    def _submit_user_message(self, text: str) -> None:
        if self._streaming:
            self._notice("stream active; wait for the assistant to finish")
            return
        if self._memory is None:
            self._notice("no active memory store")
            return

        base_user = self._plugins.transform_user_message(text)
        task_model = self._router.select_model(base_user, current_model=self._active_chat_model)
        if task_model != self._active_chat_model and self._router.enabled:
            self._active_chat_model = task_model
            self._status_message = f"routed to {task_model}"
        self._chat_lines.append(ChatLine(role="user", content=base_user))
        self._chat_lines.append(ChatLine(role="assistant", content="", streaming=True))
        assistant_index = len(self._chat_lines) - 1
        local_file_context = self._file_context.prompt_context()
        self._streaming = True
        if self._status_message == "streaming":
            self._status_message = "streaming"
        self._refresh_all()

        thread = threading.Thread(
            target=self._stream_response_worker,
            args=(base_user, assistant_index, self._session_id, self._memory, local_file_context),
            daemon=True,
        )
        thread.start()

    def _submit_file_analysis(self, *, user_label: str, prompt: str, status: str) -> None:
        if self._memory is None:
            self._notice("no active memory store")
            return

        self._chat_lines.append(ChatLine(role="user", content=user_label))
        self._chat_lines.append(ChatLine(role="assistant", content="", streaming=True))
        assistant_index = len(self._chat_lines) - 1
        self._streaming = True
        self._status_message = status
        self._refresh_all()

        thread = threading.Thread(
            target=self._stream_direct_prompt_worker,
            args=(prompt, assistant_index, self._session_id, self._memory, user_label),
            daemon=True,
        )
        thread.start()

    def _stream_response_worker(
        self,
        base_user: str,
        assistant_index: int,
        session_id: str,
        memory: ChatMemory,
        local_file_context: str | None,
    ) -> None:
        try:
            if self._settings.rag_enabled:
                docs = self._retriever.retrieve(base_user, top_k=self._settings.rag_top_k)
                after_docs = augment_user_message(base_user, docs)
            else:
                after_docs = base_user

            if local_file_context:
                after_docs = f"{local_file_context}\n\n---\n\n{after_docs}"

            snippets: list[str] = []
            if self._settings.memory_context_search_enabled:
                snippets = memory.retrieve_context_snippets(
                    base_user,
                    top_k=self._settings.memory_context_search_top_k,
                )

            turn_user = inject_memory_snippets(after_docs, snippets)
            api_messages = list(memory.get())
            api_messages.append({"role": "user", "content": turn_user})

            stream = self._backend.chat(
                model=self._active_chat_model,
                messages=api_messages,
                stream=True,
            )

            full: list[str] = []
            for delta in iter_ollama_text_deltas(stream):
                full.append(delta)
                self.call_from_thread(self._append_assistant_delta, assistant_index, delta)

            response_text = "".join(full)
            memory.append({"role": "user", "content": base_user})
            memory.append({"role": "assistant", "content": response_text})
            self._plugins.notify_assistant(response_text)
            self._session_manager.touch_ram_session(session_id)
            self.call_from_thread(self._finish_stream, assistant_index, None)
        except Exception as exc:
            self.call_from_thread(self._finish_stream, assistant_index, str(exc))

    def _stream_direct_prompt_worker(
        self,
        prompt: str,
        assistant_index: int,
        session_id: str,
        memory: ChatMemory,
        memory_user_content: str,
    ) -> None:
        try:
            api_messages = list(memory.get())
            api_messages.append({"role": "user", "content": prompt})

            stream = self._backend.chat(
                model=self._active_chat_model,
                messages=api_messages,
                stream=True,
            )

            full: list[str] = []
            for delta in iter_ollama_text_deltas(stream):
                full.append(delta)
                self.call_from_thread(self._append_assistant_delta, assistant_index, delta)

            response_text = "".join(full)
            memory.append({"role": "user", "content": memory_user_content})
            memory.append({"role": "assistant", "content": response_text})
            self._plugins.notify_assistant(response_text)
            self._session_manager.touch_ram_session(session_id)
            self.call_from_thread(self._finish_stream, assistant_index, None)
        except Exception as exc:
            self.call_from_thread(self._finish_stream, assistant_index, str(exc))

    def _append_assistant_delta(self, index: int, delta: str) -> None:
        if index >= len(self._chat_lines):
            return
        line = self._chat_lines[index]
        if line.role != "assistant":
            return
        line.content += delta
        self._refresh_chat()

    def _finish_stream(self, index: int, error: str | None) -> None:
        if index < len(self._chat_lines):
            self._chat_lines[index].streaming = False
            if error:
                self._chat_lines[index].content = f"local backend error: {error}"
        self._streaming = False
        self._status_message = "error" if error else "ready"
        if error:
            self._ollama_status = "error"
            self._ollama_error = error
        self._refresh_all()
        if not error and index < len(self._chat_lines):
            text = self._chat_lines[index].content
            if text:
                self.call_after_refresh(self._write_to_scrollback, text)

    def _open_session(self, session_id: str, *, announce: bool) -> None:
        self._close_current_memory()
        self._session_id = session_id
        self._memory = self._session_manager.memory_for(session_id)
        self._chat_lines = [
            ChatLine(role=message["role"], content=message["content"])
            for message in self._memory.get()
        ]
        if announce:
            self._add_system_line(f"session opened: {session_id}")
        self._status_message = f"session {session_id}"
        self._refresh_all()

    def _switch_session_from_arg(self, arg: str) -> None:
        if self._streaming:
            self._notice("stream active; finish current response before switching sessions")
            return
        session_id = arg
        if arg.isdigit():
            index = int(arg) - 1
            if 0 <= index < len(self._displayed_sessions):
                session_id = self._displayed_sessions[index].id
        known = {session.id for session in self._session_manager.list_sessions()}
        if session_id not in known:
            self._notice(f"session not found: {arg}")
            return
        self._open_session(session_id, announce=True)

    def _save_current_session(self, *, title: str | None = None) -> None:
        if self._streaming:
            self._notice("stream active; finish current response before saving")
            return
        label = title or self._title_from_current_session()
        try:
            session = self._session_manager.save_session(self._session_id, title=label)
        except Exception as exc:
            self._notice(f"save failed: {exc}")
            return
        self._status_message = f"saved {session.title}"
        self._refresh_all()

    def _title_from_current_session(self) -> str:
        for line in self._chat_lines:
            if line.role == "user":
                return derive_session_title(line.content)
        for session in self._session_manager.list_sessions():
            if session.id == self._session_id:
                return session.title
        return "Untitled Session"

    def _close_current_memory(self) -> None:
        if self._memory is None:
            return
        close = getattr(self._memory, "close", None)
        if callable(close):
            close()
        self._memory = None

    def _refresh_ollama_status(self) -> None:
        self._ollama_status = "checking"
        self._ollama_error = None
        self._refresh_status()
        thread = threading.Thread(target=self._ollama_status_worker, daemon=True)
        thread.start()

    def _ollama_status_worker(self) -> None:
        try:
            rows = self._backend.list_installed_models()
            self.call_from_thread(self._set_ollama_status, "online", None, rows)
        except Exception as exc:
            self.call_from_thread(self._set_ollama_status, "offline", str(exc), [])

    def _set_ollama_status(
        self,
        status: str,
        error: str | None,
        models: list[tuple[str, str]],
    ) -> None:
        self._ollama_status = status
        self._ollama_error = error
        self._installed_models = models
        self._refresh_status()
        self._refresh_settings()

    def _notice(self, message: str) -> None:
        self._status_message = message
        self._add_system_line(message)

    def _add_system_line(self, message: str, *, renderable: RenderableType | None = None) -> None:
        self._chat_lines.append(ChatLine(role="system", content=message, renderable=renderable))
        self._refresh_all()

    def _refresh_all(self) -> None:
        self._refresh_sessions()
        self._refresh_chat()
        self._refresh_settings()
        self._refresh_status()

    def _refresh_sessions(self) -> None:
        self._displayed_sessions = self._session_manager.list_sessions()
        self.query_one("#sessions-pane", Static).update(self._render_sessions())

    def _refresh_chat(self) -> None:
        self.query_one("#chat-content", Static).update(self._render_chat())
        self.call_after_refresh(self._scroll_chat_end)

    def _scroll_chat_end(self) -> None:
        self.query_one("#chat-pane", FocusVerticalScroll).scroll_end(animate=False)

    def _refresh_settings(self) -> None:
        self.query_one("#settings-pane", Static).update(self._render_settings())

    def _refresh_status(self) -> None:
        self.query_one("#status-bar", Static).update(self._render_status())

    def _render_sessions(self) -> RenderableType:
        lines = Text()
        lines.append("SESSIONS / HISTORY\n", style=f"bold {AMBER}")
        lines.append("Ctrl+N new  Ctrl+S save\n\n", style=MUTED)
        if not self._displayed_sessions:
            lines.append("no sessions\n", style=MUTED)
        for index, session in enumerate(self._displayed_sessions[:12], start=1):
            active = ">" if session.id == self._session_id else " "
            saved = "S" if session.saved_at else "."
            style = AMBER if session.id == self._session_id else BEIGE
            lines.append(f"{active}{index:02d} [{saved}] {session.title}\n", style=style)
            lines.append(f"    {session.message_count} msgs  {session.id}\n", style=MUTED)

        recent = [line for line in self._chat_lines if line.role != "system"][-5:]
        lines.append("\nCURRENT TRACE\n", style=f"bold {GREEN}")
        if not recent:
            lines.append("empty session\n", style=MUTED)
        for line in recent:
            label = "you" if line.role == "user" else "ai"
            preview = self._one_line(line.content, limit=28)
            lines.append(f"{label:>3}: {preview}\n", style=MUTED)
        return lines

    def _render_chat(self) -> RenderableType:
        if not self._chat_lines:
            return Text(
                "No transcript loaded. Type a message or use /help.",
                style=MUTED,
            )

        blocks: list[RenderableType] = []
        for line in self._chat_lines:
            if line.role == "user":
                blocks.append(Text("OPERATOR\n", style=f"bold {AMBER}"))
                blocks.append(Text(f"{line.content}\n", style=BEIGE))
            elif line.role == "assistant":
                suffix = " [stream]" if line.streaming else ""
                blocks.append(Text(f"ASK.AI{suffix}\n", style=f"bold {GREEN}"))
                body = line.content or "..."
                blocks.append(Markdown(body))
            else:
                blocks.append(Text("SYSTEM\n", style=f"bold {MUTED}"))
                if line.renderable is not None:
                    blocks.append(line.renderable)
                else:
                    blocks.append(Text(f"{line.content}\n", style=MUTED))
            blocks.append(Text("\n--\n", style=DIM))
        return Group(*blocks)

    def _render_settings(self) -> RenderableType:
        table = Table.grid(expand=True)
        table.add_column(ratio=1)
        table.add_column(ratio=2)
        table.add_row(Text("SETTINGS", style=f"bold {AMBER}"), Text(""))
        table.add_row(Text("model", style=MUTED), Text(self._active_chat_model, style=GREEN))
        table.add_row(Text("memory", style=MUTED), Text(self._memory_label(), style=BEIGE))
        table.add_row(Text("stream", style=MUTED), Text("active" if self._streaming else "idle", style=GREEN))
        table.add_row(Text("ollama", style=MUTED), Text(self._ollama_label(), style=self._ollama_style()))
        table.add_row(Text("host", style=MUTED), Text(self._settings.ollama_host, style=BEIGE))
        table.add_row(Text("session", style=MUTED), Text(self._session_id, style=BEIGE))
        table.add_row(Text("router", style=MUTED), Text("on" if self._router.enabled else "off", style=GREEN if self._router.enabled else MUTED))
        git_label = "on" if self._settings.git_enabled else "off"
        git_style = GREEN if self._settings.git_enabled else MUTED
        table.add_row(Text("git", style=MUTED), Text(git_label, style=git_style))
        table.add_row(Text("files", style=MUTED), Text(self._file_context.status_label(), style=BEIGE))

        commands = Text()
        commands.append("\nCOMMANDS\n", style=f"bold {AMBER}")
        commands.append(
            "/workspace <dir>\n/model <name>\n/git-status\n/git-diff\n/git-log\n/save-file <path>\n/export\n",
            style=BEIGE,
        )

        models = Text()
        models.append("\nLOCAL MODELS\n", style=f"bold {GREEN}")
        if self._installed_models:
            for name, size in self._installed_models[:10]:
                marker = ">" if self._model_matches_active(name) else " "
                models.append(f"{marker} {name}  {size}\n", style=BEIGE if marker == ">" else MUTED)
        elif self._ollama_error:
            models.append(self._one_line(self._ollama_error, limit=48), style=ERROR)
        else:
            models.append("checking local manifest\n", style=MUTED)

        return Group(table, commands, models)

    def _render_status(self) -> RenderableType:
        memory = self._memory_label()
        stream = "STREAM:ON" if self._streaming else "STREAM:IDLE"
        git_avail = "GIT" if self._git.is_available and self._settings.git_enabled else ""
        return Text.assemble(
            ("MODEL ", MUTED),
            (self._active_chat_model, GREEN),
            ("  |  MEMORY ", MUTED),
            (memory, BEIGE),
            ("  |  ", MUTED),
            (stream, AMBER if self._streaming else GREEN),
            ("  |  OLLAMA ", MUTED),
            (self._ollama_status.upper(), self._ollama_style()),
            ("  |  CTX ", MUTED),
            (self._file_context.active_root_label, BEIGE),
            (f"  |  {git_avail} ", GREEN) if git_avail else Text(""),
            ("  |  ", MUTED),
            (self._status_message, BEIGE),
        )

    def _format_session_lines(self) -> list[str]:
        lines = ["sessions:"]
        for index, session in enumerate(self._session_manager.list_sessions(), start=1):
            active = "*" if session.id == self._session_id else " "
            saved = "saved" if session.saved_at else "open"
            lines.append(f"{active} {index}. {session.id}  {session.title}  {saved}")
        return lines

    def _memory_label(self) -> str:
        if self._settings.memory_persist_path:
            return f"SQLITE {Path(self._settings.memory_persist_path).expanduser().name}"
        return "RAM"

    @staticmethod
    def _format_context_summary(summary: ContextSummary) -> str:
        lines = [
            f"context: {summary.root_label}",
            f"readable files: {summary.file_count}",
            f"ignored directories: {summary.ignored_dir_count}",
        ]
        if summary.sample_paths:
            lines.append("sample files:")
            lines.extend(f"- {path}" for path in summary.sample_paths[:12])
        return "\n".join(lines)

    def _format_find_result(result: FileFindResult) -> str:
        lines = [
            f"find: {result.pattern}",
            f"context: {result.root_label}",
            f"scanned files: {result.scanned_files}",
            f"skipped files: {result.skipped_files}",
            f"matches: {len(result.matches)}",
        ]
        if result.matches:
            lines.append("results:")
            for match in result.matches[:24]:
                lines.append(f"{match.path}:{match.line_number}: {match.line}")
        if result.truncated:
            lines.append("[results truncated]")
        return "\n".join(lines)

    def _ollama_label(self) -> str:
        if self._ollama_status == "offline" and self._ollama_error:
            return "offline"
        return self._ollama_status

    def _ollama_style(self) -> str:
        if self._ollama_status == "online":
            return GREEN
        if self._ollama_status in {"offline", "error"}:
            return ERROR
        return AMBER

    def _model_matches_active(self, name: str) -> bool:
        return name == self._active_chat_model or name.split(":", 1)[0] == self._active_chat_model.split(":", 1)[0]

    def action_copy_last_response(self) -> None:
        last = self._last_assistant_response()
        if last is None:
            self._notice("no assistant response to copy")
            return
        if self._copy_to_clipboard(last):
            self._notice(f"copied {len(last)} chars to clipboard")
        else:
            self._notice("clipboard not available; use /print instead")

    def _format_exit_transcript(self) -> list[str]:
        lines: list[str] = []
        lines.append("── ask.ai transcript ──\n")
        for line in self._chat_lines:
            if line.role == "user":
                lines.append(f"\n>>> {line.content}\n")
            elif line.role == "assistant" and line.content:
                lines.append(f"\n{line.content}\n")
            elif line.role == "system" and line.content:
                lines.append(f"\n# {line.content}\n")
        lines.append("── end transcript ──\n")
        return lines

    def _last_assistant_response(self) -> str | None:
        for line in reversed(self._chat_lines):
            if line.role == "assistant" and line.content and not line.streaming:
                return line.content
        return None

    def _print_last_response(self) -> None:
        last = self._last_assistant_response()
        if last is None:
            self._notice("no completed assistant response to print")
            return
        self._write_to_scrollback(last)
        self._notice(f"printed {len(last)} chars to terminal scrollback")

    @staticmethod
    def _write_to_scrollback(text: str) -> None:
        out = sys.__stdout__
        try:
            out.write("\033[?47l")
            out.flush()
            out.write("\n")
            out.write(text)
            if not text.endswith("\n"):
                out.write("\n")
            out.write("\033[?47h")
            out.flush()
        except OSError:
            pass

    @staticmethod
    def _copy_to_clipboard(text: str) -> bool:
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except ImportError:
            pass
        try:
            if shutil.which("xclip"):
                proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                proc.communicate(text.encode("utf-8"))
                if proc.returncode == 0:
                    return True
        except OSError:
            pass
        try:
            if shutil.which("wl-copy"):
                proc = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                proc.communicate(text.encode("utf-8"))
                if proc.returncode == 0:
                    return True
        except OSError:
            pass
        try:
            if shutil.which("pbcopy"):
                proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                proc.communicate(text.encode("utf-8"))
                if proc.returncode == 0:
                    return True
        except OSError:
            pass
        try:
            if shutil.which("clip"):
                proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                proc.communicate(text.encode("utf-8"))
                return proc.returncode == 0
        except OSError:
            pass
        return False

    @staticmethod
    def _one_line(text: str, *, limit: int) -> str:
        clean = " ".join(text.split())
        if len(clean) <= limit:
            return clean
        return clean[: max(0, limit - 3)] + "..."
