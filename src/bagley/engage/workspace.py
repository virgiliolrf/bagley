"""Engagement workspace — filesystem auto-organizado por engagement.

Layout:
    ~/.bagley/engagements/<slug>/
        manifest.json          # scope, objective, dates, tools allowed
        scans/                 # nmap/gobuster/etc output
        loot/                  # extracted files
        creds/                 # discovered credentials (encrypted at rest future)
        shells/                # shell sessions, transcripts
        notes.md               # operator notes
        audit.log              # every tool invocation
        memory.db              # SQLite — hosts, findings, attempted, references

CLI:
    bagley engage new <slug> --scope 10.10.0.0/16 --objective "get user flag"
    bagley engage list
    bagley engage use <slug>           # sets CURRENT_ENGAGEMENT env var
    bagley engage close [<slug>]
    bagley engage report <slug>        # markdown summary of findings

Integrates with ReActLoop — when engagement active, tool executions auto-log to scans/,
audit_log includes engagement slug, memory writes to engagement's memory.db.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("BAGLEY_ENGAGE_ROOT", str(Path.home() / ".bagley" / "engagements")))


@dataclass
class Manifest:
    slug: str
    scope: list[str] = field(default_factory=list)          # CIDRs / hostnames
    objective: str = ""
    created_at: str = ""
    closed_at: str | None = None
    success_markers: list[str] = field(default_factory=list)
    tools_allowed: list[str] = field(default_factory=lambda: ["shell", "browser", "research"])
    success: bool | None = None                              # set on close if objective met


@dataclass
class Engagement:
    slug: str
    root: Path

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.json"

    @property
    def memory_db_path(self) -> Path:
        return self.root / "memory.db"

    @property
    def audit_log_path(self) -> Path:
        return self.root / "audit.log"

    def load_manifest(self) -> Manifest:
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return Manifest(**data)

    def save_manifest(self, m: Manifest) -> None:
        self.manifest_path.write_text(json.dumps(asdict(m), indent=2), encoding="utf-8")

    def audit(self, entry: str) -> None:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(f"{dt.datetime.now().isoformat()} {entry}\n")

    def subdir(self, name: str) -> Path:
        p = self.root / name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def store_scan_output(self, command: str, output: str) -> Path:
        ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_cmd = "".join(c if c.isalnum() else "_" for c in command)[:40]
        scans = self.subdir("scans")
        path = scans / f"{ts}_{safe_cmd}.txt"
        path.write_text(f"# cmd: {command}\n{output}", encoding="utf-8")
        return path


def _slugify(s: str) -> str:
    return "".join(c if c.isalnum() or c == "-" else "_" for c in s.lower()).strip("_") or "unnamed"


def create(slug: str, scope: list[str] | None = None, objective: str = "",
           success_markers: list[str] | None = None) -> Engagement:
    slug = _slugify(slug)
    root = ROOT / slug
    if root.exists():
        raise FileExistsError(f"engagement '{slug}' already exists at {root}")
    root.mkdir(parents=True)
    for sub in ("scans", "loot", "creds", "shells"):
        (root / sub).mkdir()
    (root / "notes.md").write_text(f"# {slug}\n\nCreated: {dt.datetime.now().isoformat()}\n\n## Objective\n{objective or '(not set)'}\n\n## Notes\n", encoding="utf-8")
    eng = Engagement(slug=slug, root=root)
    m = Manifest(
        slug=slug, scope=scope or [], objective=objective,
        created_at=dt.datetime.now().isoformat(),
        success_markers=success_markers or _DEFAULT_SUCCESS_MARKERS.copy(),
    )
    eng.save_manifest(m)
    eng.audit("ENGAGE_CREATED")
    return eng


def load(slug: str) -> Engagement:
    slug = _slugify(slug)
    root = ROOT / slug
    if not root.exists():
        raise FileNotFoundError(f"no engagement '{slug}' at {root}")
    return Engagement(slug=slug, root=root)


def list_all() -> list[tuple[str, Manifest]]:
    if not ROOT.exists():
        return []
    out = []
    for entry in sorted(ROOT.iterdir()):
        if entry.is_dir() and (entry / "manifest.json").exists():
            eng = Engagement(slug=entry.name, root=entry)
            try:
                out.append((entry.name, eng.load_manifest()))
            except Exception:
                continue
    return out


def close(slug: str, success: bool | None = None) -> Engagement:
    eng = load(slug)
    m = eng.load_manifest()
    m.closed_at = dt.datetime.now().isoformat()
    m.success = success
    eng.save_manifest(m)
    eng.audit(f"ENGAGE_CLOSED success={success}")
    return eng


def get_current() -> Engagement | None:
    slug = os.environ.get("BAGLEY_CURRENT_ENGAGEMENT")
    if not slug:
        return None
    try:
        return load(slug)
    except FileNotFoundError:
        return None


_DEFAULT_SUCCESS_MARKERS = [
    r"flag\{[^}]+\}",
    r"uid=0\([^)]*root\)",
    r"NT AUTHORITY\\SYSTEM",
    r"KEY FOUND",
    r"Meterpreter session \d+ opened",
    r"root:x:0:0",
]
