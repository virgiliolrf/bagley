"""Toast widget and ToastLayer — slide-in bottom-right notification stack.

ToastLayer subscribes to the global AlertBus on mount and manages up to
MAX_STACK Toast children. CRIT toasts require explicit dismiss; others
auto-dismiss after AUTO_DISMISS_S seconds via set_interval.
"""

from __future__ import annotations

import time
from typing import Callable

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal

from bagley.tui.services.alerts import Alert, AlertBus, Severity, SEVERITY_COLOR, SEVERITY_DISMISS, bus as _global_bus

MAX_STACK = 4
AUTO_DISMISS_S = 3.0


class Toast(Widget):
    """A single notification card."""

    DEFAULT_CSS = """
    Toast {
        height: auto;
        min-height: 3;
        width: 40;
        padding: 0 1;
        margin: 0 0 1 0;
        border: round $accent;
    }
    Toast.severity-info { border: round cyan; }
    Toast.severity-ok   { border: round green; }
    Toast.severity-warn { border: round yellow; }
    Toast.severity-crit { border: round red; }
    Toast > Horizontal { height: 1; }
    Toast > Label.body  { color: $text-muted; }
    """

    COMPONENT_CLASSES = {"toast-widget"}

    def __init__(self, alert: Alert, on_dismiss: Callable[["Toast"], None], **kwargs) -> None:
        super().__init__(**kwargs)
        self.alert = alert
        self._on_dismiss = on_dismiss
        self.add_class("toast-widget")
        sev_name = alert.severity.name.lower()
        self.add_class(f"severity-{sev_name}")

    def compose(self) -> ComposeResult:
        color = SEVERITY_COLOR[self.alert.severity]
        with Horizontal():
            yield Label(f"[bold {color}]{self.alert.title}[/]", id="toast-title")
            yield Button("✕", id="toast-close", variant="default")
        if self.alert.body:
            yield Label(self.alert.body, classes="body")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toast-close":
            self._on_dismiss(self)

    def on_click(self) -> None:
        if self.alert.pane_selector:
            try:
                self.app.query_one(self.alert.pane_selector).focus()
            except Exception:
                pass
        self._on_dismiss(self)


class ToastLayer(Widget):
    """Fixed bottom-right widget that owns up to MAX_STACK Toast children."""

    DEFAULT_CSS = """
    ToastLayer {
        dock: bottom;
        align: right bottom;
        width: 42;
        height: auto;
        max-height: 20;
        padding: 0 1 1 0;
        layer: overlay;
    }
    """

    def __init__(self, alert_bus: AlertBus | None = None, **kwargs) -> None:
        super().__init__(id="toast-layer", **kwargs)
        self._bus = alert_bus or _global_bus
        self._toasts: list[Toast] = []
        self._toast_timers: dict[int, object] = {}   # id(toast) → timer handle

    def on_mount(self) -> None:
        self._bus.subscribe(self._on_alert)

    def on_unmount(self) -> None:
        self._bus.unsubscribe(self._on_alert)

    # called from AlertBus subscriber (safe from UI or worker thread)
    def _on_alert(self, alert: Alert) -> None:
        try:
            # call_later schedules on the UI loop regardless of caller thread
            self.app.call_later(self._add_toast, alert)
        except Exception:
            # fallback: synchronous call (e.g., during tests before app ready)
            try:
                self._add_toast(alert)
            except Exception:
                pass

    def _add_toast(self, alert: Alert) -> None:
        # enforce stack cap
        while len(self._toasts) >= MAX_STACK:
            oldest = self._toasts[0]
            self._dismiss(oldest)

        toast = Toast(alert, on_dismiss=self._dismiss)
        self._toasts.append(toast)
        self.mount(toast)

        dismiss_policy = SEVERITY_DISMISS[alert.severity]
        if dismiss_policy == "auto":
            handle = self.set_timer(AUTO_DISMISS_S, lambda t=toast: self._dismiss(t))
            self._toast_timers[id(toast)] = handle

    def _dismiss(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        key = id(toast)
        if key in self._toast_timers:
            del self._toast_timers[key]
        try:
            toast.remove()
        except Exception:
            pass
