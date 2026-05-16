from __future__ import annotations

from ask.config import Settings
from ask.memory import ChatMemory
from ask.models import OllamaChatBackend
from ask.plugins import PluginRegistry
from ask.rag import Retriever, augment_user_message
from ask.streaming import collect_stream_text, iter_ollama_text_deltas
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

    def _handle_slash_command(self, line: str) -> None:
        """Handle `/…` REPL commands (no LLM call)."""
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
            return
        if cmd == "/baseurl":
            if not arg:
                self._ui.print_baseurl_usage()
                return
            self._backend.set_host(arg)
            self._ui.print_ollama_host_switched(self._backend.host)
            # Auto-refresh models for the new host
            self._handle_slash_command("/models")
            return
        self._ui.print_unknown_slash(cmd)

    @staticmethod
    def _inject_memory_snippets(text: str, snippets: list[str]) -> str:
        return inject_memory_snippets(text, snippets)

    def run(self) -> None:
        self._ui.print_chat_header()
        
        # Check model availability on startup
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

        import time
        import signal

        self._last_sigint = 0.0
        self._exit_requested = False

        def sigint_handler(sig, frame):
            now = time.time()
            if now - self._last_sigint < 2.0:
                self._exit_requested = True
                # We need to print here because the exception won't be caught by the input loop immediately
                self._ui.print_session_end()
                sys.exit(0)
            else:
                self._ui.print_status("Type /quit or click Ctrl+C twice to exit")
                self._last_sigint = now

        signal.signal(signal.SIGINT, sigint_handler)

        while not self._exit_requested:
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

                base_user = self._plugins.transform_user_message(user_input)
                self._ui.print_user_transmission(base_user)

                if self._settings.rag_enabled:
                    docs = self._retriever.retrieve(base_user, top_k=self._settings.rag_top_k)
                    after_docs = augment_user_message(base_user, docs)
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
