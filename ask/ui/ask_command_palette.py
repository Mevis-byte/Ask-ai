from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, ListItem, Static
from textual import events

from ask.ui.fuzzy import fuzzy_filter_objects
from ask.ui.colors import AMBER, BEIGE, BG, DIM, ERROR, PANE

if TYPE_CHECKING:
    from ask.ui.workstation import AskWorkstationApp

_COMMAND_CATEGORIES: list[tuple[str, list[tuple[str, str]]]] = [
    ("Workspace", [
        ("Analyze Workspace", "/workspace ."),
        ("Show Context", "/context"),
        ("Clear Context", "/clear-context"),
        ("Read File <file>", "/read "),
        ("Find in Files <pattern>", "/find "),
    ]),
    ("Git", [
        ("Git Status", "/git-status"),
        ("Git Diff [file]", "/git-diff"),
        ("Git Log [n]", "/git-log"),
        ("Git Review", "/git-review"),
        ("Explain Commit", "/explain-commit"),
        ("Generate Commit Message", "/generate-commit"),
    ]),
    ("Sessions", [
        ("New Session", "/new"),
        ("Save Session [title]", "/save"),
        ("List Sessions", "/sessions"),
        ("Session History <query>", "/history"),
        ("Clear Session", "/clear"),
    ]),
    ("Models", [
        ("Switch Model <name>", "/model "),
        ("List Models", "/models"),
        ("Set Ollama Host <url>", "/baseurl "),
    ]),
    ("Export", [
        ("Save Response to File <path>", "/save-file "),
        ("Export Session as Markdown", "/export"),
        ("Copy Last Response", "/copy"),
        ("Print to Terminal", "/print"),
    ]),
    ("Files", [
        ("Explain File <file>", "/explain "),
        ("Summarize File <file>", "/summarize "),
        ("Review File <file>", "/review "),
    ]),
]


class PaletteItem(ListItem):
    def __init__(self, label: str, command: str, category: str) -> None:
        super().__init__()
        self.palette_label = label
        self.palette_command = command
        self.palette_category = category


class CategoryHeader(Static):
    pass


class CommandPalette(Screen):
    """Modal command palette with fuzzy search and keyboard navigation."""

    CSS = f"""
CommandPalette {{
    background: rgba(0,0,0,0.85);
    align: center middle;
}}

#cp-title {{
    width: 60%;
    height: auto;
    text-align: center;
    color: {AMBER};
    bold: true;
    margin: 1 0 0 0;
}}

#cp-input {{
    width: 60%;
    height: 3;
    margin: 0 0 0 0;
    border: solid {DIM};
    background: {PANE};
    color: {BEIGE};
}}

#cp-input:focus {{
    border: solid {AMBER};
}}

#cp-results {{
    width: 60%;
    height: 60%;
    border: solid {DIM};
    background: {BG};
    overflow-y: auto;
}}

#cp-results ListItem {{
    padding: 0 1;
    color: {BEIGE};
}}

#cp-results ListItem:hover {{
    background: {DIM};
}}

#cp-results ListItem:focus {{
    background: {AMBER};
    color: {BG};
}}
"""

    BINDINGS = [
        Binding("escape", "close_palette", "Close"),
        Binding("down", "next_item", "Next", show=False),
        Binding("up", "prev_item", "Previous", show=False),
        Binding("enter", "execute_selected", "Execute", show=False),
    ]

    def __init__(self, app_ref: AskWorkstationApp) -> None:
        super().__init__()
        self._app_ref = app_ref
        self._all_entries: list[tuple[str, str, str]] = []
        self._build_entries()

    def _build_entries(self) -> None:
        for cat, items in _COMMAND_CATEGORIES:
            for label, cmd in items:
                self._all_entries.append((label, cmd, cat))

    def compose(self) -> ComposeResult:
        yield Static("COMMAND PALETTE", id="cp-title", classes="cp-header")
        yield Input(placeholder="Search commands...", id="cp-input")
        yield VerticalScroll(id="cp-results")

    def on_mount(self) -> None:
        self.query_one("#cp-input", Input).focus()

    async def on_input_changed(self, event: Input.Changed) -> None:
        self._filter(event.value)

    @staticmethod
    def _display_line(category: str, label: str) -> str:
        return f"[{category}] {label}"

    def _filter(self, query: str) -> None:
        scroll = self.query_one("#cp-results", VerticalScroll)
        scroll.remove_children()
        if not query:
            current_cat = ""
            for cat, items in _COMMAND_CATEGORIES:
                if cat != current_cat:
                    scroll.mount(CategoryHeader(Text(f"\n{cat}\n", style=f"bold {AMBER}")))
                    current_cat = cat
                for label, cmd in items:
                    display = self._display_line(cat, label)
                    scroll.mount(PaletteItem(display, cmd, cat))
        else:
            filtered = fuzzy_filter_objects(
                [(label, cmd) for label, cmd, _ in self._all_entries],
                query,
                score_cutoff=0.3,
                limit=30,
            )
            current_cat = ""
            for label, cmd, _ in filtered:
                cat = self._find_category(cmd)
                if cat != current_cat:
                    scroll.mount(CategoryHeader(Text(f"\n{cat}\n", style=f"bold {AMBER}")))
                    current_cat = cat
                display = self._display_line(cat, label) if cat else label
                scroll.mount(PaletteItem(display, cmd, cat))
        if scroll.children:
            scroll.children[0].focus()

    def _find_category(self, command: str) -> str:
        for label, cmd, cat in self._all_entries:
            if cmd == command:
                return cat
        return ""

    async def on_key(self, event: events.Key) -> None:
        if event.key == "down":
            self._move_focus(1)
            event.stop()
        elif event.key == "up":
            self._move_focus(-1)
            event.stop()

    def _move_focus(self, direction: int) -> None:
        scroll = self.query_one("#cp-results", VerticalScroll)
        children = list(scroll.children)
        if not children:
            return
        current = self.focused
        current_idx = -1
        for i, child in enumerate(children):
            if child is current:
                current_idx = i
                break
        if current_idx < 0:
            children[0].focus()
            return
        next_idx = current_idx + direction
        if 0 <= next_idx < len(children):
            children[next_idx].focus()

    async def on_list_item_selected(self, event: ListItem.Selected) -> None:
        item = event.item
        if isinstance(item, PaletteItem):
            self._execute(item.palette_command)

    def action_execute_selected(self) -> None:
        focused = self.focused
        if isinstance(focused, PaletteItem):
            self._execute(focused.palette_command)

    def _execute(self, command: str) -> None:
        if command.endswith(" "):
            stripped = command.rstrip()
            self.dismiss(stripped + " ")
        else:
            self.dismiss(command)

    def action_close_palette(self) -> None:
        self.dismiss(None)
