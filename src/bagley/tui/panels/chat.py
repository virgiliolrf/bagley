"""ChatPanel — center column: ReAct stream. Phase 1 stub."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog, Input

from bagley.tui.state import AppState


class ChatPanel(Vertical):
    DEFAULT_CSS = """
    ChatPanel { border: round $primary; padding: 0 1; }
    ChatPanel > RichLog { height: 1fr; }
    ChatPanel > Input { height: 3; dock: bottom; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="chat-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        log = RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield log
        yield Input(placeholder="you> ", id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-log").write(
            "[dim]Phase 1 — chat skeleton. ReActLoop wiring comes in Task 8.[/]"
        )
