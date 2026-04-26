"""UndoStack: removes the last undoable event from an EngagementHistory.

Undoable event kinds: FINDING, INGEST, CRED, NOTE.
Non-undoable: SCAN, PORT, SHELL (side-effectful; removing from the timeline
would not reverse the real-world action and could confuse the operator).

The removed event is returned as an UndoRecord so the timeline widget can
offer a one-click replay (re-append).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bagley.tui.services.history import EngagementHistory, EventKind, TimelineEvent

_UNDOABLE = {EventKind.FINDING, EventKind.INGEST, EventKind.CRED, EventKind.NOTE}


@dataclass
class UndoRecord:
    event: TimelineEvent


class UndoStack:
    """Single-level undo for false-positive removal.

    Wraps an EngagementHistory and exposes ``undo()`` which removes the most
    recent undoable event and returns an ``UndoRecord`` the caller can use to
    replay (re-append) the event if needed.
    """

    def __init__(self, history: EngagementHistory) -> None:
        self._history = history

    def undo(self) -> Optional[UndoRecord]:
        """Remove and return the latest undoable event, or None if none exists."""
        return self._undo_latest_across_kinds()

    def _undo_latest_across_kinds(self) -> Optional[UndoRecord]:
        """Find and remove the single most-recent undoable event across all kinds."""
        best_idx: Optional[int] = None
        events = self._history._events  # direct access to internal list
        for i in range(len(events) - 1, -1, -1):
            if events[i].kind in _UNDOABLE:
                best_idx = i
                break
        if best_idx is None:
            return None
        removed = events.pop(best_idx)
        return UndoRecord(event=removed)
