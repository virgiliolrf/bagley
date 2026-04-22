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


from bagley.tui.modes.policy import apply_mode_to_loop
from bagley.agent.loop import ReActLoop
from bagley.persona import DEFAULT_SYSTEM


class _StubEng:
    def generate(self, messages, **kw):
        from bagley.inference.engine import stub_response
        last = next((m for m in reversed(messages) if m["role"] == "user"), None)
        return stub_response(last["content"] if last else "")


def _make_loop() -> ReActLoop:
    return ReActLoop(engine=_StubEng(), auto_approve=True, max_steps=1)


def test_apply_mode_sets_confirm_fn_explicit():
    loop = _make_loop()
    apply_mode_to_loop(loop, "EXPLOIT")
    # EXPLOIT confirm_policy=explicit → confirm_fn must NOT auto-approve
    assert loop.auto_approve is False


def test_apply_mode_sets_confirm_fn_auto():
    loop = _make_loop()
    apply_mode_to_loop(loop, "RECON")
    # RECON confirm_policy=auto → auto_approve stays True
    assert loop.auto_approve is True


def test_apply_mode_sets_persona_attribute():
    loop = _make_loop()
    apply_mode_to_loop(loop, "OSINT")
    assert hasattr(loop, "_mode_name")
    assert loop._mode_name == "OSINT"


def test_apply_mode_report_blocks_shell():
    """REPORT allowlist is empty: any shell cmd must be blocked."""
    loop = _make_loop()
    apply_mode_to_loop(loop, "REPORT")
    # confirm_fn returns False for REPORT (no exec allowed)
    assert loop.confirm_fn("ls /") is False


def test_apply_mode_exploit_allowlist_blocks_unknown():
    loop = _make_loop()
    apply_mode_to_loop(loop, "EXPLOIT")
    # nmap is NOT in EXPLOIT allowlist → should be blocked
    assert loop.confirm_fn("nmap -sV 10.10.10.10") is False


def test_apply_mode_learn_inherits_none_allowlist():
    loop = _make_loop()
    apply_mode_to_loop(loop, "LEARN")
    # LEARN allowlist=None → no allowlist restriction; confirm_fn uses explicit policy
    assert loop.auto_approve is False
    # A random command is not blocked by allowlist
    assert loop.confirm_fn("echo hello") is False  # explicit: always False in non-interactive


def test_apply_mode_recon_allowlist_blocks_hydra():
    loop = _make_loop()
    apply_mode_to_loop(loop, "RECON")
    # hydra not in RECON allowlist → blocked
    assert loop.confirm_fn("hydra -l admin 10.10.10.10") is False
