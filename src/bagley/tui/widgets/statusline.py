"""Statusline footer — turn, engine, hints."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.state import AppState


class Statusline(Static):
    DEFAULT_CSS = """
    Statusline { height: 1; dock: bottom; background: $panel; color: $text-muted; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="statusline", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        s = self._state
        self.update(
            f"turn={s.turn} · engine={s.engine_label} · "
            f"[b]F1[/] help · [b]Ctrl+K[/] palette · [b]Ctrl+D[/] disconnect"
        )
