"""TargetPanel — target info, kill-chain, creds, notes."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState

_STAGES = ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]


class TargetPanel(Vertical):
    DEFAULT_CSS = """
    TargetPanel { width: 32; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="target-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("", id="target-info")
        yield Static("", id="killchain")
        yield Static("", id="creds-section")
        yield Static("", id="notes-section")

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        tab = self._state.tabs[self._state.active_tab]
        if tab.kind == "recon":
            info = "[b orange3]◆ TARGET[/]\n[dim](no target — recon tab)[/]"
        else:
            info = f"[b orange3]◆ TARGET[/]\n[orange3]{tab.id}[/]"

        kc_lines = ["[b orange3]◆ KILL-CHAIN[/]"]
        for i, stage in enumerate(_STAGES):
            if i < tab.killchain_stage:
                kc_lines.append(f"[green]✓[/] {stage}")
            elif i == tab.killchain_stage:
                kc_lines.append(f"[orange3]▸[/] [b]{stage}[/]")
            else:
                kc_lines.append(f"[dim]·[/] [dim]{stage}[/]")

        creds = "[b orange3]◆ CREDS[/]\n"
        creds += "[dim](none yet)[/]" if not tab.creds else "\n".join(
            f"{c.get('user','?')}:{c.get('secret','?')}" for c in tab.creds
        )

        notes = "[b orange3]◆ NOTES[/]\n"
        notes += tab.notes_md or "[dim](empty)[/]"

        self.query_one("#target-info").update(info)
        self.query_one("#killchain").update("\n".join(kc_lines))
        self.query_one("#creds-section").update(creds)
        self.query_one("#notes-section").update(notes)
