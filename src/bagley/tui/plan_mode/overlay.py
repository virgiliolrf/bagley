"""PlanOverlay — full-screen-ish Textual widget for plan mode."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

from bagley.tui.plan_mode.plan import Plan, StepStatus


class PlanOverlay(Container):
    """Displays and drives user interaction with a Plan.

    Keyboard:
      up/down   — move cursor
      Enter     — approve + run current step (posts ApproveStep)
      s         — skip current step
      e         — edit command (posts EditStep)
      A         — approve all remaining steps
      Esc       — dismiss (posts Dismissed)
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("enter", "approve", "Approve"),
        Binding("s", "skip", "Skip"),
        Binding("e", "edit", "Edit"),
        Binding("A", "approve_all", "Approve All"),
        Binding("escape", "dismiss_overlay", "Exit"),
    ]

    DEFAULT_CSS = """
    PlanOverlay {
        layer: overlay;
        background: $surface;
        border: solid $primary;
        padding: 1 2;
        width: 80%;
        height: auto;
        max-height: 80%;
        align: center middle;
    }
    PlanOverlay .plan-title { color: $primary; text-style: bold; }
    PlanOverlay .step-current { color: $success; text-style: bold; }
    PlanOverlay .step-done { color: $text-muted; }
    PlanOverlay .step-pending { color: $text; }
    """

    cursor: reactive[int] = reactive(0)

    # ── Messages ──────────────────────────────────────────────────────────────

    class ApproveStep(Message):
        """Emitted when the user presses Enter to run a step."""
        def __init__(self, cmd: str) -> None:
            super().__init__()
            self.cmd = cmd

    class EditStep(Message):
        """Emitted when the user presses 'e' to edit the current step's cmd."""
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    class Dismissed(Message):
        """Emitted when the overlay is closed via Esc."""

    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, plan: Plan, **kwargs) -> None:
        super().__init__(**kwargs)
        self.plan = plan
        self.cursor = plan.current_index
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]Plan:[/] {self.plan.goal}", classes="plan-title")
        yield Label("", id="steps-label")

    def on_mount(self) -> None:
        self._refresh_steps()
        self.focus()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render_steps_text(self) -> str:
        lines: list[str] = []
        for i, step in enumerate(self.plan.steps):
            icon = self.plan.status_icon(i)
            marker = "▶" if i == self.cursor else " "
            lines.append(f"  {marker} {icon}  {step.description}  [{step.cmd}]")
        return "\n".join(lines)

    def _refresh_steps(self) -> None:
        try:
            label = self.query_one("#steps-label", Label)
            label.update(self.render_steps_text())
        except Exception:
            pass

    def watch_cursor(self, _: int) -> None:
        self._refresh_steps()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_cursor_up(self) -> None:
        if self.cursor > 0:
            self.cursor -= 1

    def action_cursor_down(self) -> None:
        if self.cursor < len(self.plan.steps) - 1:
            self.cursor += 1

    def action_approve(self) -> None:
        step = self.plan.current_step()
        if step is None:
            return
        self.post_message(self.ApproveStep(cmd=step.cmd))
        self.plan.advance()
        self.cursor = self.plan.current_index
        self._refresh_steps()

    def action_skip(self) -> None:
        self.plan.skip()
        self.cursor = self.plan.current_index
        self._refresh_steps()

    def action_edit(self) -> None:
        self.post_message(self.EditStep(index=self.plan.current_index))

    def action_approve_all(self) -> None:
        while not self.plan.is_done():
            step = self.plan.current_step()
            if step:
                self.post_message(self.ApproveStep(cmd=step.cmd))
            self.plan.advance()
        self.cursor = self.plan.current_index
        self._refresh_steps()

    def action_dismiss_overlay(self) -> None:
        self.post_message(self.Dismissed())
