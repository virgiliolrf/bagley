"""Tests for the REPORT mode markdown/PDF generator.

Uses a seeded temporary SQLite (same schema as memory/store.py) plus
in-memory notes to verify the markdown output.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from bagley.tui.services.reporter import Reporter, ReportConfig


# ---------------------------------------------------------------------------
# Fixtures: seed a minimal MemoryStore-compatible SQLite
# ---------------------------------------------------------------------------

def _seed_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hosts (
            ip TEXT PRIMARY KEY, hostname TEXT, first_seen TEXT, notes_md TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS ports (
            host TEXT, port INTEGER, proto TEXT, service TEXT, version TEXT, detected_at TEXT,
            PRIMARY KEY (host, port, proto)
        );
        CREATE TABLE IF NOT EXISTS creds (
            id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, service TEXT,
            username TEXT, credential TEXT, source TEXT, validated INTEGER DEFAULT 0, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, severity TEXT,
            category TEXT, summary TEXT, evidence_path TEXT, cve TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, technique TEXT,
            tool TEXT, outcome TEXT, ts TEXT, details TEXT
        );
    """)
    conn.execute("INSERT INTO hosts VALUES ('10.10.14.5','target.thm','2026-04-27','test host')")
    conn.execute("INSERT INTO ports VALUES ('10.10.14.5',80,'tcp','http','Apache 2.4.49','2026-04-27')")
    conn.execute("INSERT INTO creds VALUES (NULL,'10.10.14.5','ssh','admin','password123','hydra',1,'2026-04-27')")
    conn.execute(
        "INSERT INTO findings VALUES "
        "(NULL,'10.10.14.5','critical','RCE','CVE-2021-41773 path traversal RCE',NULL,'CVE-2021-41773','2026-04-27')"
    )
    conn.execute(
        "INSERT INTO attempts VALUES "
        "(NULL,'10.10.14.5','path-traversal','curl','success','2026-04-27','poc worked')"
    )
    conn.commit()
    conn.close()


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db = tmp_path / "memory.db"
    _seed_db(db)
    return db


@pytest.fixture
def report_dir(tmp_path: Path) -> Path:
    d = tmp_path / "reports"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Markdown compilation
# ---------------------------------------------------------------------------

def test_report_contains_executive_summary_section(seeded_db, report_dir):
    notes = {"recon": "Initial recon complete. Target is Apache 2.4.49."}
    cfg = ReportConfig(db_path=seeded_db, notes=notes, output_dir=report_dir,
                       engagement="test-engagement")
    r = Reporter(cfg)
    md = r.compile()
    assert "# " in md
    assert "Executive Summary" in md or "executive" in md.lower()


def test_report_contains_hosts_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "10.10.14.5" in md
    assert "target.thm" in md


def test_report_contains_findings_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "critical" in md.lower() or "CRITICAL" in md
    assert "CVE-2021-41773" in md


def test_report_contains_creds_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "admin" in md
    assert "ssh" in md


def test_report_contains_timeline_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    # Timeline comes from attempts table
    assert "path-traversal" in md or "2026-04-27" in md


def test_report_saves_markdown_file(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    r = Reporter(cfg)
    r.compile()
    saved = r.save()
    assert saved.exists()
    assert saved.suffix == ".md"
    assert "test-engagement" in saved.name


def test_report_includes_notes_from_all_tabs(seeded_db, report_dir):
    notes = {
        "recon": "Scope is 10.10.14.0/24.",
        "10.10.14.5": "This host runs Apache 2.4.49 which is vuln to CVE-2021-41773.",
    }
    cfg = ReportConfig(db_path=seeded_db, notes=notes, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "Scope is 10.10.14.0/24" in md
    assert "CVE-2021-41773" in md


def test_pdf_skipped_gracefully_when_renderer_absent(seeded_db, report_dir, monkeypatch):
    """When neither weasyprint nor pandoc is available, save() returns .md only."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _: None)   # pretend nothing is installed

    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement", generate_pdf=True)
    r = Reporter(cfg)
    r.compile()
    saved = r.save()
    assert saved.suffix == ".md"     # PDF skipped; md saved
