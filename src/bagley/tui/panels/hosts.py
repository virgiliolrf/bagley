"""HostsPanel — left column: hosts, ports, findings. Phase 1 stub."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState


class HostsPanel(Vertical):
    DEFAULT_CSS = """
    HostsPanel { width: 28; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="hosts-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("[b orange3]◆ HOSTS[/]\n[dim](Phase 1 stub)[/]", id="hosts-section")
        yield Static("[b orange3]◆ PORTS[/]\n[dim](Phase 1 stub)[/]", id="ports-section")
        yield Static("[b orange3]◆ FINDINGS[/]\n[dim](Phase 1 stub)[/]", id="findings-section")
