"""BagleyApp — Textual TUI entrypoint."""

from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding

from bagley.tui.state import AppState, detect_os


class BagleyApp(App):
    CSS = """
    #header { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    BINDINGS = [
        Binding("ctrl+d", "disconnect", "Disconnect", show=True),
        Binding("ctrl+c", "disconnect", "Disconnect", show=False),
        Binding("alt+1", "set_mode(1)", "", show=False),
        Binding("alt+2", "set_mode(2)", "", show=False),
        Binding("alt+3", "set_mode(3)", "", show=False),
        Binding("alt+4", "set_mode(4)", "", show=False),
        Binding("alt+5", "set_mode(5)", "", show=False),
        Binding("alt+6", "set_mode(6)", "", show=False),
        Binding("alt+7", "set_mode(7)", "", show=False),
        Binding("alt+8", "set_mode(8)", "", show=False),
        Binding("alt+9", "set_mode(9)", "", show=False),
    ]

    def __init__(self, stub: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")

    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        from bagley.tui.widgets.modes_bar import ModesBar
        yield Header(self.state)
        yield ModesBar(self.state)

    def action_disconnect(self) -> None:
        self.exit()

    def action_set_mode(self, idx: int) -> None:
        from bagley.tui.modes import by_index
        self.state.mode = by_index(idx).name
        self.query_one("#header").refresh_content()
        self.query_one("#modes-bar").refresh_content()


def run() -> None:
    simple = "--simple" in sys.argv
    if simple:
        from bagley.agent.cli import app as simple_app
        sys.argv = [a for a in sys.argv if a != "--simple"]
        simple_app()
        return
    BagleyApp().run()
