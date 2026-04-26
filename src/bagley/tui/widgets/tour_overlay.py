"""First-launch tour overlay widget.

Renders a full-screen translucent overlay with a highlighted caption
panel. Advances through TOUR_STEPS on Enter/Space; Esc skips.
"""

from __future__ import annotations

from typing import Callable, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label

from bagley.tui.services.tour import TOUR_STEPS


class TourOverlay(Widget):
    """Full-screen overlay driving the first-launch tour."""

    DEFAULT_CSS = """
    TourOverlay {
        layer: overlay;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        align: center bottom;
    }
    #tour-caption {
        width: 80;
        height: 5;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
        align: center middle;
        margin-bottom: 2;
    }
    #tour-progress { color: $text-muted; }
    """

    BINDINGS = [
        Binding("escape", "skip_tour", "Skip tour", show=True),
        Binding("enter", "next_step", "Next", show=True),
        Binding("space", "next_step", "Next", show=False),
    ]

    def __init__(self, on_done: Optional[Callable[[], None]] = None, **kwargs) -> None:
        super().__init__(id="tour-overlay", **kwargs)
        self._step = 0
        self._on_done = on_done
        self.can_focus = True

    def compose(self) -> ComposeResult:
        with Vertical(id="tour-caption"):
            yield Label("", id="tour-text")
            yield Label("", id="tour-progress")

    def on_mount(self) -> None:
        self._render_step()
        try:
            self.focus()
        except Exception:
            pass

    def _render_step(self) -> None:
        if self._step >= len(TOUR_STEPS):
            self._finish()
            return
        _pane_id, caption = TOUR_STEPS[self._step]
        try:
            self.query_one("#tour-text", Label).update(caption)
            progress = f"Step {self._step + 1} / {len(TOUR_STEPS)}  -  Esc to skip"
            self.query_one("#tour-progress", Label).update(f"[dim]{progress}[/dim]")
        except Exception:
            pass

    def action_next_step(self) -> None:
        self._step += 1
        if self._step >= len(TOUR_STEPS):
            self._finish()
        else:
            self._render_step()

    def action_skip_tour(self) -> None:
        self._finish()

    def _finish(self) -> None:
        if self._on_done:
            try:
                self._on_done()
            except Exception:
                pass
        try:
            self.remove()
        except Exception:
            pass
