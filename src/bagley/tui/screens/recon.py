"""ReconScreen — tab-0 scope overview with subnet minimap.

Same 4-pane skeleton as DashboardScreen, but the right column is replaced
by a scope summary panel containing ProgressRings (aggregate) and Minimap.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from bagley.tui.panels.chat import ChatPanel
from bagley.tui.panels.hosts import HostsPanel
from bagley.tui.state import AppState
from bagley.tui.widgets.rings import Minimap


class ReconScopePanel(Vertical):
    """Right column for the recon tab — scope summary + subnet minimap."""

    DEFAULT_CSS = """
    ReconScopePanel { width: 32; border: solid $panel-lighten-2; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="recon-scope-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Static("[b orange3]◆ SCOPE SUMMARY[/]", id="scope-header")
        yield Static("[dim]Hosts up: 0 / 0[/]", id="scope-stats")
        yield Static("[b orange3]◆ SUBNET MAP[/]", id="minimap-header")
        yield Minimap(subnet_prefix="10.10.0")


class ReconScreen(Screen):
    """Full recon tab layout — HostsPanel | ChatPanel | ReconScopePanel."""

    DEFAULT_CSS = """
    ReconScreen { layout: vertical; }
    #recon-pane-row { height: 1fr; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    def compose(self) -> ComposeResult:
        with Horizontal(id="recon-pane-row"):
            yield HostsPanel(self._state)
            yield ChatPanel(self._state)
            yield ReconScopePanel(self._state)
