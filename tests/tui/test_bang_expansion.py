"""Tests for bang re-exec expansion: !!, !N, !prefix."""

import pytest

from bagley.tui.interactions.bang import BangExpander, BangExpansionError


HISTORY = ["nmap -sV 10.0.0.1", "gobuster dir ...", "ping 10.0.0.1", "nmap -p 80 10.0.0.1"]


def test_double_bang_returns_last():
    exp = BangExpander(cmd_history=HISTORY)
    assert exp.expand("!!") == "nmap -p 80 10.0.0.1"


def test_bang_n_returns_nth():
    exp = BangExpander(cmd_history=HISTORY)
    # !1 == index 0 (1-based)
    assert exp.expand("!1") == "nmap -sV 10.0.0.1"
    assert exp.expand("!2") == "gobuster dir ..."
    assert exp.expand("!4") == "nmap -p 80 10.0.0.1"


def test_bang_prefix_returns_last_matching():
    exp = BangExpander(cmd_history=HISTORY)
    assert exp.expand("!nmap") == "nmap -p 80 10.0.0.1"
    assert exp.expand("!ping") == "ping 10.0.0.1"
    assert exp.expand("!gob") == "gobuster dir ..."


def test_bang_prefix_no_match_raises():
    exp = BangExpander(cmd_history=HISTORY)
    with pytest.raises(BangExpansionError, match="No command"):
        exp.expand("!zzz")


def test_bang_n_out_of_range_raises():
    exp = BangExpander(cmd_history=HISTORY)
    with pytest.raises(BangExpansionError, match="index"):
        exp.expand("!99")


def test_non_bang_string_returned_as_is():
    exp = BangExpander(cmd_history=HISTORY)
    assert exp.expand("hello world") == "hello world"
    assert exp.expand("!") == "!"   # bare ! is not a valid bang


def test_empty_history_double_bang_raises():
    exp = BangExpander(cmd_history=[])
    with pytest.raises(BangExpansionError, match="empty"):
        exp.expand("!!")
