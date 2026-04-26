"""ObserveService: /observe pid <N> handler.

Thin adapter around ``src/bagley/observe/terminal.py``. The tap object is
accessed via ``_get_tap()`` so tests can patch it without importing the
real terminal module (which may require OS-level capabilities on Linux).

Usage (from TUI slash command handler):
    svc = ObserveService()
    svc.attach(pid=1234)          # start streaming
    chunk = svc.read_chunk()      # bytes or b""
    svc.stop()                    # detach
"""
from __future__ import annotations

from typing import Optional


class ObserveError(Exception):
    """Raised for illegal ObserveService state transitions."""


def _get_tap():
    """Return the singleton terminal tap object from observe/terminal.py.

    Isolated in a function so tests can patch ``bagley.tui.services.observe._get_tap``
    without importing the real terminal module.
    """
    from bagley.observe.terminal import get_tap  # type: ignore[import]
    return get_tap()


class ObserveService:
    """Manages a single /observe session.

    Only one external terminal can be observed at a time. Attach, stream,
    and detach. The read_chunk() method is called by the TUI read loop
    (same pattern as PtyBridge.read) and feeds bytes into the read-only
    ObservePane which then runs the smart-paste classifier.
    """

    def __init__(self) -> None:
        self._attached_pid: Optional[int] = None

    @property
    def is_active(self) -> bool:
        return self._attached_pid is not None

    def attach(self, pid: int) -> None:
        tap = _get_tap()
        if tap.is_active():
            raise ObserveError("already attached to a terminal; call /observe stop first")
        tap.attach(pid)
        self._attached_pid = pid

    def stop(self) -> None:
        tap = _get_tap()
        if not tap.is_active():
            return
        tap.detach()
        self._attached_pid = None

    def read_chunk(self) -> bytes:
        if not self.is_active:
            return b""
        tap = _get_tap()
        return tap.read_chunk()
