"""NudgeEngine — background heuristic evaluator.

Evaluates two heuristics every 30 s (via set_interval in BagleyApp):
    1. Idle nudge: operator has been idle >= 15 ticks -> suggest next step.
    2. Findings nudge: >= 3 HIGH findings exist -> prompt to address them.

Playbook-sequence detection and online Metasploit check are deferred to Phase 4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bagley.tui.services.alerts import Alert, AlertBus, Severity

if TYPE_CHECKING:
    from bagley.memory.store import MemoryStore
    from bagley.tui.state import AppState

_IDLE_THRESHOLD = 15          # ticks before idle nudge fires (each tick = 30 s)
_HIGH_THRESHOLD = 3           # number of untouched HIGH findings before nudge


class NudgeEngine:
    """Stateful heuristic engine. Instantiate once; call tick() on each interval."""

    def __init__(
        self,
        state: "AppState",
        store: "MemoryStore",
        bus: AlertBus | None = None,
    ) -> None:
        self._state = state
        self._store = store
        self._bus   = bus or _get_global_bus()
        self._idle_ticks       = 0
        self._idle_nudged_at   = -1   # tick at which the idle nudge last fired
        self._findings_nudged  = False

    def tick(self) -> None:
        """Called by set_interval every 30 s. Increments idle counter then evaluates."""
        self._idle_ticks += 1
        self._evaluate()

    def reset_idle(self) -> None:
        """Call whenever the user submits a chat message."""
        self._idle_ticks = 0
        self._idle_nudged_at = -1

    def _evaluate(self) -> None:
        self._check_idle()
        self._check_high_findings()

    def _check_idle(self) -> None:
        if (
            self._idle_ticks >= _IDLE_THRESHOLD
            and self._idle_ticks != self._idle_nudged_at
        ):
            self._idle_nudged_at = self._idle_ticks
            idle_min = round(self._idle_ticks * 30 / 60, 1)
            self._bus.publish(Alert(
                severity=Severity.INFO,
                title="Idle nudge",
                body=f"You've been idle for ~{idle_min} min. Want a suggested next step?",
                source="nudge",
                pane_selector="#chat-panel",
            ))

    def _check_high_findings(self) -> None:
        try:
            highs = self._store.list_findings_by_severity("high")
        except Exception:
            return
        if len(highs) >= _HIGH_THRESHOLD and not self._findings_nudged:
            self._findings_nudged = True
            hosts = list({f["host"] for f in highs})[:3]
            host_str = ", ".join(hosts)
            self._bus.publish(Alert(
                severity=Severity.WARN,
                title="Untouched findings",
                body=f"{len(highs)} HIGH findings untouched on {host_str}. Open a tab to address?",
                source="nudge",
                pane_selector="#hosts-panel",
            ))


def _get_global_bus() -> AlertBus:
    from bagley.tui.services.alerts import bus
    return bus
