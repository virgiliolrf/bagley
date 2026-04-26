"""TargetPanel — target info, kill-chain, creds, notes."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState

_STAGES = ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]


class TargetPanel(Vertical):
    DEFAULT_CSS = """
    TargetPanel { width: 32; border: solid $panel-lighten-2; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="target-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        from bagley.tui.widgets.rings import ProgressRings
        from bagley.tui.panels.notes_editor import NotesEditor
        yield Static("[b orange3]◆ TARGET[/]\n[dim](no target)[/]", id="target-info")
        yield Static("[b orange3]◆ KILL-CHAIN[/]", id="killchain-header")
        stage = (self._state.tabs[self._state.active_tab].killchain_stage
                 if self._state.tabs else 0)
        yield ProgressRings(stage=stage)
        yield Static("[b orange3]◆ CREDS[/]\n[dim](none yet)[/]", id="creds-section")
        yield NotesEditor(self._state)

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        if not self._state.tabs:
            return
        tab = self._state.tabs[self._state.active_tab]
        if tab.kind == "recon":
            info = "[b orange3]◆ TARGET[/]\n[dim](no target — recon tab)[/]"
        else:
            info = f"[b orange3]◆ TARGET[/]\n[orange3]{tab.id}[/]"

        creds = "[b orange3]◆ CREDS[/]\n"
        creds += "[dim](none yet)[/]" if not tab.creds else "\n".join(
            f"{c.get('user','?')}:{c.get('secret','?')}" for c in tab.creds
        )

        try:
            self.query_one("#target-info").update(info)
        except Exception:
            pass
        # Update ProgressRings stage
        try:
            from bagley.tui.widgets.rings import ProgressRings
            self.query_one(ProgressRings).refresh_stage(tab.killchain_stage)
        except Exception:
            pass
        try:
            self.query_one("#creds-section").update(creds)
        except Exception:
            pass
