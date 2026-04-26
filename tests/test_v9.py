"""v9 module smoke tests — engagement workspace, memory store, browser allowlist, research gap detection."""

import os
import tempfile
from pathlib import Path

import pytest

from bagley.tools.browser import _host_allowed
from bagley.research.agent import detect_knowledge_gap


def test_browser_allowlist_whitelisted():
    assert _host_allowed("https://exploit-db.com/exploits/50000")
    assert _host_allowed("https://book.hacktricks.xyz/linux-hardening")
    assert _host_allowed("https://raw.githubusercontent.com/x/y/main/z.md")
    assert _host_allowed("https://www.reddit.com/r/netsec")


def test_browser_allowlist_blocked():
    assert not _host_allowed("https://evil.com/malware")
    assert not _host_allowed("https://attacker-controlled.net")
    assert not _host_allowed("https://random-site.xyz")


def test_gap_detection_positive():
    assert detect_knowledge_gap("I have no record of that CVE.")
    assert detect_knowledge_gap("Not familiar with the Foo-Bar technique.")
    assert detect_knowledge_gap("I don't recognize that tool.")


def test_gap_detection_negative():
    assert not detect_knowledge_gap("CVE-2021-41773 is Apache path traversal. Use curl --path-as-is.")
    assert not detect_knowledge_gap("Run nmap -sV -sC on the target.")


def test_memory_store_basic_flow(tmp_path):
    from bagley.memory.store import MemoryStore, Finding

    db = tmp_path / "mem.db"
    store = MemoryStore(db)
    try:
        store.add_host("10.10.10.5", hostname="target.thm")
        store.add_port("10.10.10.5", 22, "tcp", "ssh", "OpenSSH 7.2")
        store.add_port("10.10.10.5", 80, "tcp", "http", "Apache 2.4.49")
        store.add_cred("10.10.10.5", "ssh", "admin", "Summer2024!", source="hydra", validated=True)
        store.add_finding(Finding(
            host="10.10.10.5", severity="critical", category="RCE",
            summary="CVE-2021-41773 path traversal → RCE", cve="CVE-2021-41773",
        ))
        store.add_attempt("10.10.10.5", "responder_poison", "responder", "fail",
                          details="SMB signing required")

        summary = store.host_summary("10.10.10.5")
        assert summary["host"]["ip"] == "10.10.10.5"
        assert len(summary["ports"]) == 2
        assert len(summary["findings"]) == 1
        assert summary["findings"][0]["cve"] == "CVE-2021-41773"
        assert len(summary["recent_attempts"]) == 1

        attempts = store.attempted("10.10.10.5")
        assert attempts[0]["outcome"] == "fail"
    finally:
        store.close()


def test_engagement_workspace_lifecycle():
    from bagley.engage import workspace

    # isolate root pra não poluir ~/.bagley
    with tempfile.TemporaryDirectory() as tmp:
        workspace.ROOT = Path(tmp)
        eng = workspace.create("test-acme", scope=["10.10.0.0/16"],
                                objective="get user flag")
        assert eng.slug == "test-acme"
        assert (eng.root / "manifest.json").exists()
        assert (eng.root / "scans").exists()
        assert (eng.root / "loot").exists()

        m = eng.load_manifest()
        assert m.scope == ["10.10.0.0/16"]
        assert m.objective == "get user flag"
        assert len(m.success_markers) > 0

        path = eng.store_scan_output("nmap -sV 10.10.10.5",
                                       "22/tcp open ssh\n80/tcp open http")
        assert path.exists()
        assert "22/tcp" in path.read_text()

        all_engs = workspace.list_all()
        assert len(all_engs) == 1
        assert all_engs[0][0] == "test-acme"

        eng2 = workspace.close("test-acme", success=True)
        m2 = eng2.load_manifest()
        assert m2.closed_at is not None
        assert m2.success is True


def test_memory_vector_similarity(tmp_path):
    from bagley.memory.store import MemoryStore

    db = tmp_path / "mem.db"
    store = MemoryStore(db)
    try:
        # Vetores fake ortogonais + um parecido
        store.add_vector("research", "ref1", "apache path traversal",
                          embedding=[1.0, 0.0, 0.0])
        store.add_vector("research", "ref2", "ssh brute force",
                          embedding=[0.0, 1.0, 0.0])
        store.add_vector("research", "ref3", "apache path",
                          embedding=[0.95, 0.05, 0.0])

        results = store.similar([1.0, 0.0, 0.0], k=2)
        assert len(results) == 2
        assert results[0]["ref_id"] == "ref1"
        assert results[1]["ref_id"] == "ref3"
        assert results[0]["score"] > results[1]["score"]
    finally:
        store.close()


def test_slugify_engagement():
    from bagley.engage.workspace import _slugify

    assert _slugify("ACME Corp Pentest") == "acme_corp_pentest"
    assert _slugify("htb-lame") == "htb-lame"
    assert _slugify("!!!") == "unnamed"
