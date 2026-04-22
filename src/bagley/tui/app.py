"""BagleyApp — Textual TUI entrypoint."""

from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from bagley.tui.state import AppState, detect_os


class BagleyApp(App):
    CSS = """
    #header { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    BINDINGS = [
        Binding("ctrl+d", "disconnect", "Disconnect", show=True),
        Binding("ctrl+c", "disconnect", "Disconnect", show=False),
    ]

    def __init__(self, stub: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="header")

    def _header_text(self) -> str:
        st = self.state
        return (
            f"Bagley · os={st.os_info.system} · scope=<none> · "
            f"mode={st.mode} · voice={st.voice_state} · turn={st.turn}"
        )

    def action_disconnect(self) -> None:
        self.exit()


def run() -> None:
    simple = "--simple" in sys.argv
    if simple:
        from bagley.agent.cli import app as simple_app
        sys.argv = [a for a in sys.argv if a != "--simple"]
        simple_app()
        return
    BagleyApp().run()
