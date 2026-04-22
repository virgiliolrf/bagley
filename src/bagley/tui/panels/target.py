"""TargetPanel — right column: target, kill-chain, creds, notes. Phase 1 stub."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState


class TargetPanel(Vertical):
    DEFAULT_CSS = """
    TargetPanel { width: 32; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="target-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("[b orange3]◆ TARGET[/]\n[dim](no target)[/]", id="target-info")
        yield Static("[b orange3]◆ KILL-CHAIN[/]\n"
                      "[dim]· recon · enum · exploit · postex · privesc · persist · cleanup[/]",
                      id="killchain")
        yield Static("[b orange3]◆ CREDS[/]\n[dim](none yet)[/]", id="creds-section")
        yield Static("[b orange3]◆ NOTES[/]\n[dim](empty)[/]", id="notes-section")
