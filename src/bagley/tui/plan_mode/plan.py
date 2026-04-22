"""Plan and Step dataclasses for plan mode."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class Step:
    kind: str                           # "run" | "prompt" | "if"
    cmd: str                            # shell command or prompt text
    description: str
    status: StepStatus = StepStatus.PENDING
    condition: Optional[str] = None     # raw condition string for "if" steps
    output: Optional[str] = None        # captured stdout after execution


@dataclass
class Plan:
    goal: str
    steps: list[Step]
    current_index: int = 0
    tab_id: str = "recon"
    timestamp: str = ""                 # ISO-8601, filled on persist

    def current_step(self) -> Optional[Step]:
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def advance(self) -> None:
        """Mark current step DONE and move to next."""
        if self.current_index < len(self.steps):
            self.steps[self.current_index].status = StepStatus.DONE
            self.current_index += 1

    def skip(self) -> None:
        """Mark current step SKIPPED and move to next."""
        if self.current_index < len(self.steps):
            self.steps[self.current_index].status = StepStatus.SKIPPED
            self.current_index += 1

    def is_done(self) -> bool:
        return self.current_index >= len(self.steps)

    def status_icon(self, index: int) -> str:
        """Return icon for a step by index."""
        if index == self.current_index:
            return "▶"  # ▶
        step = self.steps[index]
        return {
            StepStatus.DONE: "✓",     # ✓
            StepStatus.SKIPPED: "↷",  # ↷
            StepStatus.FAILED: "✗",   # ✗
            StepStatus.PENDING: "·",  # ·
            StepStatus.RUNNING: "▶",  # ▶
        }.get(step.status, "·")
