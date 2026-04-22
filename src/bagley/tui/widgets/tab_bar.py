"""Tab bar with recon + per-target tabs and a + indicator."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.state import AppState


class TabBar(Static):
    DEFAULT_CSS = """
    TabBar { height: 1; padding: 0 1; background: $panel-lighten-1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="tab-bar", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        parts = []
        for i, tab in enumerate(self._state.tabs):
            label = tab.id
            if i == self._state.active_tab:
                parts.append(f"[reverse][b]{label}[/][/]")
            else:
                parts.append(f"[dim]{label}[/]")
        parts.append("[dim]+[/]")
        self.update(" │ ".join(parts))
