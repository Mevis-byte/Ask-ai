from __future__ import annotations

import dataclasses
import sys

from ask.config import Settings, save_user_settings
from ask.memory import ChatMemory
from ask.models import OllamaChatBackend
from ask.plugins import PluginRegistry
from ask.rag import Retriever, augment_user_message
from ask.rag.injection import augment_with_structural_context
from ask.streaming import collect_stream_text, iter_ollama_text_deltas
from ask.tools.scanner import build_dependency_graph, format_dependency_context, scan_project
from ask.tools.memory_tracker import ContextTracker
from ask.ui import ConsoleUI


def inject_memory_snippets(text: str, snippets: list[str]) -> str:
    if not snippets:
        return text
    block = "Relevant prior conversation (retrieved):\n" + "\n---\n".join(snippets)
    return f"{block}\n\n---\n\n{text}"


class ChatApplication:
    """Wires config, memory, RAG, plugins, streaming, and UI into a REPL."""

    def __init__(
        self,
        *,
        settings: Settings,
        ui: ConsoleUI,
        backend: OllamaChatBackend,
        memory: ChatMemory,
        retriever: Retriever,
        plugins: PluginRegistry,
    ) -> None:
        self._settings = settings
        self._ui = ui
        self._backend = backend
        self._memory = memory
        self._retriever = retriever
        self._plugins = plugins
        self._active_chat_model = settings.chat_model
        self._context_tracker = ContextTracker()
        self._dependency_graph = None

    def _handle_slash_command(self, line: str) -> None:
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/help", "/?"):
            self._ui.print_slash_commands_help()
            return
        if cmd == "/models":
            try:
                rows = self._backend.list_installed_models()
            except Exception as exc:
                self._ui.print_ollama_list_error(str(exc))
                return
            if not rows:
                self._ui.print_models_empty()
            else:
                self._ui.print_models_catalog(rows, self._active_chat_model)
            return
        if cmd == "/model":
            if not arg:
                self._ui.print_model_usage(self._active_chat_model)
                return
            self._active_chat_model = arg
            self._ui.print_model_switched(self._active_chat_model)

            updated = dataclasses.replace(self._settings, chat_model=arg)
            save_user_settings(updated)

            self._memory.set_metadata({"chat_model": arg})
            return
        if cmd == "/baseurl":
            if not arg:
                self._ui.print_baseurl_usage()
                return
            self._backend.set_host(arg)
            self._ui.print_ollama_host_switched(self._backend.host)

            updated = dataclasses.replace(self._settings, ollama_host=self._backend.host)
            save_user_settings(updated)

            self._handle_slash_command("/models")
            return
        self._ui.print_unknown_slash(cmd)

    @staticmethod
    def _inject_memory_snippets(text: str, snippets: list[str]) -> str:
        return inject_memory_snippets(text, snippets)

    def run(self) -> None:
        self._ui.print_chat_header()

        meta = self._memory.get_metadata()
        if "chat_model" in meta:
            self._active_chat_model = str(meta["chat_model"])

        try:
            available = self._backend.list_installed_models()
        except Exception as exc:
            self._ui.print_ollama_list_error(str(exc))
            available = []

        if not available:
            self._ui.print_models_empty()
        elif not any(m[0] == self._active_chat_model for m in available):
            self._ui.print_model_selection_prompt(available)
            idx = self._ui.prompt_model_choice(len(available))
            self._active_chat_model = available[idx - 1][0]
            self._ui.print_model_switched(self._active_chat_model)

        import signal
        import time

        last_sigint = 0.0
        exit_requested = False

        def sigint_handler(sig, frame):
            nonlocal last_sigint, exit_requested
            now = time.time()
            if now - last_sigint < 2.0:
                exit_requested = True
                self._ui.print_session_end()
                sys.exit(0)
            else:
                self._ui.print_status("Type /quit or click Ctrl+C twice to exit")
                last_sigint = now

        signal.signal(signal.SIGINT, sigint_handler)

        # Auto-detect if there's a project in the current directory
        import os
        from pathlib import Path
        try:
            cwd = Path.cwd()
            git_dir = cwd / ".git"
            if git_dir.is_dir() or any(cwd.iterdir()) if cwd.is_dir() else False:
                self._ui.print_status("Scanning project directory...")
                proj = scan_project(cwd)
                if proj.total_files > 0:
                    self._dependency_graph = build_dependency_graph(cwd)
                    self._context_tracker.set_workspace(
                        root=str(cwd),
                        languages=list(proj.languages.keys()),
                        frameworks=proj.frameworks,
                    )
                    self._ui.print_status(
                        f"Auto-detected project: {proj.total_files} files, "
                        f"{', '.join(list(proj.languages.keys())[:4])}"
                    )
        except Exception:
            pass

        while not exit_requested:
            try:
                self._ui.print_session_status_bar(active_chat_model=self._active_chat_model)
                user_input = self._ui.prompt_user_line()

                if user_input.lower() in ("exit", "/quit", "quit"):
                    self._ui.print_session_end()
                    break

                if user_input.startswith("/"):
                    self._handle_slash_command(user_input)
                    continue

                if not user_input:
                    continue

                self._context_tracker.track_topic(user_input[:80])

                base_user = self._plugins.transform_user_message(user_input)
                self._ui.print_user_transmission(base_user)

                dep_context = ""
                if self._dependency_graph:
                    words = set(base_user.lower().split())
                    related_parts: list[str] = []
                    for f in self._dependency_graph.all_files():
                        path_words = set(f.lower().replace("/", " ").replace("\\", " ").replace(".", " ").split())
                        if words & path_words:
                            ctx = format_dependency_context(self._dependency_graph, f)
                            if ctx:
                                related_parts.append(ctx)
                    dep_context = "\n".join(related_parts[:3])

                session_ctx = self._context_tracker.get_session_context() or ""

                if self._settings.rag_enabled:
                    docs = self._retriever.retrieve(base_user, top_k=self._settings.rag_top_k)
                    after_docs = augment_with_structural_context(
                        base_user, docs,
                        dependency_context=dep_context or None,
                        session_context=session_ctx or None,
                    )
                else:
                    after_docs = base_user

                snippets: list[str] = []
                if self._settings.memory_context_search_enabled:
                    snippets = self._memory.retrieve_context_snippets(
                        base_user,
                        top_k=self._settings.memory_context_search_top_k,
                    )

                turn_user = self._inject_memory_snippets(after_docs, snippets)

                history = self._memory.get()
                api_messages = list(history)
                api_messages.append({"role": "user", "content": turn_user})

                self._ui.print_response_label()

                stream = self._backend.chat(
                    model=self._active_chat_model,
                    messages=api_messages,
                    stream=True,
                )

                if self._settings.chat_live_stream:
                    full = self._ui.stream_markdown_live(iter_ollama_text_deltas(stream))
                else:
                    with self._ui.thinking("BUFFERING RESPONSE …"):
                        full = collect_stream_text(stream)
                    self._ui.print_plain(full)

                self._memory.append({"role": "user", "content": base_user})
                self._memory.append({"role": "assistant", "content": full})
                self._plugins.notify_assistant(full)

            except KeyboardInterrupt:
                now = time.time()
                if now - last_sigint < 2.0:
                    self._ui.print_session_end()
                    break
                self._ui.print_status("Type /quit or click Ctrl+C twice to exit")
                last_sigint = now
