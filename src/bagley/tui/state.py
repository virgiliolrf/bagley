"""In-memory session state for the TUI."""

from __future__ import annotations

import platform
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OsInfo:
    system: str
    release: str
    distro: str
    shell: str
    eof: str
    pty_stream: bool


def detect_os() -> OsInfo:
    sysname = platform.system()
    release = platform.release()
    shell = "cmd.exe" if sysname == "Windows" else "/bin/sh"
    eof = "Ctrl+Z, Enter" if sysname == "Windows" else "Ctrl+D"
    distro = ""
    if sysname == "Linux":
        try:
            for line in Path("/etc/os-release").read_text().splitlines():
                if line.startswith("PRETTY_NAME="):
                    distro = line.split("=", 1)[1].strip().strip('"')
                    break
        except Exception:
            pass
    return OsInfo(
        system=sysname, release=release, distro=distro,
        shell=shell, eof=eof, pty_stream=sysname != "Windows",
    )


@dataclass
class TabState:
    id: str
    kind: str                         # "recon" | "target"
    chat: list[dict] = field(default_factory=list)
    react_history: list[dict] = field(default_factory=list)
    cmd_history: list[str] = field(default_factory=list)
    killchain_stage: int = 0
    creds: list[dict] = field(default_factory=list)
    notes_md: str = ""


@dataclass
class AppState:
    os_info: OsInfo
    scope_cidrs: tuple[str, ...] = ()
    scope_hosts: frozenset[str] = field(default_factory=frozenset)
    mode: str = "RECON"
    engine_label: str = "stub"
    tabs: list[TabState] = field(default_factory=lambda: [TabState(id="recon", kind="recon")])
    active_tab: int = 0
    voice_state: str = "off"
    unread_alerts: int = 0
    turn: int = 0
