"""Header widget — OS, scope, mode, voice, alerts badge."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.state import AppState


class Header(Static):
    DEFAULT_CSS = """
    Header { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="header", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        s = self._state
        scope = ",".join(s.scope_cidrs) or "<none>"
        self.update(
            f"[b]Bagley[/] · os={s.os_info.system} · scope={scope} · "
            f"[b]mode={s.mode}[/] · voice={s.voice_state} · "
            f"🔔 {s.unread_alerts} · turn={s.turn}"
        )
