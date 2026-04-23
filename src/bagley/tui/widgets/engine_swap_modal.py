"""Ctrl+Shift+M Hot-Swap Engine Modal.

Lists available engines (local adapters, Ollama models, stub).
On selection, replaces the active engine in AppState; subsequent chat
turns are tagged [engine=<label>] automatically.
Chat history is intentionally preserved across the swap.
"""

from __future__ import annotations

from typing import Callable, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListView, ListItem

from bagley.tui.services.engine_registry import EngineEntry, EngineKind, list_engines


_KIND_ICONS = {
    EngineKind.LOCAL: "[green]*[/green]",
    EngineKind.OLLAMA: "[cyan]*[/cyan]",
    EngineKind.STUB: "[dim]*[/dim]",
}


class EngineSwapModal(ModalScreen):
    """Full-screen modal listing available inference engines."""

    DEFAULT_CSS = """
    EngineSwapModal { align: center middle; }
    EngineSwapModal > #engine-swap-modal {
        width: 60;
        height: 24;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #engine-list { height: 16; border: solid $panel; }
    """

    BINDINGS = [
        Binding("escape", "close_modal", "Close", show=True),
        Binding("enter", "select_engine", "Select", show=True),
    ]

    def __init__(
        self,
        on_select: Optional[Callable[[EngineEntry], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._on_select = on_select
        self._engines: list[EngineEntry] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="engine-swap-modal"):
            yield Label("[b]Hot-Swap Engine[/b]  (Enter to select, Esc to cancel)")
            yield ListView(id="engine-list")

    def on_mount(self) -> None:
        self._engines = list_engines()
        lv = self.query_one("#engine-list", ListView)
        for entry in self._engines:
            icon = _KIND_ICONS.get(entry.kind, "")
            lv.append(ListItem(Label(f"{icon} {entry.label}  [{entry.kind.value}]")))
        if self._engines:
            lv.index = 0
        lv.focus()

    def _select_current(self) -> None:
        try:
            lv = self.query_one("#engine-list", ListView)
        except Exception:
            self.dismiss(None)
            return
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._engines):
            chosen = self._engines[idx]
            if self._on_select:
                try:
                    self._on_select(chosen)
                except Exception:
                    pass
            self.dismiss(chosen)
        else:
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self._select_current()

    def action_select_engine(self) -> None:
        self._select_current()

    def action_close_modal(self) -> None:
        self.dismiss(None)
