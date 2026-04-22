"""DashboardScreen — 4-pane layout for a tab."""

from __future__ import annotations

from textual.containers import Horizontal
from textual.screen import Screen

from bagley.tui.panels.chat import ChatPanel
from bagley.tui.panels.hosts import HostsPanel
from bagley.tui.panels.target import TargetPanel
from bagley.tui.state import AppState


class DashboardScreen(Screen):
    DEFAULT_CSS = """
    DashboardScreen { layout: vertical; }
    #pane-row { height: 1fr; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    def compose(self):
        with Horizontal(id="pane-row"):
            yield HostsPanel(self._state)
            yield ChatPanel(self._state)
            yield TargetPanel(self._state)
