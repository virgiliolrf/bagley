"""Modes bar — 9 pills, active one highlighted by state.mode."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.modes import MODES
from bagley.tui.state import AppState


class ModesBar(Static):
    DEFAULT_CSS = """
    ModesBar { height: 1; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="modes-bar", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        active = self._state.mode
        pills = []
        for m in MODES:
            marker = "◉" if m.name == active else "○"
            style = f"bold {m.color}" if m.name == active else f"dim {m.color}"
            pills.append(f"[{style}]{marker} {m.index}.{m.name}[/]")
        self.update(" ".join(pills))
