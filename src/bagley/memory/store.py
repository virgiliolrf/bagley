"""Persistent memory SQLite + embeddings.

Schema:
    hosts        (ip PK, hostname, first_seen, notes_md)
    ports        (host, port, proto, service, version, detected_at)
    creds        (id PK, host, service, username, credential, source, validated)
    findings     (id PK, host, severity, category, summary, evidence_path, cve)
    attempts     (id PK, host, technique, tool, outcome, ts, details)
    vectors      (id PK, kind, ref_id, text, embedding BLOB)   # RAG index

Usage:
    store = MemoryStore(engagement.memory_db_path)
    store.add_host("10.10.10.5", hostname="target.thm")
    store.add_finding(host="10.10.10.5", severity="high", category="RCE", ...)
    related = store.similar("apache 2.4.49 path traversal", k=5)
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS hosts (
    ip TEXT PRIMARY KEY,
    hostname TEXT,
    first_seen TEXT,
    notes_md TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS ports (
    host TEXT,
    port INTEGER,
    proto TEXT,
    service TEXT,
    version TEXT,
    detected_at TEXT,
    PRIMARY KEY (host, port, proto),
    FOREIGN KEY (host) REFERENCES hosts(ip)
);
CREATE TABLE IF NOT EXISTS creds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT,
    service TEXT,
    username TEXT,
    credential TEXT,
    source TEXT,
    validated INTEGER DEFAULT 0,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT,
    severity TEXT,
    category TEXT,
    summary TEXT,
    evidence_path TEXT,
    cve TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT,
    technique TEXT,
    tool TEXT,
    outcome TEXT,     -- success|fail|partial|skipped
    ts TEXT,
    details TEXT
);
CREATE TABLE IF NOT EXISTS vectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT,        -- finding|host_summary|research|trace
    ref_id TEXT,
    text TEXT,
    embedding BLOB,
    created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_attempts_host ON attempts(host);
CREATE INDEX IF NOT EXISTS idx_findings_host ON findings(host);
CREATE INDEX IF NOT EXISTS idx_ports_host ON ports(host);
CREATE TABLE IF NOT EXISTS sessions (
    id        TEXT PRIMARY KEY,
    tab_id    TEXT NOT NULL,
    method    TEXT NOT NULL,
    started   REAL NOT NULL,
    ended     REAL,
    uptime_s  REAL
);
"""


# ── Sessions (persistent shells) ──────────────────────────────────────────────

def init_sessions_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id        TEXT PRIMARY KEY,
            tab_id    TEXT NOT NULL,
            method    TEXT NOT NULL,
            started   REAL NOT NULL,
            ended     REAL,
            uptime_s  REAL
        )
    """)
    conn.commit()


def upsert_session(conn, *, id: str, tab_id: str, method: str, started: float) -> None:
    conn.execute(
        """INSERT INTO sessions (id, tab_id, method, started)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET method=excluded.method""",
        (id, tab_id, method, started),
    )
    conn.commit()


def close_session(conn, *, id: str, ended: float) -> None:
    conn.execute(
        "UPDATE sessions SET ended=?, uptime_s=ended-started WHERE id=?",
        (ended, id),
    )
    conn.commit()


def list_sessions(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT id, tab_id, method, started, ended, uptime_s FROM sessions ORDER BY started DESC"
    ).fetchall()
    return [
        {"id": r[0], "tab_id": r[1], "method": r[2],
         "started": r[3], "ended": r[4], "uptime_s": r[5]}
        for r in rows
    ]


@dataclass
class Finding:
    host: str
    severity: str
    category: str
    summary: str
    evidence_path: str = ""
    cve: str = ""


class MemoryStore:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(str(self.db_path))
        self.con.row_factory = sqlite3.Row
        self.con.executescript(SCHEMA)
        self.con.commit()

    # ---- writes ----
    def add_host(self, ip: str, hostname: str = "", notes_md: str = "") -> None:
        self.con.execute(
            "INSERT OR IGNORE INTO hosts(ip, hostname, first_seen, notes_md) VALUES (?, ?, ?, ?)",
            (ip, hostname, dt.datetime.now().isoformat(), notes_md),
        )
        self.con.commit()

    def add_port(self, host: str, port: int, proto: str = "tcp",
                 service: str = "", version: str = "") -> None:
        self.add_host(host)
        self.con.execute(
            "INSERT OR REPLACE INTO ports(host, port, proto, service, version, detected_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (host, port, proto, service, version, dt.datetime.now().isoformat()),
        )
        self.con.commit()

    def add_cred(self, host: str, service: str, username: str, credential: str,
                 source: str = "", validated: bool = False) -> int:
        self.add_host(host)
        cur = self.con.execute(
            "INSERT INTO creds(host, service, username, credential, source, validated, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (host, service, username, credential, source, int(validated),
             dt.datetime.now().isoformat()),
        )
        self.con.commit()
        return cur.lastrowid

    def add_finding(self, f: Finding) -> int:
        self.add_host(f.host)
        cur = self.con.execute(
            "INSERT INTO findings(host, severity, category, summary, evidence_path, cve, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f.host, f.severity, f.category, f.summary, f.evidence_path, f.cve,
             dt.datetime.now().isoformat()),
        )
        self.con.commit()
        return cur.lastrowid

    def add_attempt(self, host: str, technique: str, tool: str, outcome: str,
                    details: str = "") -> int:
        self.add_host(host)
        cur = self.con.execute(
            "INSERT INTO attempts(host, technique, tool, outcome, ts, details) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (host, technique, tool, outcome, dt.datetime.now().isoformat(), details),
        )
        self.con.commit()
        return cur.lastrowid

    # ---- reads ----
    def host_summary(self, ip: str) -> dict:
        h = self.con.execute("SELECT * FROM hosts WHERE ip = ?", (ip,)).fetchone()
        if not h:
            return {}
        ports = self.con.execute("SELECT port, proto, service, version FROM ports WHERE host = ?", (ip,)).fetchall()
        findings = self.con.execute("SELECT severity, category, summary, cve, evidence_path FROM findings WHERE host = ?", (ip,)).fetchall()
        attempts = self.con.execute(
            "SELECT technique, tool, outcome, details FROM attempts WHERE host = ? ORDER BY ts DESC LIMIT 20",
            (ip,)).fetchall()
        return {
            "host": dict(h),
            "ports": [dict(p) for p in ports],
            "findings": [dict(f) for f in findings],
            "recent_attempts": [dict(a) for a in attempts],
        }

    def attempted(self, host: str) -> list[dict]:
        return [dict(r) for r in self.con.execute(
            "SELECT technique, tool, outcome FROM attempts WHERE host = ?", (host,)
        ).fetchall()]

    def list_findings(self, severity: str | None = None) -> list[dict]:
        if severity:
            q = self.con.execute(
                "SELECT * FROM findings WHERE severity = ? ORDER BY created_at DESC", (severity,))
        else:
            q = self.con.execute("SELECT * FROM findings ORDER BY created_at DESC")
        return [dict(r) for r in q.fetchall()]

    def list_findings_by_severity(self, severity: str) -> list[dict]:
        """Return all findings matching *severity* (case-insensitive), newest first."""
        rows = self.con.execute(
            "SELECT * FROM findings WHERE LOWER(severity) = LOWER(?) ORDER BY created_at DESC",
            (severity,),
        ).fetchall()
        return [dict(r) for r in rows]

    def recent_attempts(self, n: int = 20) -> list[dict]:
        """Return the *n* most-recent attempt rows across all hosts, newest first."""
        rows = self.con.execute(
            "SELECT * FROM attempts ORDER BY ts DESC LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- embeddings / RAG ----
    def add_vector(self, kind: str, ref_id: str, text: str, embedding: list[float]) -> int:
        blob = struct.pack(f"{len(embedding)}f", *embedding)
        cur = self.con.execute(
            "INSERT INTO vectors(kind, ref_id, text, embedding, created_at) VALUES (?, ?, ?, ?, ?)",
            (kind, ref_id, text, blob, dt.datetime.now().isoformat()),
        )
        self.con.commit()
        return cur.lastrowid

    def similar(self, query_embedding: list[float], k: int = 5,
                kind_filter: str | None = None) -> list[dict]:
        """Brute-force cosine similarity. Fast enough for <10k vectors; swap for qdrant later."""
        import math
        sql = "SELECT id, kind, ref_id, text, embedding FROM vectors"
        params: tuple = ()
        if kind_filter:
            sql += " WHERE kind = ?"
            params = (kind_filter,)
        rows = self.con.execute(sql, params).fetchall()
        if not rows:
            return []
        q_norm = math.sqrt(sum(x * x for x in query_embedding))
        if q_norm == 0:
            return []
        scored = []
        for r in rows:
            blob = r["embedding"]
            n = len(blob) // 4
            if n != len(query_embedding):
                continue
            emb = struct.unpack(f"{n}f", blob)
            dot = sum(a * b for a, b in zip(emb, query_embedding))
            e_norm = math.sqrt(sum(x * x for x in emb))
            if e_norm == 0:
                continue
            score = dot / (q_norm * e_norm)
            scored.append((score, dict(r)))
        scored.sort(key=lambda kv: -kv[0])
        return [{"score": s, **d} for s, d in scored[:k]]

    # ---- convenience aliases (TUI / task-spec API) ----
    def upsert_host(self, ip: str, state: str = "up", hostname: str = "") -> None:
        """Insert or update a host record with an optional state field.

        The schema stores no 'state' column; state is recorded in notes_md
        as a lightweight convention so the hosts table stays schema-stable.
        """
        self.con.execute(
            "INSERT OR IGNORE INTO hosts(ip, hostname, first_seen, notes_md) VALUES (?, ?, ?, ?)",
            (ip, hostname, dt.datetime.now().isoformat(), f"state:{state}"),
        )
        self.con.execute(
            "UPDATE hosts SET notes_md = ? WHERE ip = ? AND notes_md NOT LIKE 'state:%'",
            (f"state:{state}", ip),
        )
        self.con.commit()

    def list_hosts(self) -> list[dict]:
        """Return all hosts as dicts with 'ip' and 'state' keys."""
        rows = self.con.execute("SELECT ip, notes_md FROM hosts ORDER BY first_seen").fetchall()
        result = []
        for r in rows:
            notes = r["notes_md"] or ""
            state = "up"
            for part in notes.split(";"):
                part = part.strip()
                if part.startswith("state:"):
                    state = part[len("state:"):]
                    break
            result.append({"ip": r["ip"], "state": state})
        return result

    def host_detail(self, ip: str) -> dict:
        """Return ports and findings for a host (subset of host_summary)."""
        summary = self.host_summary(ip)
        if not summary:
            return {"ports": [], "findings": []}
        return {"ports": summary.get("ports", []), "findings": summary.get("findings", [])}

    def close(self) -> None:
        self.con.close()
