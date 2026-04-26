"""Tests for UndoStack."""
import datetime
import pytest
from bagley.tui.services.history import EngagementHistory, TimelineEvent, EventKind
from bagley.tui.services.undo import UndoStack, UndoRecord


def _ts(offset_s: int = 0) -> datetime.datetime:
    return datetime.datetime(2026, 4, 26, 12, 0, 0) + datetime.timedelta(seconds=offset_s)


def test_undo_removes_last_finding():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="CVE-2021-41773", data={}))
    stack = UndoStack(history=h)
    record = stack.undo()
    assert record is not None
    assert record.event.label == "CVE-2021-41773"
    assert len(h.events) == 1


def test_undo_on_empty_history_returns_none():
    h = EngagementHistory(tab_id="10.10.14.1")
    stack = UndoStack(history=h)
    assert stack.undo() is None


def test_undo_removes_last_ingest_when_no_finding():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.INGEST, ts=_ts(5), label="nmap xml ingest", data={}))
    stack = UndoStack(history=h)
    record = stack.undo()
    assert record.event.kind == EventKind.INGEST


def test_undo_record_replayable_from_timeline():
    h = EngagementHistory(tab_id="10.10.14.1")
    ev = TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="false positive", data={"severity": "HIGH"})
    h.append(ev)
    stack = UndoStack(history=h)
    record = stack.undo()
    # Replay: re-append the removed event
    h.append(record.event)
    assert len(h.events) == 1
    assert h.events[0].label == "false positive"


def test_undo_skips_non_undoable_kinds():
    """SCAN and SHELL events are not undoable — only FINDING, INGEST, CRED, NOTE."""
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.SHELL, ts=_ts(5), label="shell", data={}))
    stack = UndoStack(history=h)
    assert stack.undo() is None
