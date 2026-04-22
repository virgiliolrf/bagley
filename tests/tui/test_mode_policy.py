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


from bagley.tui.modes.persona import mode_system_suffix


def test_persona_returns_string_for_each_mode():
    from bagley.tui.modes import MODES
    for m in MODES:
        suffix = mode_system_suffix(m.name)
        assert isinstance(suffix, str)
        assert len(suffix) > 0


def test_persona_exploit_is_aggressive():
    suffix = mode_system_suffix("EXPLOIT")
    assert "aggressive" in suffix.lower() or "exploit" in suffix.lower()


def test_persona_recon_mentions_readonly():
    suffix = mode_system_suffix("RECON")
    assert "read-only" in suffix.lower() or "cautious" in suffix.lower()


def test_persona_unknown_mode_raises():
    with pytest.raises(KeyError):
        mode_system_suffix("NONEXISTENT")
