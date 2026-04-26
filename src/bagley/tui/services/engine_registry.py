"""Enumerate available Bagley inference engines.

Sources:
  1. LOCAL - directories in `runs/` that contain `adapter_config.json`.
  2. OLLAMA - models returned by `GET http://localhost:11434/api/tags`.
  3. STUB  - always present as a safe fallback.

Usage:
    engines = list_engines(
        runs_dir=Path("./runs"),
        ollama_host="http://localhost:11434",
    )
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _default_ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://localhost:11434")


class EngineKind(str, enum.Enum):
    LOCAL = "local"
    OLLAMA = "ollama"
    STUB = "stub"


@dataclass
class EngineEntry:
    label: str
    kind: EngineKind
    path: Optional[Path] = None      # adapter dir for LOCAL; None otherwise
    ollama_name: Optional[str] = None  # "bagley:latest" etc. for OLLAMA


def _discover_local(runs_dir: Path) -> list[EngineEntry]:
    """Return adapter dirs that contain adapter_config.json."""
    entries: list[EngineEntry] = []
    if not runs_dir.is_dir():
        return entries
    for sub in sorted(runs_dir.iterdir()):
        if sub.is_dir() and (sub / "adapter_config.json").exists():
            entries.append(EngineEntry(label=sub.name, kind=EngineKind.LOCAL, path=sub))
    return entries


def _discover_ollama(host: str) -> list[EngineEntry]:
    """Query Ollama /api/tags. Returns [] on any failure."""
    try:
        import requests
        r = requests.get(f"{host}/api/tags", timeout=3.0)
        if r.status_code != 200:
            return []
        data = r.json()
        return [
            EngineEntry(
                label=m["name"],
                kind=EngineKind.OLLAMA,
                ollama_name=m["name"],
            )
            for m in data.get("models", [])
        ]
    except Exception:
        return []


def list_engines(
    runs_dir: Optional[Path] = None,
    ollama_host: Optional[str] = None,
) -> list[EngineEntry]:
    """Return all available engines.

    Order: LOCAL (sorted by name) -> OLLAMA -> STUB.
    """
    if runs_dir is None:
        runs_dir = Path("./runs")
    if ollama_host is None:
        ollama_host = _default_ollama_host()

    engines: list[EngineEntry] = []
    engines.extend(_discover_local(runs_dir))

    if ollama_host:
        engines.extend(_discover_ollama(ollama_host))

    engines.append(EngineEntry(label="stub", kind=EngineKind.STUB))
    return engines
