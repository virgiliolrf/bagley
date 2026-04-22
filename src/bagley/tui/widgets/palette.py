"""Command palette (Ctrl+K) — fuzzy action list."""

from __future__ import annotations

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static


ACTIONS: list[tuple[str, str]] = [
    ("new tab", "new_tab"),
    ("close tab", "close_tab"),
    ("focus hosts", "focus('#hosts-panel')"),
    ("focus chat", "focus('#chat-panel')"),
    ("focus target", "focus('#target-panel')"),
    ("disconnect", "disconnect"),
]


class CommandPalette(ModalScreen):
    DEFAULT_CSS = """
    CommandPalette { align: center middle; }
    #palette { width: 60; height: auto; border: round $primary;
                background: $panel; padding: 1 1; }
    #palette-results { height: auto; max-height: 10; }
    """

    def compose(self):
        with Vertical(id="palette"):
            yield Input(placeholder="type action…", id="palette-input")
            yield ListView(id="palette-results")

    def on_mount(self) -> None:
        self._refresh("")
        self.query_one("#palette-input").focus()

    def _refresh(self, query: str) -> None:
        lv = self.query_one("#palette-results", ListView)
        lv.clear()
        q = query.lower().strip()
        for label, _ in ACTIONS:
            if q in label:
                lv.append(ListItem(Static(label)))

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.lower().strip()
        for label, action in ACTIONS:
            if q in label:
                self.dismiss(action)
                return
        self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
