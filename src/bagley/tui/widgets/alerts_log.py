"""AlertsLog — full-history modal opened by Ctrl+N.

Reads from the module-level AlertBus.history deque and renders a
scrollable RichLog of all past alerts, newest at top.
"""

from __future__ import annotations

import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, RichLog, Button
from textual.containers import Vertical

from bagley.tui.services.alerts import bus, SEVERITY_COLOR, Severity


class AlertsLog(ModalScreen):
    """Ctrl+N modal showing full alert history."""

    DEFAULT_CSS = """
    AlertsLog {
        align: center middle;
    }
    #alerts-log-screen {
        width: 80;
        height: 30;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    #alerts-list { height: 1fr; }
    #alerts-close { dock: bottom; width: 100%; }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="alerts-log-screen"):
            yield Label("[bold]Alert History[/] — most recent first", id="alerts-header")
            log = RichLog(id="alerts-list", markup=True, highlight=False, wrap=True)
            yield log
            yield Button("Close  [Esc]", id="alerts-close", variant="default")

    def on_mount(self) -> None:
        log = self.query_one("#alerts-list", RichLog)
        history = list(bus.history)
        history.reverse()  # newest first
        if not history:
            log.write("[dim]No alerts yet.[/]")
            return
        for alert in history:
            color = SEVERITY_COLOR[alert.severity]
            ts = datetime.datetime.fromtimestamp(alert.ts).strftime("%H:%M:%S")
            log.write(
                f"[dim]{ts}[/]  [{color}]{alert.severity.name:5}[/]  "
                f"[bold]{alert.title}[/]  {alert.body}"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "alerts-close":
            self.dismiss()
