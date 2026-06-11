from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, Static
from textual import events

from ask.app.session_manager import _format_relative_time
from ask.ui.colors import AMBER, BEIGE, BG, DIM, GREEN, MUTED, PANE, PANE_ALT

if TYPE_CHECKING:
    from ask.ui.workstation import AskWorkstationApp

_TIPS = [
    "Type /workspace <dir> to inject code architecture into the AI context.",
    "Use /explain <file> to get AI analysis of source code.",
    "Ctrl+N starts a new session; Ctrl+S saves the current one.",
    "Type /git-review to have AI review your uncommitted changes.",
    "Use /find <pattern> to search files in your active workspace.",
    "Prefix a message with / to access commands, without / to chat.",
    "Tab switches between panes: sessions, chat, settings, input.",
    "Use /model <name> to switch between installed Ollama models.",
    "The router auto-selects the best model for each coding task.",
    "Use /history <query> to search past conversations.",
    "Type /export to save your session as a Markdown file.",
    "Resume any past session with /session <id|title>.",
    "The RAG system indexes your codebase for smarter answers.",
    "Use /save to bookmark a session with a meaningful title.",
]

LOGO_ASCII = """               / \\   / ___|| |/ / / \\  |_ _|
              / _ \\  \\___ \\| ' / / _ \\  | |
             / ___ \\  ___) | . \\/ ___ \\ | |
            /_/   \\_\\|____/|_|\\_\\_/   \\_\\___|"""


class HomeScreen(Screen):
    """Startup landing page with logo, quick actions, sessions, and prompt line."""

    CSS = f"""
HomeScreen {{
    background: {BG};
    layout: vertical;
    overflow-y: auto;
}}

#home-logo {{
    width: 100%;
    height: auto;
    text-align: left;
    margin: 1 0 0 4;
}}

#home-status {{
    width: 100%;
    height: auto;
    text-align: left;
    margin: 0 0 0 4;
}}

#home-columns {{
    width: 100%;
    height: auto;
    align: left top;
    margin: 1 0 0 2;
}}

.home-col {{
    width: 46%;
    height: auto;
    margin: 0 1;
}}

.col-header {{
    width: 100%;
    height: auto;
    text-align: left;
    margin: 0 0 0 0;
}}

.col-box {{
    width: 100%;
    height: auto;
    border: none;
    background: {PANE};
    padding: 0 1;
}}

.col-box:focus-within {{
    background: {PANE_ALT};
}}

#home-tip {{
    width: 100%;
    height: auto;
    content-align: center middle;
    margin: 1 0 0 0;
}}

#home-prompt-bar {{
    width: 100%;
    height: auto;
    content-align: center middle;
    margin: 1 0 0 0;
    padding: 0 0;
}}

#home-footer {{
    width: 100%;
    height: auto;
    content-align: center middle;
    margin: 0 0 1 0;
}}
"""

    BINDINGS = [
        Binding("ctrl+p", "open_command_palette", "Command Palette"),
        Binding("ctrl+n", "new_session", "New Session"),
        Binding("ctrl+s", "save_session", "Save Session"),
        Binding("escape", "dismiss_home", "Start Chatting"),
        Binding("ctrl+c", "quit", "Exit"),
        Binding("tab", "cycle_focus", "Cycle Focus"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._focus_pane = 0
        self._digit_buffer = ""

    def compose(self) -> ComposeResult:
        yield Static(id="home-logo")
        yield Static(id="home-status")
        with Horizontal(id="home-columns"):
            with Vertical(id="home-quick-col", classes="home-col"):
                yield Static(id="home-quick-header", classes="col-header")
                yield Static(id="home-quick-box", classes="col-box")
            with Vertical(id="home-sessions-col", classes="home-col"):
                yield Static(id="home-sessions-header", classes="col-header")
                yield Static(id="home-sessions-box", classes="col-box")
        yield Static(id="home-tip")
        yield Static(id="home-prompt-bar")
        yield Static(id="home-footer")

    def on_mount(self) -> None:
        self._render_logo()
        self._render_status()
        self._render_quick_actions()
        self._render_sessions()
        self._render_tip()
        self._render_prompt()
        self._render_footer()
        self._tip_timer = self.set_interval(15, self._rotate_tip)
        self._update_focus_highlight()

    def _render_logo(self) -> None:
        self.query_one("#home-logo", Static).update(
            Text(LOGO_ASCII, style=f"bold {AMBER}")
        )

    def _render_status(self) -> None:
        app: AskWorkstationApp = self.app  # type: ignore
        from ask import __version__ as ver_mod
        v = getattr(ver_mod, "__version__", "0.1.0")
        model = getattr(app, "_active_chat_model", "Ollama (Auto)")
        ctx = "None"
        if hasattr(app, "_file_context") and app._file_context.active_root:
            ctx = str(app._file_context.active_root)
        line = f"LOCAL NEURAL SHELL  v{v}  |  Model: {model}  |  Context: {ctx}"
        self.query_one("#home-status", Static).update(
            Text(f"  {line}\n", style=MUTED)
        )

    def _render_quick_actions(self) -> None:
        header = self.query_one("#home-quick-header", Static)
        header.update(Text("QUICK ACTIONS\n", style=f"bold {GREEN}"))

        lines = ["─" * 40]
        actions = [
            ("w", "Load Current Workspace Context", "/workspace ."),
            ("g", "Run AI Git Review on Changes", "/git-review"),
            ("m", "Change Active Ollama Model", "/models"),
            ("n", "Open Fresh Chat Session", "/new"),
        ]
        for key, desc, _ in actions:
            lines.append(f"[{key}] {desc}")
        lines.append("")

        self.query_one("#home-quick-box", Static).update(
            Text("\n".join(lines), style=BEIGE)
        )

    def _render_sessions(self) -> None:
        app: AskWorkstationApp = self.app  # type: ignore
        header = self.query_one("#home-sessions-header", Static)
        header.update(Text("RECENT SESSIONS (Type # to switch)\n", style=f"bold {GREEN}"))

        sessions = []
        if hasattr(app, "_session_manager"):
            sessions = app._session_manager.list_sessions()[:8]

        lines = ["─" * 42]
        if not sessions:
            lines.append("  (no sessions yet)")
        else:
            for idx, s in enumerate(sessions, start=1):
                rel = _format_relative_time(s.updated_at)
                title = s.title if s.title else "New Session"
                lines.append(f"[{idx}] {title}  ({rel})")
        lines.append("")

        self.query_one("#home-sessions-box", Static).update(
            Text("\n".join(lines), style=BEIGE)
        )

    def _render_tip(self) -> None:
        tip = random.choice(_TIPS)
        self.query_one("#home-tip", Static).update(
            Text(f"  \U0001f4a1 Tip: {tip}", style=MUTED)
        )

    def _rotate_tip(self) -> None:
        self._render_tip()

    def _render_prompt(self) -> None:
        bar = "─" * 74
        self.query_one("#home-prompt-bar", Static).update(
            Text(f"  \n  (ASKAI) \u276f Type a prompt or a slash command...\n  {bar}", style=BEIGE)
        )

    def _render_footer(self) -> None:
        self.query_one("#home-footer", Static).update(
            Text(
                "  keys: Ctrl+N new, Ctrl+S save, Ctrl+Y copy, Tab panes, Ctrl+C exit",
                style=MUTED,
            )
        )

    def _update_focus_highlight(self) -> None:
        quick_box = self.query_one("#home-quick-box", Static)
        sessions_box = self.query_one("#home-sessions-box", Static)

        if self._focus_pane == 1:
            quick_box.styles.background = PANE_ALT
            quick_box.styles.border = ("solid", AMBER)
        else:
            quick_box.styles.background = PANE
            quick_box.styles.border = None

        if self._focus_pane == 2:
            sessions_box.styles.background = PANE_ALT
            sessions_box.styles.border = ("solid", AMBER)
        else:
            sessions_box.styles.background = PANE
            sessions_box.styles.border = None

    async def on_key(self, event: events.Key) -> None:
        key = event.key

        if key == "escape":
            self.action_dismiss_home()
            event.stop()
            return

        if key == "ctrl+c":
            self.app.exit()
            event.stop()
            return

        if key == "ctrl+p":
            self.action_open_command_palette()
            event.stop()
            return

        if key in ("ctrl+n",):
            self._dismiss_and_run_command("/new")
            event.stop()
            return

        if key in ("ctrl+s",):
            self._dismiss_and_run_command("/save")
            event.stop()
            return

        if key == "tab":
            self._focus_pane = (self._focus_pane + 1) % 3
            self._update_focus_highlight()
            event.stop()
            return

        if key in ("up", "down"):
            event.stop()
            return

        if key == "slash":
            self.action_open_command_palette()
            event.stop()
            return

        if key == "enter":
            self.action_dismiss_home()
            event.stop()
            return

        if key.isdigit():
            self._handle_digit(key)
            event.stop()
            return

        if key == "shift+3":
            self._handle_hash()
            event.stop()
            return

        if key == "w":
            self._dismiss_and_run_command("/workspace .")
            event.stop()
            return
        if key == "g":
            self._dismiss_and_run_command("/git-review")
            event.stop()
            return
        if key == "m":
            self._dismiss_and_run_command("/models")
            event.stop()
            return
        if key == "n":
            self._dismiss_and_run_command("/new")
            event.stop()
            return

        if len(key) == 1:
            self._dismiss_and_type(key)
            event.stop()
            return

    def _handle_digit(self, digit: str) -> None:
        self._digit_buffer += digit
        try:
            num = int(self._digit_buffer)
            app: AskWorkstationApp = self.app  # type: ignore
            sessions = app._session_manager.list_sessions()
            if 1 <= num <= len(sessions):
                target = sessions[num - 1]
                self._dismiss_and_run_command(f"/session {target.id}")
            else:
                self._digit_buffer = ""
        except (ValueError, IndexError):
            self._digit_buffer = ""

    def _handle_hash(self) -> None:
        app: AskWorkstationApp = self.app  # type: ignore
        sessions = app._session_manager.list_sessions()
        if not sessions:
            return
        lines_to_show = []
        for idx, s in enumerate(sessions[:8], start=1):
            rel = _format_relative_time(s.updated_at)
            title = s.title if s.title else "New Session"
            lines_to_show.append(f"  [{idx}] {title}  ({rel})")
        if len(sessions) > 8:
            lines_to_show.append(f"  ... and {len(sessions) - 8} more")
        self.query_one("#home-tip", Static).update(
            Text("Type a number to switch session:\n" + "\n".join(lines_to_show), style=AMBER)
        )

    def action_dismiss_home(self) -> None:
        self._do_dismiss()

    def _do_dismiss(self, prefix: str = "") -> None:
        app = self.app
        app.pop_screen()
        try:
            inp = app.query_one("#command-input", Input)
            if prefix:
                inp.value = prefix
            inp.focus()
        except Exception:
            pass

    def _dismiss_and_run_command(self, command: str) -> None:
        app = self.app
        app.pop_screen()
        try:
            inp = app.query_one("#command-input", Input)
            inp.value = command
            inp.focus()
        except Exception:
            pass

    def _dismiss_and_type(self, char: str) -> None:
        self._do_dismiss(prefix=char)

    def action_open_command_palette(self) -> None:
        from ask.ui.ask_command_palette import CommandPalette
        app = self.app
        app.pop_screen()
        def on_palette_dismissed(result: str | None) -> None:
            if result:
                inp = app.query_one("#command-input", Input)
                inp.value = result
                inp.focus()
        app.push_screen(CommandPalette(app), on_palette_dismissed)

    def action_new_session(self) -> None:
        self._dismiss_and_run_command("/new")

    def action_save_session(self) -> None:
        self._dismiss_and_run_command("/save")

    def action_cycle_focus(self) -> None:
        self._focus_pane = (self._focus_pane + 1) % 3
        self._update_focus_highlight()
