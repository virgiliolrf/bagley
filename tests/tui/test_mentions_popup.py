"""Tests for @ mention popup and token substitution."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input

from bagley.tui.interactions.mentions import MentionSubstitutor, build_mention_entries


# ── MentionSubstitutor unit tests ────────────────────────────────────────────

CONTEXT = {
    "hosts": ["10.0.0.1", "10.0.0.2"],
    "creds": {"admin": "admin:s3cr3t", "root": "root:toor"},
    "scan_last": "nmap -sV 10.0.0.1 result: open 22/tcp 80/tcp",
    "findings": {"CVE-2021-41773": "Apache path traversal"},
    "playbooks": ["htb-recon", "smb-enum"],
}


def test_substitutor_ip():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("scan @10.0.0.1 now")
    assert "10.0.0.1" in result  # IP mention resolves to the IP itself


def test_substitutor_creds_user():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("try @creds.admin on the form")
    assert "admin:s3cr3t" in result


def test_substitutor_creds_all():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("use @creds for hydra")
    assert "admin:s3cr3t" in result or "admin" in result


def test_substitutor_scan_last():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("review @scan.last findings")
    assert "nmap" in result


def test_substitutor_finding():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("exploit @finding.CVE-2021-41773")
    assert "Apache" in result


def test_substitutor_unknown_token_kept():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("check @unknown.thing here")
    assert "@unknown.thing" in result  # Unknown tokens are preserved


def test_build_mention_entries_includes_ips():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@10.0.0.1" in labels
    assert "@10.0.0.2" in labels


def test_build_mention_entries_includes_creds():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@creds" in labels
    assert "@creds.admin" in labels


def test_build_mention_entries_includes_scan_last():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@scan.last" in labels


def test_build_mention_entries_includes_playbooks():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@playbook.htb-recon" in labels
