"""Unit tests for the regex-based selection classifier."""

import pytest
from bagley.tui.interactions.selection import classify, ClassifyResult, SelectionType


# ── IPv4 ──────────────────────────────────────────────────────────────────────

def test_classify_ipv4_plain():
    r = classify("192.168.1.1")
    assert r.type == SelectionType.IPV4
    assert r.value == "192.168.1.1"


def test_classify_ipv4_with_cidr():
    r = classify("10.10.0.0/24")
    assert r.type == SelectionType.IPV4


def test_classify_ipv4_embedded_in_whitespace():
    r = classify("  172.16.0.5  ")
    assert r.type == SelectionType.IPV4


def test_classify_not_ipv4_too_large():
    r = classify("999.999.999.999")
    assert r.type != SelectionType.IPV4


# ── CVE ───────────────────────────────────────────────────────────────────────

def test_classify_cve_standard():
    r = classify("CVE-2021-44228")
    assert r.type == SelectionType.CVE
    assert r.value == "CVE-2021-44228"


def test_classify_cve_case_insensitive():
    r = classify("cve-2023-12345")
    assert r.type == SelectionType.CVE


def test_classify_cve_five_digit():
    r = classify("CVE-2024-123456")
    assert r.type == SelectionType.CVE


# ── MD5 ───────────────────────────────────────────────────────────────────────

def test_classify_md5_lowercase():
    r = classify("d41d8cd98f00b204e9800998ecf8427e")
    assert r.type == SelectionType.MD5


def test_classify_md5_uppercase():
    r = classify("D41D8CD98F00B204E9800998ECF8427E")
    assert r.type == SelectionType.MD5


def test_classify_not_md5_wrong_length():
    r = classify("d41d8cd98f00b204")
    assert r.type != SelectionType.MD5


# ── SHA256 ────────────────────────────────────────────────────────────────────

def test_classify_sha256():
    r = classify("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    assert r.type == SelectionType.SHA256


def test_classify_sha256_mixed_case():
    r = classify("E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855")
    assert r.type == SelectionType.SHA256


# ── URL ───────────────────────────────────────────────────────────────────────

def test_classify_url_http():
    r = classify("http://example.com/path")
    assert r.type == SelectionType.URL


def test_classify_url_https():
    r = classify("https://192.168.1.1:8443/admin")
    assert r.type == SelectionType.URL


def test_classify_url_ftp():
    r = classify("ftp://files.example.com")
    assert r.type == SelectionType.URL


# ── PORT ──────────────────────────────────────────────────────────────────────

def test_classify_port_tcp():
    r = classify("443/tcp")
    assert r.type == SelectionType.PORT


def test_classify_port_udp():
    r = classify("53/udp")
    assert r.type == SelectionType.PORT


# ── PATH ──────────────────────────────────────────────────────────────────────

def test_classify_absolute_path_linux():
    r = classify("/etc/passwd")
    assert r.type == SelectionType.PATH


def test_classify_absolute_path_windows():
    r = classify("C:\\Windows\\System32\\cmd.exe")
    assert r.type == SelectionType.PATH


# ── UNKNOWN ───────────────────────────────────────────────────────────────────

def test_classify_unknown_plain_text():
    r = classify("hello world")
    assert r.type == SelectionType.UNKNOWN


def test_classify_empty_string():
    r = classify("")
    assert r.type == SelectionType.UNKNOWN


# ── Priority ordering ─────────────────────────────────────────────────────────

def test_classify_priority_cve_over_unknown():
    # CVE in a sentence should still classify as CVE
    r = classify("Found CVE-2021-44228 in log4j")
    assert r.type == SelectionType.CVE


def test_classify_priority_url_over_ipv4():
    # A URL that contains an IP should be classified as URL
    r = classify("https://10.10.10.10/shell")
    assert r.type == SelectionType.URL


from bagley.tui.interactions.inspector_actions import actions_for, InspectorAction
from bagley.tui.interactions.selection import classify


def test_actions_for_ipv4_contains_nmap():
    result = classify("10.10.10.10")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("nmap" in l.lower() for l in labels)


def test_actions_for_cve_contains_searchsploit():
    result = classify("CVE-2021-44228")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("searchsploit" in l.lower() or "exploit" in l.lower() for l in labels)


def test_actions_for_md5_contains_crack():
    result = classify("d41d8cd98f00b204e9800998ecf8427e")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("crack" in l.lower() or "hashcat" in l.lower() for l in labels)


def test_actions_for_url_contains_dirb():
    result = classify("http://example.com")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("gobuster" in l.lower() or "dirb" in l.lower() or "ffuf" in l.lower() for l in labels)


def test_actions_for_unknown_has_send_to_chat():
    result = classify("some random text")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("chat" in l.lower() or "send" in l.lower() for l in labels)


def test_actions_each_have_command_string():
    result = classify("10.10.10.10")
    actions = actions_for(result)
    for a in actions:
        assert isinstance(a.label, str)
        assert isinstance(a.command, str)
        assert len(a.label) > 0
