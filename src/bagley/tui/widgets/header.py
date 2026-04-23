"""Header widget - OS, scope, mode, voice, alerts badge."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from bagley.tui.services.voice import VoiceState
from bagley.tui.state import AppState
from bagley.tui.widgets.voice_badge import VoiceBadge


class Header(Static):
    DEFAULT_CSS = """
    Header { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="header", **kwargs)
        self._state = state

    def compose(self) -> ComposeResult:
        yield VoiceBadge()

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        s = self._state
        scope = ",".join(s.scope_cidrs) or "<none>"
        self.update(
            f"[b]Bagley[/] - os={s.os_info.system} - scope={scope} - "
            f"[b]mode={s.mode}[/] - voice={s.voice_state} - "
            f"ALERTS {s.unread_alerts} - turn={s.turn}"
        )

    def set_voice_state(self, state: VoiceState) -> None:
        try:
            badge = self.query_one(VoiceBadge)
            badge.set_state(state)
        except Exception:
            pass
