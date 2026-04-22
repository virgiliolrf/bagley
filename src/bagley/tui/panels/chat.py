"""ChatPanel — ReAct stream (Phase 1: plain exchange, no tool use UI yet)."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog, Input

from bagley.agent.loop import ReActLoop
from bagley.inference.engine import stub_response
from bagley.persona import DEFAULT_SYSTEM
from bagley.tui.state import AppState


class _StubEngine:
    def generate(self, messages, **kwargs):
        last = next((m for m in reversed(messages) if m["role"] == "user"), None)
        return stub_response(last["content"] if last else "")


class ChatPanel(Vertical):
    DEFAULT_CSS = """
    ChatPanel { border: round $primary; padding: 0 1; }
    ChatPanel > RichLog { height: 1fr; }
    ChatPanel > Input { height: 3; dock: bottom; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="chat-panel", **kwargs)
        self._state = state
        self._loop = ReActLoop(engine=_StubEngine(), auto_approve=True, max_steps=1)
        self.can_focus = True

    def compose(self):
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield Input(placeholder="you> ", id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-log").write(
            "[dim]Phase 1 chat (stub engine). Type and press Enter.[/]"
        )

    def on_key(self, event) -> None:
        if event.key == "enter":
            inp = self.query_one("#chat-input", Input)
            inp.post_message(Input.Submitted(inp, inp.value))
            event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input":
            return
        msg = event.value.strip()
        if not msg:
            return
        event.input.value = ""
        log = self.query_one("#chat-log")
        log.write(f"[bold green]you>[/] {msg}")
        steps = self._loop.run(msg, DEFAULT_SYSTEM)
        for step in steps:
            prefix = "[magenta]bagley>[/]" if step.kind in {"assistant", "final"} else "[yellow]tool>[/]"
            log.write(f"{prefix} {step.content}")
        self._state.turn += 1
        self.app.query_one("#header").refresh_content()
