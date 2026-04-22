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


# ---- MemoryPromoter tests ----

from bagley.tui.services.memory_promoter import MemoryPromoter


def test_promoter_detects_new_host():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Host 192.168.1.50 is up (latency 0.1s).", s, current_host=None)
    assert any(e[0] == "new_host" and "192.168.1.50" in e[1] for e in events)
    hosts = s.list_hosts()
    assert any(h["ip"] == "192.168.1.50" for h in hosts)
    s.close()


def test_promoter_detects_open_port():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("80/tcp open http Apache 2.4.49", s, current_host="10.0.0.1")
    assert any(e[0] == "new_port" for e in events)
    detail = s.host_detail("10.0.0.1")
    assert any(r["port"] == 80 for r in detail["ports"])
    s.close()


def test_promoter_detects_cve():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Vulnerable to CVE-2021-44228 (log4j RCE).", s, current_host="10.0.0.1")
    assert any(e[0] == "cve_match" and "CVE-2021-44228" in e[1] for e in events)
    findings = s.list_findings_by_severity("critical")
    assert any("CVE-2021-44228" in f["cve"] for f in findings)
    s.close()


def test_promoter_detects_credential():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Found credential: admin:Password123!", s, current_host="10.0.0.1")
    assert any(e[0] == "new_cred" for e in events)
    s.close()


def test_promoter_detects_shell_obtained():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Shell obtained on 10.0.0.1. Meterpreter session 1 opened.", s, current_host="10.0.0.1")
    assert any(e[0] == "shell_obtained" for e in events)
    s.close()


def test_promoter_silent_on_empty_text():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("", s, current_host=None)
    assert events == []
    s.close()
