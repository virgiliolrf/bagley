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
        Binding("ctrl+t", "new_tab", "New tab", show=True),
        Binding("ctrl+w", "close_tab", "Close tab", show=True),
        Binding("ctrl+1", "goto_tab(1)", "", show=False),
        Binding("ctrl+2", "goto_tab(2)", "", show=False),
        Binding("ctrl+3", "goto_tab(3)", "", show=False),
        Binding("ctrl+4", "goto_tab(4)", "", show=False),
        Binding("ctrl+5", "goto_tab(5)", "", show=False),
        Binding("ctrl+6", "goto_tab(6)", "", show=False),
        Binding("ctrl+7", "goto_tab(7)", "", show=False),
        Binding("ctrl+8", "goto_tab(8)", "", show=False),
        Binding("ctrl+9", "goto_tab(9)", "", show=False),
    ]

    def __init__(self, stub: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")

    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        from bagley.tui.widgets.modes_bar import ModesBar
        yield Header(self.state)
        yield ModesBar(self.state)
        from bagley.tui.widgets.tab_bar import TabBar
        yield TabBar(self.state)

    def action_disconnect(self) -> None:
        self.exit()

    def action_set_mode(self, idx: int) -> None:
        from bagley.tui.modes import by_index
        self.state.mode = by_index(idx).name
        self.query_one("#header").refresh_content()
        self.query_one("#modes-bar").refresh_content()

    def action_new_tab(self) -> None:
        from bagley.tui.state import TabState
        tab_id = f"target-{len(self.state.tabs)}"
        self.state.tabs.append(TabState(id=tab_id, kind="target"))
        self.state.active_tab = len(self.state.tabs) - 1
        self.query_one("#tab-bar").refresh_content()

    def action_close_tab(self) -> None:
        if self.state.active_tab == 0:
            return
        del self.state.tabs[self.state.active_tab]
        self.state.active_tab = max(0, self.state.active_tab - 1)
        self.query_one("#tab-bar").refresh_content()

    def action_goto_tab(self, idx: int) -> None:
        target = idx - 1
        if 0 <= target < len(self.state.tabs):
            self.state.active_tab = target
            self.query_one("#tab-bar").refresh_content()


def run() -> None:
    simple = "--simple" in sys.argv
    if simple:
        from bagley.agent.cli import app as simple_app
        sys.argv = [a for a in sys.argv if a != "--simple"]
        simple_app()
        return
    BagleyApp().run()
