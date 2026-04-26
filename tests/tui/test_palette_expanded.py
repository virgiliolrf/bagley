"""Tests: expanded palette has at least 50 actions and fuzzy-finds key ones."""

import pytest
from bagley.tui.widgets.palette import ACTIONS, fuzzy_filter


def test_palette_has_at_least_50_actions():
    assert len(ACTIONS) >= 50, f"only {len(ACTIONS)} actions — need >=50"


def test_palette_has_all_mode_switches():
    labels = [label for label, _ in ACTIONS]
    for mode in ("recon", "enum", "exploit", "post", "privesc", "stealth", "osint", "report", "learn"):
        assert any(mode in l.lower() for l in labels), f"mode '{mode}' not found in palette"


def test_palette_has_tab_operations():
    labels = [label for label, _ in ACTIONS]
    assert any("new tab" in l.lower() for l in labels)
    assert any("close tab" in l.lower() for l in labels)


def test_palette_has_focus_actions():
    labels = [label for label, _ in ACTIONS]
    assert any("focus chat" in l.lower() for l in labels)
    assert any("focus hosts" in l.lower() for l in labels)


def test_palette_has_engine_swap_placeholder():
    labels = [label for label, _ in ACTIONS]
    assert any("engine" in l.lower() or "swap" in l.lower() for l in labels)


def test_palette_has_help_action():
    labels = [label for label, _ in ACTIONS]
    assert any("help" in l.lower() for l in labels)


def test_palette_has_disconnect():
    labels = [label for label, _ in ACTIONS]
    assert any("disconnect" in l.lower() for l in labels)


def test_palette_has_palette_playbook_stub():
    labels = [label for label, _ in ACTIONS]
    assert any("playbook" in l.lower() for l in labels)


def test_fuzzy_filter_returns_subset():
    results = fuzzy_filter("exploit", ACTIONS)
    assert len(results) > 0
    assert all("exploit" in label.lower() for label, _ in results)


def test_fuzzy_filter_empty_query_returns_all():
    results = fuzzy_filter("", ACTIONS)
    assert len(results) == len(ACTIONS)


def test_fuzzy_filter_partial_match():
    results = fuzzy_filter("rec", ACTIONS)
    # Should find "mode: recon" and similar
    assert any("rec" in label.lower() for label, _ in results)


def test_fuzzy_filter_no_match_returns_empty():
    results = fuzzy_filter("xyzzynonexistent999", ACTIONS)
    assert len(results) == 0
