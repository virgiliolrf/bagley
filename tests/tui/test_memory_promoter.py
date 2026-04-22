"""Tests for MemoryStore Phase-3 helpers."""
import tempfile
from pathlib import Path

import pytest
from bagley.memory.store import MemoryStore, Finding


def _fresh_store() -> MemoryStore:
    tmp = tempfile.mktemp(suffix=".db")
    return MemoryStore(tmp)


def test_list_findings_by_severity_returns_correct_subset():
    s = _fresh_store()
    s.add_finding(Finding("10.0.0.1", "critical", "RCE", "RCE via log4j"))
    s.add_finding(Finding("10.0.0.1", "high",     "SQLi", "blind SQLi"))
    s.add_finding(Finding("10.0.0.2", "high",     "XSS",  "stored XSS"))
    s.add_finding(Finding("10.0.0.3", "low",      "Info", "version disclosure"))

    crits = s.list_findings_by_severity("critical")
    highs = s.list_findings_by_severity("high")
    lows  = s.list_findings_by_severity("low")
    meds  = s.list_findings_by_severity("medium")

    assert len(crits) == 1
    assert crits[0]["category"] == "RCE"
    assert len(highs) == 2
    assert len(lows) == 1
    assert meds == []
    s.close()


def test_recent_attempts_returns_n_most_recent():
    s = _fresh_store()
    for i in range(5):
        s.add_attempt("10.0.0.1", f"tech{i}", "nmap", "fail")
    rows = s.recent_attempts(n=3)
    assert len(rows) == 3
    # most-recent first
    assert rows[0]["technique"] == "tech4"
    s.close()


def test_recent_attempts_default_n():
    s = _fresh_store()
    for i in range(25):
        s.add_attempt("10.0.0.1", f"t{i}", "tool", "success")
    rows = s.recent_attempts()
    assert len(rows) == 20   # default cap
    s.close()
