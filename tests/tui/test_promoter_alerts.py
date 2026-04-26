"""Promoter event → correct alert severity mapping."""
import tempfile
import pytest
from bagley.memory.store import MemoryStore, Finding
from bagley.tui.services.memory_promoter import MemoryPromoter
from bagley.tui.services.alerts import AlertBus, Alert, Severity
from bagley.tui.panels.chat import _promoter_event_to_alert


def _fresh_store():
    return MemoryStore(tempfile.mktemp(suffix=".db"))


def test_cve_event_maps_to_crit():
    a = _promoter_event_to_alert("cve_match", "CVE-2021-44228")
    assert a.severity == Severity.CRIT
    assert "CRITICAL" in a.title.upper() or "FINDING" in a.title.upper()


def test_shell_event_maps_to_crit():
    a = _promoter_event_to_alert("shell_obtained", "10.0.0.1")
    assert a.severity == Severity.CRIT
    assert "SHELL" in a.title.upper()


def test_new_cred_maps_to_warn():
    a = _promoter_event_to_alert("new_cred", "admin:***")
    assert a.severity == Severity.WARN
    assert "CRED" in a.title.upper()


def test_new_host_maps_to_info():
    a = _promoter_event_to_alert("new_host", "10.0.0.5")
    assert a.severity == Severity.INFO
    assert "memory" in a.title.lower() or "saved" in a.title.lower()


def test_new_port_maps_to_info():
    a = _promoter_event_to_alert("new_port", "80/tcp http")
    assert a.severity == Severity.INFO


def test_unknown_event_falls_back_to_info():
    a = _promoter_event_to_alert("some_future_event", "detail")
    assert a.severity == Severity.INFO
