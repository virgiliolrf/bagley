"""AlertBus — publish/subscribe hub for TUI alerts and toasts.

Usage:
    from bagley.tui.services.alerts import bus, Alert, Severity

    bus.subscribe(my_callback)
    bus.publish(Alert(Severity.CRIT, "Shell obtained", "10.0.0.1", source="promoter"))
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable


class Severity(IntEnum):
    INFO = 0
    OK   = 1
    WARN = 2
    CRIT = 3


# Severity → Textual color name
SEVERITY_COLOR: dict[Severity, str] = {
    Severity.INFO: "cyan",
    Severity.OK:   "green",
    Severity.WARN: "orange3",
    Severity.CRIT: "red",
}

# Severity → dismiss policy ("auto" = 3 s; "explicit" = must click X)
SEVERITY_DISMISS: dict[Severity, str] = {
    Severity.INFO: "auto",
    Severity.OK:   "auto",
    Severity.WARN: "auto",
    Severity.CRIT: "explicit",
}


@dataclass
class Alert:
    severity: Severity
    title: str
    body: str
    source: str                          # "scan" | "promoter" | "nudge" | …
    ts: float = field(default_factory=time.time)
    pane_selector: str = ""              # CSS selector to open on click


class AlertBus:
    _MAX_HISTORY = 200

    def __init__(self) -> None:
        self._subscribers: list[Callable[[Alert], None]] = []
        self.history: deque[Alert] = deque(maxlen=self._MAX_HISTORY)

    def subscribe(self, cb: Callable[[Alert], None]) -> None:
        if cb not in self._subscribers:
            self._subscribers.append(cb)

    def unsubscribe(self, cb: Callable[[Alert], None]) -> None:
        try:
            self._subscribers.remove(cb)
        except ValueError:
            pass

    def publish(self, alert: Alert) -> None:
        self.history.append(alert)
        for cb in list(self._subscribers):
            try:
                cb(alert)
            except Exception:
                pass


# module-level singleton used by all TUI components
bus: AlertBus = AlertBus()
