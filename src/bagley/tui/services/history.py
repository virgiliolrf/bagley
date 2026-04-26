"""Append-only engagement timeline for one tab.

Each `TimelineEvent` is immutable after append. `EngagementHistory` supports
snapshot-at-time queries and pairwise diffs used by the timeline scrubber and
the undo stack.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class EventKind(Enum):
    SCAN = auto()
    PORT = auto()
    FINDING = auto()
    CRED = auto()
    SHELL = auto()
    INGEST = auto()
    NOTE = auto()


@dataclass(frozen=True)
class TimelineEvent:
    kind: EventKind
    ts: datetime.datetime
    label: str
    data: dict  # arbitrary payload, treated as opaque by scrubber


@dataclass
class SnapshotDiff:
    added: list[TimelineEvent] = field(default_factory=list)
    removed: list[TimelineEvent] = field(default_factory=list)


class EngagementHistory:
    """Ordered list of timeline events for a single tab."""

    def __init__(self, tab_id: str) -> None:
        self.tab_id = tab_id
        self._events: list[TimelineEvent] = []

    @property
    def events(self) -> list[TimelineEvent]:
        return list(self._events)

    def append(self, event: TimelineEvent) -> None:
        self._events.append(event)

    def snapshot_at(self, ts: datetime.datetime) -> list[TimelineEvent]:
        """Return all events with timestamp <= ts."""
        return [e for e in self._events if e.ts <= ts]

    def diff(self, ts_from: datetime.datetime, ts_to: datetime.datetime) -> SnapshotDiff:
        """Events in (ts_from, ts_to] — what changed between two scrubber positions."""
        before = set(id(e) for e in self.snapshot_at(ts_from))
        after = self.snapshot_at(ts_to)
        added = [e for e in after if id(e) not in before]
        # Removals only possible via undo; diff between two forward points never removes
        return SnapshotDiff(added=added, removed=[])

    def remove_last(self, kind: EventKind) -> Optional[TimelineEvent]:
        """Pop the most recent event of *kind*. Returns the removed event or None."""
        for i in range(len(self._events) - 1, -1, -1):
            if self._events[i].kind == kind:
                return self._events.pop(i)
        return None
