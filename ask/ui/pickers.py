from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, ListItem, Static
from textual import events

from ask.app.session_manager import _format_relative_time, SessionInfo
from ask.ui.fuzzy import fuzzy_filter_objects
from ask.ui.colors import AMBER, BEIGE, BG, DIM, PANE

if TYPE_CHECKING:
    from ask.ui.workstation import AskWorkstationApp


class PickerItem(ListItem):
    def __init__(self, label: str, value: str) -> None:
        super().__init__()
        self.picker_label = label
        self.picker_value = value


class PickerScreen(Screen):
    """Base picker screen with search and list selection."""

    CSS = f"""
PickerScreen {{
    background: rgba(0,0,0,0.85);
    align: center middle;
}}

#picker-title {{
    width: 50%;
    height: auto;
    text-align: center;
    color: {AMBER};
    bold: true;
    margin: 1 0 0 0;
}}

#picker-input {{
    width: 50%;
    height: 3;
    margin: 0 0 0 0;
    border: solid {DIM};
    background: {PANE};
    color: {BEIGE};
}}

#picker-input:focus {{
    border: solid {AMBER};
}}

#picker-results {{
    width: 50%;
    height: 50%;
    border: solid {DIM};
    background: {BG};
    overflow-y: auto;
}}

.picker-item {{
    padding: 0 1;
    color: {BEIGE};
}}

.picker-item:hover {{
    background: {DIM};
}}

.picker-item:focus {{
    background: {AMBER};
    color: {BG};
}}
"""

    BINDINGS = [
        Binding("escape", "close_picker", "Close"),
        Binding("down", "next_item", "Next", show=False),
        Binding("up", "prev_item", "Previous", show=False),
        Binding("enter", "execute_selected", "Execute", show=False),
    ]

    def __init__(
        self,
        app_ref: AskWorkstationApp,
        title: str,
        items: list[tuple[str, str]],
        callback: Any = None,
    ) -> None:
        super().__init__()
        self._app_ref = app_ref
        self._title = title
        self._all_items = items
        self._callback = callback

    def compose(self) -> ComposeResult:
        yield Static(self._title, id="picker-title")
        yield Input(placeholder="Search...", id="picker-input")
        yield VerticalScroll(id="picker-results")

    def on_mount(self) -> None:
        self.query_one("#picker-input", Input).focus()
        self._filter("")

    async def on_input_changed(self, event: Input.Changed) -> None:
        self._filter(event.value)

    def _filter(self, query: str) -> None:
        scroll = self.query_one("#picker-results", VerticalScroll)
        scroll.remove_children()
        filtered = fuzzy_filter_objects(self._all_items, query, score_cutoff=0.3, limit=30)
        for label, value, _ in filtered:
            scroll.mount(PickerItem(label, value))
        if scroll.children:
            scroll.children[0].focus()

    async def on_key(self, event: events.Key) -> None:
        if event.key == "down":
            self._move_focus(1)
            event.stop()
        elif event.key == "up":
            self._move_focus(-1)
            event.stop()

    def _move_focus(self, direction: int) -> None:
        scroll = self.query_one("#picker-results", VerticalScroll)
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
        if isinstance(item, PickerItem):
            self._select(item.picker_value)

    def action_execute_selected(self) -> None:
        focused = self.focused
        if isinstance(focused, PickerItem):
            self._select(focused.picker_value)

    def _select(self, value: str) -> None:
        self.dismiss(value)
        if self._callback:
            self._callback(value)

    def action_close_picker(self) -> None:
        self.dismiss(None)
        if self._callback:
            self._callback(None)


class SessionPicker(PickerScreen):
    def __init__(self, app_ref: AskWorkstationApp, callback: Any = None) -> None:
        sessions: list[SessionInfo] = app_ref._session_manager.list_sessions()
        items: list[tuple[str, str]] = []
        for s in sessions:
            rel = _format_relative_time(s.updated_at)
            title = s.title if s.title else "New Session"
            label = f"{title}  ({rel}, {s.message_count} msgs)"
            items.append((label, s.id))
        super().__init__(app_ref, "SWITCH SESSION", items, callback)


class ModelPicker(PickerScreen):
    def __init__(self, app_ref: AskWorkstationApp, callback: Any = None) -> None:
        items: list[tuple[str, str]] = []
        for name, size in app_ref._installed_models:
            label = f"{name}  ({size})"
            items.append((label, name))
        if not items:
            items.append(("(no models found - run Ollama or /models)", ""))
        super().__init__(app_ref, "SWITCH MODEL", items, callback)


class WorkspacePicker(PickerScreen):
    def __init__(self, app_ref: AskWorkstationApp, callback: Any = None) -> None:
        items: list[tuple[str, str]] = [("Current Directory", ".")]
        extra = getattr(app_ref, "_workspace_history", None)
        if extra:
            for w in extra:
                items.append((w, w))
        root = app_ref._file_context.project_root
        try:
            for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
                if child.is_dir() and not child.name.startswith("."):
                    items.append((child.name, child.name))
        except OSError:
            pass
        super().__init__(app_ref, "SELECT WORKSPACE", items, callback)
