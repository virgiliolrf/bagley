"""Tests: mode wiring — allowlist, persona suffix, confirm policy."""

import pytest
from bagley.tui.modes import MODES, by_name, by_index


def test_all_modes_have_allowlist():
    for m in MODES:
        assert hasattr(m, "allowlist"), f"{m.name} missing allowlist"
        assert isinstance(m.allowlist, frozenset) or m.allowlist is None, f"{m.name}.allowlist must be frozenset or None"


def test_exploit_allowlist_contains_sqlmap():
    m = by_name("EXPLOIT")
    assert "sqlmap" in m.allowlist


def test_recon_allowlist_contains_nmap():
    m = by_name("RECON")
    assert "nmap" in m.allowlist


def test_report_allowlist_is_readonly():
    m = by_name("REPORT")
    # REPORT has no shell exec tools
    assert len(m.allowlist) == 0


def test_learn_allowlist_is_none_sentinel():
    # LEARN inherits caller's allowlist; sentinel is None
    m = by_name("LEARN")
    assert m.allowlist is None


def test_mode_index_ordering():
    for i, m in enumerate(MODES, start=1):
        assert m.index == i
