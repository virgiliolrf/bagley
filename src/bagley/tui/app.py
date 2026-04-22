"""BagleyApp — Textual TUI entrypoint."""

from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding

from bagley.tui.state import AppState, detect_os


class BagleyApp(App):
    CSS = """
    #header { height: 1; background: $panel; color: $text; padding: 0 1; }
    #pane-row { height: 1fr; }
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
        Binding("f2", "focus('#hosts-panel')", "Hosts", show=True),
        Binding("f3", "focus('#chat-panel')", "Chat", show=True),
        Binding("f4", "focus('#target-panel')", "Notes", show=True),
        Binding("ctrl+k", "open_palette", "Palette", show=True),
    ]

    def __init__(self, stub: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")

    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        from bagley.tui.widgets.modes_bar import ModesBar
        from bagley.tui.widgets.tab_bar import TabBar
        from bagley.tui.panels.hosts import HostsPanel
        from bagley.tui.panels.chat import ChatPanel
        from bagley.tui.panels.target import TargetPanel
        from textual.containers import Horizontal
        yield Header(self.state)
        yield ModesBar(self.state)
        yield TabBar(self.state)
        with Horizontal(id="pane-row"):
            yield HostsPanel(self.state)
            yield ChatPanel(self.state)
            yield TargetPanel(self.state)

    def action_focus(self, selector: str) -> None:
        try:
            widget = self.query_one(selector)
        except Exception:
            return
        widget.focus()

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
        self.query_one("#hosts-panel").refresh_content()
        self.query_one("#target-panel").refresh_content()

    def action_close_tab(self) -> None:
        if self.state.active_tab == 0:
            return
        del self.state.tabs[self.state.active_tab]
        self.state.active_tab = max(0, self.state.active_tab - 1)
        self.query_one("#tab-bar").refresh_content()
        self.query_one("#hosts-panel").refresh_content()
        self.query_one("#target-panel").refresh_content()

    async def action_open_palette(self) -> None:
        from bagley.tui.widgets.palette import CommandPalette

        def _on_dismiss(result: str | None) -> None:
            if result is None:
                return
            if "(" in result:
                name, _, rest = result.partition("(")
                arg = rest.rstrip(")").strip("'\"")
                method = getattr(self, f"action_{name}", None)
                if method:
                    method(arg)
            else:
                method = getattr(self, f"action_{result}", None)
                if method:
                    method()

        self.push_screen(CommandPalette(), callback=_on_dismiss)

    def action_goto_tab(self, idx: int) -> None:
        target = idx - 1
        if 0 <= target < len(self.state.tabs):
            self.state.active_tab = target
            self.query_one("#tab-bar").refresh_content()
            self.query_one("#hosts-panel").refresh_content()
            self.query_one("#target-panel").refresh_content()


def run() -> None:
    if "--simple" in sys.argv:
        from bagley.agent.cli import app as simple_app
        sys.argv = [a for a in sys.argv if a != "--simple"]
        simple_app()
        return

    import argparse
    parser = argparse.ArgumentParser(prog="bagley", add_help=False)
    parser.add_argument("--stub", action="store_true")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--base", default="./models/foundation-sec-8b")
    parser.add_argument("--ollama", action="store_true")
    parser.add_argument("--ollama-model", default="bagley")
    parser.add_argument("-h", "--help", action="store_true")
    args, _ = parser.parse_known_args()

    if args.help:
        print("bagley [--stub] [--adapter PATH] [--base PATH] [--ollama] [--simple]")
        return

    BagleyApp(stub=args.stub).run()
