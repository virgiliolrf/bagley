"""BagleyApp — Textual TUI entrypoint. Phase 2: modes + inspector + Ctrl+M."""

from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input

from bagley.tui.state import AppState, detect_os


class BagleyApp(App):
    CSS = """
    #header { height: 1; background: $panel; color: $text; padding: 0 1; }
    #pane-row { height: 1fr; }
    """

    BINDINGS = [
        Binding("ctrl+d", "disconnect", "Disconnect", show=True),
        Binding("ctrl+c", "disconnect", "Disconnect", show=False),
        # Mode switches
        Binding("alt+1", "set_mode(1)", "", show=False),
        Binding("alt+2", "set_mode(2)", "", show=False),
        Binding("alt+3", "set_mode(3)", "", show=False),
        Binding("alt+4", "set_mode(4)", "", show=False),
        Binding("alt+5", "set_mode(5)", "", show=False),
        Binding("alt+6", "set_mode(6)", "", show=False),
        Binding("alt+7", "set_mode(7)", "", show=False),
        Binding("alt+8", "set_mode(8)", "", show=False),
        Binding("alt+9", "set_mode(9)", "", show=False),
        Binding("ctrl+m", "cycle_mode", "Cycle mode", show=False),
        # Tab management
        Binding("ctrl+t", "new_tab",     "New tab",   show=True),
        Binding("ctrl+w", "close_tab",   "Close tab", show=True),
        Binding("ctrl+1", "goto_tab(1)", "", show=False),
        Binding("ctrl+2", "goto_tab(2)", "", show=False),
        Binding("ctrl+3", "goto_tab(3)", "", show=False),
        Binding("ctrl+4", "goto_tab(4)", "", show=False),
        Binding("ctrl+5", "goto_tab(5)", "", show=False),
        Binding("ctrl+6", "goto_tab(6)", "", show=False),
        Binding("ctrl+7", "goto_tab(7)", "", show=False),
        Binding("ctrl+8", "goto_tab(8)", "", show=False),
        Binding("ctrl+9", "goto_tab(9)", "", show=False),
        # Focus
        Binding("f2", "focus('#hosts-panel')",  "Hosts", show=True),
        Binding("f3", "focus('#chat-panel')",   "Chat",  show=True),
        Binding("f4", "focus_notes", "Notes", show=True),
        # Inspector
        Binding("ctrl+i", "open_inspector", "Inspect", show=False),
        # Palette
        Binding("ctrl+k", "open_palette", "Palette", show=True),
        # Alerts log
        Binding("ctrl+n", "open_alerts_log", "Alerts", show=True),
        # Plan mode
        Binding("alt+p", "toggle_plan", "Plan mode", show=False),
        # Smart paste
        Binding("ctrl+shift+v", "smart_paste", "Smart paste", show=False),
        # Phase 5: graph / timeline / undo / background shell
        Binding("f7",           "toggle_graph",      "Graph view",        show=True),
        Binding("ctrl+shift+t", "open_timeline",     "Timeline scrubber", show=True),
        Binding("ctrl+shift+z", "undo",              "Undo last ingest",  show=True),
        Binding("ctrl+b",       "background_shell",  "Background shell",  show=True),
    ]

    def __init__(self, stub: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")

    def query_one(self, selector, expect_type=None):
        """Query the default screen first; if not found, fall back to the
        topmost screen (e.g., pushed ModalScreen). Matches the plan's test
        expectations that `app.query_one('#alerts-log-screen')` can reach
        a widget inside a modal.
        """
        try:
            if expect_type is None:
                return super().query_one(selector)
            return super().query_one(selector, expect_type)
        except Exception:
            try:
                screen = self.screen
                if screen is not None:
                    if expect_type is None:
                        return screen.query_one(selector)
                    return screen.query_one(selector, expect_type)
            except Exception:
                pass
            raise

    def on_mount(self) -> None:
        """Start background services after the DOM is ready."""
        from bagley.tui.services.nudges import NudgeEngine
        # MemoryStore is optional — if no engagement DB exists yet, use a stub path
        try:
            from bagley.memory.store import MemoryStore
            from pathlib import Path
            db_path = Path(".bagley") / "memory.db"
            store = MemoryStore(db_path)
        except Exception:
            store = None  # type: ignore[assignment]

        if store is not None:
            self._nudge_engine = NudgeEngine(state=self.state, store=store)
            self.set_interval(30, self._nudge_engine.tick)

    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        from bagley.tui.widgets.modes_bar import ModesBar
        from bagley.tui.widgets.tab_bar import TabBar
        from bagley.tui.panels.hosts import HostsPanel
        from bagley.tui.panels.chat import ChatPanel
        from bagley.tui.panels.target import TargetPanel
        from bagley.tui.panels.inspector import InspectorPane
        from bagley.tui.widgets.statusline import Statusline
        from textual.containers import Horizontal

        from bagley.tui.widgets.rings import Minimap
        from textual.containers import Vertical

        yield Header(self.state)
        yield ModesBar(self.state)
        yield TabBar(self.state)
        with Horizontal(id="pane-row"):
            yield HostsPanel(self.state)
            yield ChatPanel(self.state)
            # tab-0 (recon) shows target column + minimap stacked;
            # future tabs show just the TargetPanel.
            if self.state.active_tab == 0:
                with Vertical(id="recon-right-col"):
                    yield TargetPanel(self.state)
                    yield Minimap()
            else:
                yield TargetPanel(self.state)
        yield InspectorPane()
        yield Statusline(self.state)
        from bagley.tui.widgets.toast import ToastLayer
        yield ToastLayer()

    # -- Actions --

    def action_focus(self, selector: str) -> None:
        try:
            self.query_one(selector).focus()
        except Exception:
            pass

    def action_disconnect(self) -> None:
        self.exit()

    def action_set_mode(self, idx: int) -> None:
        from bagley.tui.modes import by_index
        mode = by_index(idx)
        self.state.mode = mode.name
        self._apply_mode_everywhere(mode.name)

    def action_cycle_mode(self) -> None:
        from bagley.tui.modes import MODES
        current_idx = next(
            (i for i, m in enumerate(MODES) if m.name == self.state.mode), 0
        )
        next_mode = MODES[(current_idx + 1) % len(MODES)]
        self.state.mode = next_mode.name
        self._apply_mode_everywhere(next_mode.name)

    def _apply_mode_everywhere(self, mode_name: str) -> None:
        """Update header, modes bar, and chat panel after a mode change."""
        try:
            self.query_one("#header").refresh_content()
        except Exception:
            pass
        try:
            self.query_one("#modes-bar").refresh_content()
        except Exception:
            pass
        try:
            from bagley.tui.panels.chat import ChatPanel
            self.query_one(ChatPanel).refresh_mode()
        except Exception:
            pass

    def action_new_tab(self) -> None:
        from bagley.tui.state import TabState
        tab_id = f"target-{len(self.state.tabs)}"
        self.state.tabs.append(TabState(id=tab_id, kind="target"))
        self.state.active_tab = len(self.state.tabs) - 1
        self._refresh_tab_dependent()

    def action_close_tab(self) -> None:
        if self.state.active_tab == 0:
            return
        del self.state.tabs[self.state.active_tab]
        self.state.active_tab = max(0, self.state.active_tab - 1)
        self._refresh_tab_dependent()

    def action_goto_tab(self, idx: int) -> None:
        target = idx - 1
        if 0 <= target < len(self.state.tabs):
            self.state.active_tab = target
            self._refresh_tab_dependent()

    def _refresh_tab_dependent(self) -> None:
        for widget_id in ("#tab-bar", "#hosts-panel", "#target-panel"):
            try:
                self.query_one(widget_id).refresh_content()
            except Exception:
                pass

    def action_focus_notes(self) -> None:
        try:
            from bagley.tui.panels.notes_editor import NotesEditor
            self.query_one(NotesEditor).focus()
        except Exception:
            pass

    def action_open_inspector(self) -> None:
        """Open inspector with the current chat-input value as selection."""
        from bagley.tui.panels.inspector import InspectorPane
        try:
            text = self.query_one("#chat-input", Input).value.strip()
        except Exception:
            text = ""
        if text:
            self.query_one(InspectorPane).inspect(text)

    def action_close_inspector(self) -> None:
        from bagley.tui.panels.inspector import InspectorPane
        try:
            self.query_one(InspectorPane).display = False
        except Exception:
            pass

    async def action_open_palette(self) -> None:
        from bagley.tui.widgets.palette import CommandPalette

        def _on_dismiss(result: str | None) -> None:
            if result is None:
                return
            if result.startswith("__placeholder__"):
                return
            if "(" in result:
                name, _, rest = result.partition("(")
                arg_raw = rest.rstrip(")").strip("'\"")
                method = getattr(self, f"action_{name}", None)
                if method:
                    try:
                        method(int(arg_raw))
                    except ValueError:
                        method(arg_raw)
            else:
                method = getattr(self, f"action_{result}", None)
                if method:
                    method()

        self.push_screen(CommandPalette(), callback=_on_dismiss)

    # -- Palette-dispatched stubs (filled out in later phases) --

    def action_swap_engine(self) -> None:
        pass   # Phase 6

    def action_set_engine(self, label: str) -> None:
        self.state.engine_label = label
        try:
            self.query_one("#header").refresh_content()
        except Exception:
            pass

    def action_run_playbook(self, name: str) -> None:
        """Look up a playbook by name in .playbooks/ and load it via plan mode."""
        from bagley.tui.playbooks.loader import scan_playbooks
        from bagley.tui.playbooks.runner import PlaybookRunner

        playbooks = scan_playbooks()
        # Match by name (case-insensitive) or by filename stem (without .yml)
        target_pb = None
        for pb in playbooks:
            if pb.name.lower() == name.lower() or (
                pb.source is not None and pb.source.stem.lower() == name.lower()
            ):
                target_pb = pb
                break
        if target_pb is None:
            try:
                self.notify(f"Playbook '{name}' not found", severity="warning")
            except Exception:
                pass
            return
        tab = self.state.tabs[self.state.active_tab] if self.state.tabs else None
        target_val = tab.id if tab else "target"
        runner = PlaybookRunner(playbook=target_pb, variables={"target": target_val})
        plan = runner.to_plan(tab_id=target_val)
        try:
            from bagley.tui.panels.chat import ChatPanel
            chat = self.query_one(ChatPanel)
            chat.load_plan(plan)
        except Exception:
            try:
                self.notify("Could not load plan into chat panel", severity="error")
            except Exception:
                pass

    def action_run_playbook_picker(self) -> None:
        """Scan .playbooks/ and load the first one through plan mode (Phase 4 stub)."""
        from bagley.tui.playbooks.loader import scan_playbooks
        from bagley.tui.playbooks.runner import PlaybookRunner

        playbooks = scan_playbooks()
        if not playbooks:
            try:
                self.notify("No playbooks found in .playbooks/", severity="warning")
            except Exception:
                pass
            return
        # Full selection screen is Phase 5 UI polish; here we just load first.
        pb = playbooks[0]
        tab = self.state.tabs[self.state.active_tab] if self.state.tabs else None
        target_val = tab.id if tab else "target"
        runner = PlaybookRunner(playbook=pb, variables={"target": target_val})
        plan = runner.to_plan(tab_id=target_val)
        try:
            from bagley.tui.panels.chat import ChatPanel
            chat = self.query_one(ChatPanel)
            chat.load_plan(plan)
        except Exception:
            try:
                self.notify("Could not load plan into chat panel", severity="error")
            except Exception:
                pass

    def action_open_alerts(self) -> None:
        self.action_open_alerts_log()

    def action_open_alerts_log(self) -> None:
        from bagley.tui.widgets.alerts_log import AlertsLog
        self.push_screen(AlertsLog())

    def action_clear_alerts(self) -> None:
        self.state.unread_alerts = 0
        try:
            self.query_one("#header").refresh_content()
        except Exception:
            pass

    def action_search_history(self) -> None:
        pass   # Phase 4

    def action_clear_chat(self) -> None:
        try:
            self.query_one("#chat-log").clear()
        except Exception:
            pass

    def action_last_tool_output(self) -> None:
        pass   # Phase 4

    def action_show_help(self) -> None:
        pass   # Phase 6

    def action_toggle_voice(self) -> None:
        pass   # Phase 6

    def action_open_payload_builder(self) -> None:
        pass   # Phase 6

    def action_toggle_plan_mode(self) -> None:
        self.action_toggle_plan()

    def action_toggle_plan(self) -> None:
        """Toggle plan mode overlay in the active ChatPanel."""
        try:
            chat = self.query_one("ChatPanel")
            chat.toggle_plan_mode()
        except Exception:
            self.notify("No chat panel active", severity="warning")

    def action_smart_paste(self) -> None:
        """Invoke smart paste: reads clipboard and dispatches to ChatPanel."""
        try:
            import pyperclip
            text = pyperclip.paste()
        except Exception:
            try:
                self.notify("Could not read clipboard (pyperclip missing?)", severity="error")
            except Exception:
                pass
            return
        try:
            chat = self.query_one("ChatPanel")
            chat.handle_smart_paste(text)
        except Exception:
            try:
                self.notify("No active chat panel for smart paste", severity="warning")
            except Exception:
                pass

    def action_toggle_graph(self) -> None:
        """F7: toggle GraphPane full-screen."""
        try:
            pane = self.query_one("GraphPane")
            pane.display = not pane.display
        except Exception:
            pass  # GraphPane not yet mounted (no hosts discovered)

    def action_open_timeline(self) -> None:
        """Ctrl+Shift+T: show/hide the timeline scrubber widget."""
        try:
            tl = self.query_one("Timeline")
            tl.display = not tl.display
            if tl.display:
                tl.focus()
        except Exception:
            pass

    def action_undo(self) -> None:
        """Ctrl+Shift+Z: undo the last finding or ingest for the active tab."""
        active = self._get_active_tab_history()
        if active is None:
            try:
                self.notify("Nothing to undo.", severity="information")
            except Exception:
                pass
            return
        from bagley.tui.services.undo import UndoStack
        record = UndoStack(history=active).undo()
        if record is None:
            try:
                self.notify("Nothing to undo.", severity="information")
            except Exception:
                pass
        else:
            try:
                self.notify(
                    f"Undone: [{record.event.kind.name}] {record.event.label}",
                    severity="warning",
                )
            except Exception:
                pass
            try:
                self.query_one("Timeline").reload()
            except Exception:
                pass

    def action_background_shell(self) -> None:
        """Ctrl+B: background the currently focused ShellPane."""
        try:
            pane = self.query_one("ShellPane:focus")
            pane.action_background()
        except Exception:
            pass

    def _get_active_tab_history(self):
        """Return the EngagementHistory for the active tab, or None."""
        try:
            return self.state.active_tab_history
        except AttributeError:
            return None

    def action_undo_finding(self) -> None:
        """Legacy alias for action_undo."""
        self.action_undo()

    def action_set_scope(self) -> None:
        pass   # Phase 3

    def action_export_report(self) -> None:
        pass   # Phase 6


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


if __name__ == "__main__":
    run()
