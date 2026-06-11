from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, ListItem, Static
from textual import events

from ask.ui.command_catalog import COMMANDS
from ask.ui.fuzzy import fuzzy_filter_objects
from ask.ui.colors import AMBER, BEIGE, BG, DIM, PANE

if TYPE_CHECKING:
    from ask.ui.workstation import AskWorkstationApp

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
        self._all_entries: list[tuple[str, str, str, str]] = []
        self._build_entries()

    def _build_entries(self) -> None:
        self._all_entries.clear()
        for spec in COMMANDS:
            label = f"{spec.title} - {spec.description}"
            self._all_entries.append((label, spec.command, spec.category, spec.title))

        for session in self._app_ref._session_manager.list_sessions()[:20]:
            title = session.title if session.title else "New Session"
            self._all_entries.append(
                (f"{title} - {session.message_count} messages", f"/session {session.id}", "Sessions", title)
            )

        for name, size in self._app_ref._installed_models:
            self._all_entries.append((f"{name} - {size}", f"/model {name}", "Models", name))

        for path in self._workspace_files(limit=80):
            self._all_entries.append((f"{path} - read file", f"/read {path}", "Files", path))
            self._all_entries.append((f"{path} - explain file", f"/explain {path}", "Files", path))

    def _workspace_files(self, *, limit: int) -> list[str]:
        ctx = self._app_ref._file_context
        root = ctx.active_root
        files: list[str] = []
        try:
            for current, dirs, names in ctx._walk(root):
                ctx._filter_dirs(current, dirs)
                for name in sorted(names):
                    path = current / name
                    if ctx._should_skip_file(path):
                        continue
                    files.append(ctx._display_path(path))
                    if len(files) >= limit:
                        return files
        except Exception:
            return files
        return files

    def compose(self) -> ComposeResult:
        yield Static("COMMAND PALETTE", id="cp-title", classes="cp-header")
        yield Input(placeholder="Search commands...", id="cp-input")
        yield VerticalScroll(id="cp-results")

    def on_mount(self) -> None:
        self.query_one("#cp-input", Input).focus()
        self._filter("")

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
            for label, cmd, cat, title in self._all_entries:
                if cat != current_cat:
                    scroll.mount(CategoryHeader(Text(f"\n{cat}\n", style=f"bold {AMBER}")))
                    current_cat = cat
                display = self._display_line(cat, title)
                scroll.mount(PaletteItem(display, cmd, cat))
        else:
            filtered = fuzzy_filter_objects(
                [(label, cmd, cat, title) for label, cmd, cat, title in self._all_entries],
                query,
                score_cutoff=0.3,
                limit=30,
            )
            current_cat = ""
            for label, cmd, cat, title, _score in filtered:
                if cat != current_cat:
                    scroll.mount(CategoryHeader(Text(f"\n{cat}\n", style=f"bold {AMBER}")))
                    current_cat = cat
                display = self._display_line(cat, title) if cat else title
                scroll.mount(PaletteItem(display, cmd, cat))
        self._focus_first_item()

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
            self._focus_first_item()
            return
        next_idx = current_idx + direction
        while 0 <= next_idx < len(children):
            if isinstance(children[next_idx], PaletteItem):
                children[next_idx].focus()
                return
            next_idx += direction

    def _focus_first_item(self) -> None:
        scroll = self.query_one("#cp-results", VerticalScroll)
        for child in scroll.children:
            if isinstance(child, PaletteItem):
                child.focus()
                return

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
