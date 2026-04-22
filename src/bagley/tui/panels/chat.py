"""ChatPanel — ReAct stream with inline confirmation and mode wiring.

Phase 2 changes vs Phase 1:
- ConfirmPanel renders inline (docked bottom of ChatPanel) for explicit-confirm
  modes instead of blocking the process.
- apply_mode_to_loop() is called whenever the mode changes.
- submit_command() is a public method used by InspectorPane and playbooks.
- Ctrl+I handler captures focused text and opens InspectorPane.
"""

from __future__ import annotations

from typing import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Input, Label, RichLog, Static

from bagley.agent.loop import ReActLoop
from bagley.inference.engine import stub_response
from bagley.persona import DEFAULT_SYSTEM
from bagley.tui.modes import by_name
from bagley.tui.modes.persona import mode_system_suffix
from bagley.tui.modes.policy import apply_mode_to_loop
from bagley.tui.state import AppState


# -- Stub engine (used when state.engine_label == "stub") --

class _StubEngine:
    def generate(self, messages, **kwargs):
        last = next((m for m in reversed(messages) if m["role"] == "user"), None)
        return stub_response(last["content"] if last else "")


# -- Inline confirmation panel --

class ConfirmPanel(Vertical):
    """Inline confirmation panel - shown docked at the bottom of ChatPanel.

    The caller provides a `callback(result: bool)` that is invoked when the
    user presses y/n or clicks the buttons. After dispatch the panel hides.
    """

    DEFAULT_CSS = """
    ConfirmPanel {
        height: 5;
        border: round $warning;
        background: $panel;
        padding: 0 1;
        display: none;
        visibility: hidden;
    }
    ConfirmPanel #confirm-cmd-label { height: 1; color: $warning; }
    ConfirmPanel #confirm-btn-row   { height: 3; align: left middle; }
    ConfirmPanel Button { min-width: 8; height: 3; }
    """

    BINDINGS = [
        Binding("y", "accept", "Yes", show=False),
        Binding("n", "reject", "No",  show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(id="confirm-panel", **kwargs)
        self._pending_cmd: str = ""
        self._callback: Callable[[bool], None] | None = None
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Label("", id="confirm-cmd-label")
        with Horizontal(id="confirm-btn-row"):
            yield Button("[Y] Yes", id="confirm-yes-btn", variant="success")
            yield Button("[N] No",  id="confirm-no-btn",  variant="error")

    def show_confirm(self, cmd: str, callback: Callable[[bool], None]) -> None:
        """Populate and reveal the panel."""
        self._pending_cmd = cmd
        self._callback = callback
        truncated = cmd[:60] + "..." if len(cmd) > 60 else cmd
        self.query_one("#confirm-cmd-label", Label).update(
            f"[bold yellow]About to execute:[/] [cyan]{truncated}[/]"
        )
        self.display = True
        self.visible = True
        self.focus()

    def _respond(self, result: bool) -> None:
        self.display = False
        self.visible = False
        if self._callback is not None:
            cb = self._callback
            self._callback = None
            cb(result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes-btn":
            self._respond(True)
            event.stop()
        elif event.button.id == "confirm-no-btn":
            self._respond(False)
            event.stop()

    def action_accept(self) -> None:
        self._respond(True)

    def action_reject(self) -> None:
        self._respond(False)


# -- ChatPanel --

class ChatPanel(Vertical):
    DEFAULT_CSS = """
    ChatPanel { border: round $primary; padding: 0 1; }
    ChatPanel > RichLog { height: 1fr; }
    ChatPanel > Input   { height: 3; dock: bottom; }
    """

    BINDINGS = [
        Binding("ctrl+i", "inspect_selection", "Inspect", show=False),
    ]

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="chat-panel", **kwargs)
        self._state = state
        self._loop = self._build_loop()
        self.can_focus = True

    def _build_loop(self) -> ReActLoop:
        engine = _StubEngine()
        loop = ReActLoop(engine=engine, auto_approve=True, max_steps=1)
        apply_mode_to_loop(loop, self._state.mode)
        return loop

    def _system_for_current_mode(self) -> str:
        return DEFAULT_SYSTEM + mode_system_suffix(self._state.mode)

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield ConfirmPanel()
        yield Input(placeholder="you> ", id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-log").write(
            "[dim]Bagley TUI Phase 2. Mode: [bold cyan]"
            + self._state.mode + "[/]. Type and press Enter.[/]"
        )

    # -- Public API --

    def refresh_mode(self) -> None:
        """Called by app.action_set_mode / action_cycle_mode after mode change."""
        apply_mode_to_loop(self._loop, self._state.mode)
        try:
            log = self.query_one("#chat-log", RichLog)
            mode = by_name(self._state.mode)
            log.write(
                f"[dim italic][mode -> {mode.name}] "
                f"confirm={mode.confirm_policy} | allowlist={'all' if mode.allowlist is None else len(mode.allowlist)}[/]"
            )
            # Update border color to reflect the new mode
            self.styles.border = ("round", mode.color)
        except Exception:
            pass

    def request_confirm(self, cmd: str, callback: Callable[[bool], None]) -> None:
        """Show the inline confirm panel for *cmd*; call *callback* with result."""
        panel = self.query_one(ConfirmPanel)
        panel.show_confirm(cmd, callback)

    def submit_command(self, cmd: str) -> None:
        """Programmatically submit a command as if the user typed it."""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold green]you>[/] {cmd}")
        self._run_in_loop(cmd, log)

    # -- Input handling --

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
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold green]you>[/] {msg}")
        self._run_in_loop(msg, log)

    def _run_in_loop(self, msg: str, log: RichLog) -> None:
        steps = self._loop.run(msg, self._system_for_current_mode())
        for step in steps:
            if step.kind in {"assistant", "final"}:
                log.write(f"[magenta]bagley>[/] {step.content}")
            elif step.kind == "tool":
                rc = step.execution.returncode if step.execution else 0
                color = "green" if rc == 0 else "yellow"
                log.write(f"[{color}]tool>[/] {step.content}")
            elif step.kind == "blocked":
                log.write(f"[red]blocked>[/] {step.content}")
        self._state.turn += 1
        try:
            self.app.query_one("#header").refresh_content()
        except Exception:
            pass
        try:
            self.app.query_one("#statusline").refresh_content()
        except Exception:
            pass

    # -- Ctrl+I - inspect selection --

    def action_inspect_selection(self) -> None:
        """Open InspectorPane with currently selected text (or chat-input fallback)."""
        text = ""
        try:
            sel = self.screen.selection
            if sel is not None:
                text = str(sel)
        except Exception:
            pass
        if not text:
            try:
                inp = self.query_one("#chat-input", Input)
                text = inp.value
            except Exception:
                pass
        if text.strip():
            try:
                from bagley.tui.panels.inspector import InspectorPane
                pane = self.app.query_one(InspectorPane)
                pane.inspect(text.strip())
            except Exception:
                pass
