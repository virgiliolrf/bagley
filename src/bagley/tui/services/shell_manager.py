"""ShellManager: spawn, background, foreground, close persistent shell sessions.

Each shell is identified by a unique *name* string (e.g. ``"rev-shell-1"``).
The manager keeps a registry of ``ShellRecord`` objects and delegates actual
I/O to the appropriate ``Bridge`` (PtyBridge on POSIX, SubprocessBridge on
Windows) via the ``_make_bridge`` factory so tests can mock it cleanly.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from bagley.tui.services.pty_bridge import Bridge, PtyBridge, SubprocessBridge


def _make_bridge(cmd: list[str]) -> Bridge:
    if sys.platform == "win32":
        return SubprocessBridge(cmd=cmd)
    return PtyBridge(cmd=cmd)


class ShellState(Enum):
    FOREGROUND = auto()
    BACKGROUND = auto()
    CLOSED = auto()


@dataclass
class ShellRecord:
    name: str
    tab_id: str
    cmd: list[str]
    state: ShellState
    bridge: Bridge
    uptime_start: float = field(default_factory=lambda: __import__("time").monotonic())


class ShellManager:
    """Singleton-style registry for live shell sessions.

    Instantiated once in ``BagleyApp`` and passed to ``ShellPane`` on creation.
    Not thread-safe; all calls must happen on the Textual event loop thread.
    """

    def __init__(self) -> None:
        self._registry: dict[str, ShellRecord] = {}

    def spawn(self, name: str, cmd: list[str], tab_id: str) -> ShellRecord:
        """Create and start a new shell, raising ValueError if name is taken."""
        if name in self._registry:
            raise ValueError(f"Shell name already in use: {name!r}")
        bridge = _make_bridge(cmd=cmd)
        bridge.start()
        record = ShellRecord(
            name=name, tab_id=tab_id, cmd=cmd,
            state=ShellState.FOREGROUND, bridge=bridge,
        )
        self._registry[name] = record
        return record

    def background(self, name: str) -> None:
        rec = self._get_or_raise(name)
        rec.state = ShellState.BACKGROUND

    def foreground(self, name: str) -> None:
        rec = self._get_or_raise(name)
        rec.state = ShellState.FOREGROUND

    def close(self, name: str) -> None:
        rec = self._get_or_raise(name)
        rec.bridge.close()
        rec.state = ShellState.CLOSED
        del self._registry[name]

    def get(self, name: str) -> Optional[ShellRecord]:
        return self._registry.get(name)

    def list_shells(self) -> list[ShellRecord]:
        return list(self._registry.values())

    def _get_or_raise(self, name: str) -> ShellRecord:
        rec = self._registry.get(name)
        if rec is None:
            raise KeyError(f"Unknown shell: {name!r}")
        return rec
