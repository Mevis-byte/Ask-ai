from __future__ import annotations

import sys
import time
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from pyfiglet import Figlet
from rich import print as rprint
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from ask.config import Settings
from ask.ui import theme as T


class ConsoleUI:
    """Cyberpunk-styled terminal: panels, status strip, Rich markdown, typing cadence."""

    def __init__(self, settings: Settings, console: Console | None = None) -> None:
        self._settings = settings
        self._console = console or Console()

    def play_startup_animation(self) -> None:
        if self._settings.ui_startup_animation:
            from ask.ui.startup import play_startup_animation as run_boot

            run_boot(self._console, self._settings)

    def print_banner(self, title: str | None = None, subtitle: str | None = None) -> None:
        title = title if title is not None else self._settings.ui_banner_title
        subtitle = subtitle if subtitle is not None else self._settings.ui_banner_subtitle
        try:
            ascii_art = Figlet(font=self._settings.ui_banner_font).renderText(title)
        except Exception:
            ascii_art = title + "\n"
        sub = f"[bold {T.CYAN}]{subtitle}[/]" if subtitle else ""
        self._console.print(
            Panel(
                Text(ascii_art, style=f"bold {T.MAGENTA}"),
                title=f"[{T.TITLE}]◆ ASK AI[/]",
                border_style=T.CYAN,
                subtitle=sub,
                padding=(0, 2),
            )
        )

    def print_hint(self, text: str | None = None) -> None:
        text = text if text is not None else self._settings.ui_exit_hint
        self._console.print(
            Panel(
                Text(text, style=f"italic {T.CYAN}"),
                border_style=T.MAGENTA,
                title=f"[{T.TITLE}]HINT[/]",
                padding=(0, 1),
            )
        )

    def print_status(self, text: str) -> None:
        self._console.print(
            Panel(
                Text(text, style=T.DIM),
                border_style=T.DIM,
                title=f"[{T.DIM}]SYS[/]",
                padding=(0, 1),
            )
        )

    def print_chat_header(self) -> None:
        self._console.print(
            Rule(f"[bold {T.CYAN}]══ {self._settings.ui_chat_header} ══[/]", style=T.BORDER)
        )
        self._console.print(
            Panel(
                Text("local session · /model · /models · /help · exit", justify="center", style=T.DIM),
                border_style=T.MAGENTA,
                padding=(0, 2),
            )
        )

    def print_session_status_bar(self, *, active_chat_model: str | None = None) -> None:
        mem = "SQLITE" if self._settings.memory_persist_path else "RAM"
        mem_tail = ""
        if self._settings.memory_persist_path:
            mem_tail = f" `{Path(self._settings.memory_persist_path).name}`"
        rag = "RAG ON" if self._settings.rag_enabled else "RAG —"
        host = self._settings.ollama_host.replace("http://", "").replace("https://", "")[:36]
        model_label = active_chat_model if active_chat_model is not None else self._settings.chat_model
        line = Text.assemble(
            (" ● ", f"bold {T.STATUS_ON}"),
            ("STANDBY", T.STATUS_ON),
            ("   │   ", T.STATUS_DIM),
            ("MODEL ", T.STATUS_DIM),
            (model_label, f"bold {T.CYAN}"),
            ("   │   ", T.STATUS_DIM),
            ("MEM ", T.STATUS_DIM),
            (mem, f"bold {T.YELLOW}"),
            (mem_tail, T.DIM),
            ("   │   ", T.STATUS_DIM),
            (rag, f"bold {T.GREEN}" if self._settings.rag_enabled else T.STATUS_DIM),
            ("   │   ", T.STATUS_DIM),
            (host, T.CYAN),
        )
        self._console.print(
            Panel(
                line,
                border_style=T.BORDER,
                title=f"[{T.TITLE}]◆ STATUS[/]",
                padding=(0, 1),
            )
        )

    @staticmethod
    def _model_row_matches_active(name: str, active: str) -> bool:
        if name == active:
            return True
        return name.split(":", 1)[0] == active.split(":", 1)[0]

    def print_models_catalog(self, models: list[tuple[str, str]], active: str) -> None:
        table = Table(show_lines=True, border_style=T.CYAN, expand=True, pad_edge=False)
        table.add_column("", width=2, style=T.GREEN, justify="center")
        table.add_column("Model", style=T.CYAN, no_wrap=False, ratio=2)
        table.add_column("Size", style=T.DIM, justify="right")
        for name, size_h in models:
            on = self._model_row_matches_active(name, active)
            mark = "◀" if on else ""
            name_style = f"bold {T.GREEN}" if on else T.CYAN
            table.add_row(mark, Text(name, style=name_style), size_h)
        self._console.print(
            Panel(
                table,
                title=f"[{T.TITLE}]◆ LOCAL MODEL MANIFEST[/]",
                border_style=T.BORDER,
                padding=(0, 1),
            )
        )

    def print_models_empty(self) -> None:
        self._console.print(
            Panel(
                Text("No local models reported. Install with: ollama pull <name>", style=T.DIM),
                title=f"[{T.TITLE}]◆ /models[/]",
                border_style=T.YELLOW,
                padding=(0, 1),
            )
        )

    def print_model_switched(self, name: str) -> None:
        self._console.print(
            Panel(
                Text(f"Active chat model: {name}", style=f"bold {T.CYAN}"),
                title=f"[{T.TITLE}]◆ /model[/]",
                border_style=T.GREEN,
                padding=(0, 1),
            )
        )

    def print_model_usage(self, current: str) -> None:
        self._console.print(
            Panel(
                Text.from_markup(
                    f"[{T.DIM}]Current model:[/] [bold {T.CYAN}]{current}[/]\n"
                    f"[{T.DIM}]Set model:[/] [bold {T.MAGENTA}]/model[/] [italic cyan]name[/]\n"
                    f"[dim]Example:[/] [cyan]/model llama3[/]  [dim]or[/]  [cyan]/model mistral:latest[/]"
                ),
                title=f"[{T.TITLE}]◆ /model[/]",
                border_style=T.YELLOW,
                padding=(0, 1),
            )
        )

    def print_slash_commands_help(self) -> None:
        self._console.print(
            Panel(
                Text.from_markup(
                    f"[bold {T.MAGENTA}]/models[/]     [dim]—[/]  List installed Ollama models\n"
                    f"[bold {T.MAGENTA}]/model[/] [cyan]name[/]  [dim]—[/]  Switch chat model (e.g. [cyan]llama3[/])\n"
                    f"[bold {T.MAGENTA}]/help[/]      [dim]—[/]  Show this panel\n"
                    f"[bold {T.DIM}]exit[/]          [dim]—[/]  End session"
                ),
                title=f"[{T.TITLE}]◆ SLASH COMMANDS[/]",
                border_style=T.CYAN,
                padding=(0, 1),
            )
        )

    def print_unknown_slash(self, command: str) -> None:
        self._console.print(
            Panel(
                Text(f"Unknown command: {command}", style=T.RED),
                subtitle=Text("Try /help for a list of commands.", style=T.DIM),
                title=f"[{T.TITLE}]◆ ERROR[/]",
                border_style=T.RED,
                padding=(0, 1),
            )
        )

    def print_ollama_list_error(self, message: str) -> None:
        self._console.print(
            Panel(
                Text(message, style=T.RED),
                subtitle=Text("Is Ollama running? Check ASK_OLLAMA_HOST / config.", style=T.DIM),
                title=f"[{T.TITLE}]◆ /models FAILED[/]",
                border_style=T.RED,
                padding=(0, 1),
            )
        )

    def prompt_user_line(self) -> str:
        return Prompt.ask(
            f"[bold {T.MAGENTA}]OPERATOR[/] [dim]│[/] [bold {T.CYAN}]›[/] ",
            default="",
            show_default=False,
            console=self._console,
        ).strip()

    def print_user_transmission(self, text: str) -> None:
        show = text if len(text) <= 600 else text[:597] + "…"
        self._console.print(
            Panel(
                Text(show, style=T.WHITE),
                title=f"[bold {T.YELLOW}]◀ UPLINK PAYLOAD[/]",
                border_style=T.YELLOW,
                padding=(0, 1),
            )
        )

    def print_session_end(self) -> None:
        self._console.print(
            Panel(
                Text("SESSION TERMINATED · NEURAL LINK CLOSED", justify="center", style=f"italic {T.DIM}"),
                title=f"[{T.TITLE}]◆ OFFLINE[/]",
                border_style=T.MAGENTA,
                padding=(0, 1),
            )
        )

    def print_response_label(self) -> None:
        if not self._settings.ui_show_response_label:
            return
        label = self._settings.ui_response_label
        self._console.print(
            Rule(f"[bold {T.MAGENTA}]▶ {label}[/]", characters="═─", style=T.MAGENTA)
        )

    def print_markdown(self, text: str) -> None:
        self._console.print(
            Panel(
                Markdown(text),
                title=f"[{T.TITLE}]◆ OUTPUT[/]",
                border_style=T.CYAN,
                padding=(1, 2),
            )
        )

    def stream_markdown_live(self, text_deltas: Iterable[str]) -> str:
        buffer: list[str] = []
        delay = max(0.0, self._settings.ui_typing_delay_ms / 1000.0)

        for delta in text_deltas:
            if delay <= 0:
                sys.stdout.write(delta)
                buffer.append(delta)
            else:
                for ch in delta:
                    sys.stdout.write(ch)
                    buffer.append(ch)
                    time.sleep(delay)
            sys.stdout.flush()

        sys.stdout.write("\n")
        sys.stdout.flush()

        return "".join(buffer)

    def print_plain(self, text: str, *, end: str = "\n") -> None:
        self._console.print(text, end=end, highlight=False)

    @contextmanager
    def thinking(self, message: str = "NEURAL UPLINK · awaiting tokens") -> Iterator[None]:
        with self._console.status(
            f"[bold {T.CYAN}]{message}[/]",
            spinner="dots12",
            spinner_style=T.MAGENTA,
        ):
            yield

    @staticmethod
    def rich_print(message: str) -> None:
        rprint(message)
