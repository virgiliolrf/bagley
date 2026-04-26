"""Tests for EngagementHistory snapshot diffs."""
import datetime
import pytest
from bagley.tui.services.history import EngagementHistory, TimelineEvent, EventKind


def _ts(offset_s: int = 0) -> datetime.datetime:
    base = datetime.datetime(2026, 4, 26, 12, 0, 0)
    return base + datetime.timedelta(seconds=offset_s)


def test_append_and_list():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="nmap -sV 10.10.14.1", data={"ports": [22, 80]}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="CVE-2021-41773", data={"severity": "CRIT"}))
    assert len(h.events) == 2


def test_snapshot_at_returns_events_up_to_ts():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.CRED, ts=_ts(20), label="admin:password", data={}))
    h.append(TimelineEvent(kind=EventKind.SHELL, ts=_ts(40), label="shell@10.10.14.1", data={}))
    snap = h.snapshot_at(_ts(25))
    assert len(snap) == 2
    assert snap[-1].kind == EventKind.CRED


def test_diff_between_two_snapshots():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="finding1", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(20), label="finding2", data={}))
    diff = h.diff(_ts(10), _ts(20))
    assert len(diff.added) == 1
    assert diff.added[0].label == "finding2"
    assert diff.removed == []


def test_remove_last_event():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(0), label="false positive", data={}))
    removed = h.remove_last(kind=EventKind.FINDING)
    assert removed.label == "false positive"
    assert len(h.events) == 0


def test_remove_last_returns_none_when_empty():
    h = EngagementHistory(tab_id="10.10.14.1")
    assert h.remove_last(kind=EventKind.FINDING) is None
