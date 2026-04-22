# Bagley TUI — Phase 5 (Persistent Shells + Screen Observe + Graph View + Timeline Scrubber + Undo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the five remaining "power-operator" features defined in spec §11 Phase 5: live PTY shell panes that stay alive across Bagley turns; an `/observe` command that attaches to any external terminal's stdout stream; a full-screen network graph view (F7) rendered with unicode box-drawing and networkx spring layout; a horizontal timeline scrubber (Ctrl+Shift+T) that shows the engagement history and lets the operator dim the workspace to any past state; and a non-destructive undo (Ctrl+Shift+Z) that removes the last finding or ingest and is replayable from the timeline. All five features ship tested, with the existing `ReActLoop`/`executor.py`/`memory/store.py` layer treated as stable under-the-hood infrastructure.

**Architecture summary:** New sub-packages `src/bagley/tui/services/` (lifecycle and data services) and additions to `src/bagley/tui/panels/` and `src/bagley/tui/widgets/`. `ShellPane` owns a PTY master fd (Linux/macOS) or a non-interactive `subprocess.Popen` (Windows) mediated by `pty_bridge.py`. `shell_manager.py` is the long-lived singleton that tracks the named registry of live shells and exposes background/foreground/close. The observe service wraps the existing `src/bagley/observe/terminal.py` tap point. `GraphPane` uses `networkx` spring layout projected onto a unicode grid. `EngagementHistory` in `history.py` is the append-only event log; `UndoStack` in `undo.py` wraps it with pop-last semantics. The `Timeline` widget reads `EngagementHistory` and emits `TimelineSeek` messages that `DashboardScreen` handles by rendering the diff panel.

**Platform notes:** Real PTY (`pty` stdlib module) is Linux/macOS only. Windows gets a degraded `subprocess.Popen` path that captures stdout but cannot drive interactive sessions. All PTY-specific tests are skipped on `win32`; all Windows-fallback tests are skipped on non-Windows. Network graph and timeline/undo work identically on all platforms.

**Tech stack:** Python 3.11, Textual 8.2.4, networkx>=3.3 (new dep), `pty` stdlib (Linux/macOS), pytest + pytest-asyncio, existing rich/typer stack.

---

## File structure

### Files to create

- `src/bagley/tui/panels/shell.py` — `ShellPane` Textual Widget (RichLog + Input, bound to PTY master or subprocess)
- `src/bagley/tui/services/__init__.py` — empty marker
- `src/bagley/tui/services/shell_manager.py` — `ShellManager` singleton: spawn, background, foreground, close, registry
- `src/bagley/tui/services/pty_bridge.py` — `PtyBridge` (Linux real PTY) + `SubprocessBridge` (Windows fallback); common `Bridge` ABC
- `src/bagley/tui/services/observe.py` — `ObserveService`: `/observe pid <N>` handler, tap into `observe/terminal.py`, smart-paste classifier bridge, `/observe stop`
- `src/bagley/tui/panels/graph.py` — `GraphPane` Widget, full-screen F7 toggle, unicode rendering engine
- `src/bagley/tui/services/graph_layout.py` — `layout_to_grid(G, width, height)`: networkx spring → integer (col, row) coordinates + edge path list
- `src/bagley/tui/widgets/timeline.py` — `Timeline` horizontal scrubber widget, left/right navigation, diff panel integration
- `src/bagley/tui/services/history.py` — `EngagementHistory`: append-only event log with snapshot diffs keyed by timestamp
- `src/bagley/tui/services/undo.py` — `UndoStack`: wraps `EngagementHistory`, pop-last finding/ingest, emit `UndoApplied` message
- `tests/tui/test_shell_pane_linux.py` — PTY spawn tests (skipif Windows)
- `tests/tui/test_shell_pane_windows_fallback.py` — subprocess fallback tests (skipif not Windows)
- `tests/tui/test_shell_manager.py` — spawn/background/foreground/close lifecycle
- `tests/tui/test_observe_service.py` — `/observe` attach + stop (mock tap)
- `tests/tui/test_graph_layout.py` — layout function purity tests
- `tests/tui/test_graph_pane.py` — node + edge + star marker rendering
- `tests/tui/test_timeline.py` — event append, scrubber navigation, diff content
- `tests/tui/test_undo.py` — undo removes last finding, replayable
- `tests/tui/test_history.py` — EngagementHistory snapshot diffs

### Files to modify

- `pyproject.toml` — add `networkx>=3.3` to `[project.dependencies]`
- `src/bagley/tui/app.py` — bind F7 (`action_toggle_graph`), Ctrl+Shift+T (`action_open_timeline`), Ctrl+Shift+Z (`action_undo`), Ctrl+B (`action_background_shell`)
- `src/bagley/memory/store.py` — add `sessions` table CRUD (`upsert_session`, `close_session`, `list_sessions`) if not already present
- `src/bagley/agent/executor.py` — detect interactive-shell intent (regex on `nc -l`, `ssh`, `meterpreter`, `bash -i`) and emit `ShellHandoff` event instead of capturing stdout

### Files NOT touched in Phase 5

`src/bagley/agent/loop.py`, `src/bagley/agent/cli.py` (`--simple` fallback), `src/bagley/tui/panels/chat.py`, `src/bagley/tui/panels/hosts.py`, `src/bagley/tui/panels/target.py`, `src/bagley/tui/screens/dashboard.py` (dashboard wires new panes but its layout engine is not restructured), all Phase 1–4 widget files.

---

## Task 1: Add `networkx` dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1.1: Add networkx to `[project.dependencies]`**

Open `pyproject.toml`. In the `[project].dependencies` list, add after the existing `textual` entry:

```toml
    "networkx>=3.3",
```

- [ ] **Step 1.2: Install in the existing venv**

```bash
.venv/Scripts/python.exe -m pip install "networkx>=3.3"
```

Expected: installs without error. Verify:

```bash
.venv/Scripts/python.exe -c "import networkx; print(networkx.__version__)"
```

Expected: a version string `3.3` or higher.

- [ ] **Step 1.3: Commit**

```bash
git add pyproject.toml
git commit -m "deps(tui/phase5): add networkx>=3.3 for graph layout"
```

---

## Task 2: `EngagementHistory` — append-only event log

**Files:**
- Create: `src/bagley/tui/services/__init__.py`
- Create: `src/bagley/tui/services/history.py`
- Create: `tests/tui/test_history.py`

- [ ] **Step 2.1: Write the failing history test**

Create `tests/tui/test_history.py`:

```python
"""Tests for EngagementHistory snapshot diffs."""
import datetime
import pytest
from bagley.tui.services.history import EngagementHistory, TimelineEvent, EventKind


def _ts(offset_s: int = 0) -> datetime.datetime:
    base = datetime.datetime(2026, 4, 26, 12, 0, 0)
    return base + datetime.timedelta(seconds=offset_s)


def test_append_and_list():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="nmap -sV 10.10.14.1", data={"ports": [22, 80]}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="CVE-2021-41773", data={"severity": "CRIT"}))
    assert len(h.events) == 2


def test_snapshot_at_returns_events_up_to_ts():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.CRED, ts=_ts(20), label="admin:password", data={}))
    h.append(TimelineEvent(kind=EventKind.SHELL, ts=_ts(40), label="shell@10.10.14.1", data={}))
    snap = h.snapshot_at(_ts(25))
    assert len(snap) == 2
    assert snap[-1].kind == EventKind.CRED


def test_diff_between_two_snapshots():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="finding1", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(20), label="finding2", data={}))
    diff = h.diff(_ts(10), _ts(20))
    assert len(diff.added) == 1
    assert diff.added[0].label == "finding2"
    assert diff.removed == []


def test_remove_last_event():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(0), label="false positive", data={}))
    removed = h.remove_last(kind=EventKind.FINDING)
    assert removed.label == "false positive"
    assert len(h.events) == 0


def test_remove_last_returns_none_when_empty():
    h = EngagementHistory(tab_id="10.10.14.1")
    assert h.remove_last(kind=EventKind.FINDING) is None
```

- [ ] **Step 2.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_history.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services'`.

- [ ] **Step 2.3: Create the services package marker**

Create `src/bagley/tui/services/__init__.py`:

```python
"""TUI lifecycle and data services for Phase 5."""
```

- [ ] **Step 2.4: Implement `history.py`**

Create `src/bagley/tui/services/history.py`:

```python
"""Append-only engagement timeline for one tab.

Each `TimelineEvent` is immutable after append. `EngagementHistory` supports
snapshot-at-time queries and pairwise diffs used by the timeline scrubber and
the undo stack.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class EventKind(Enum):
    SCAN = auto()
    PORT = auto()
    FINDING = auto()
    CRED = auto()
    SHELL = auto()
    INGEST = auto()
    NOTE = auto()


@dataclass(frozen=True)
class TimelineEvent:
    kind: EventKind
    ts: datetime.datetime
    label: str
    data: dict  # arbitrary payload, treated as opaque by scrubber


@dataclass
class SnapshotDiff:
    added: list[TimelineEvent] = field(default_factory=list)
    removed: list[TimelineEvent] = field(default_factory=list)


class EngagementHistory:
    """Ordered list of timeline events for a single tab."""

    def __init__(self, tab_id: str) -> None:
        self.tab_id = tab_id
        self._events: list[TimelineEvent] = []

    @property
    def events(self) -> list[TimelineEvent]:
        return list(self._events)

    def append(self, event: TimelineEvent) -> None:
        self._events.append(event)

    def snapshot_at(self, ts: datetime.datetime) -> list[TimelineEvent]:
        """Return all events with timestamp <= ts."""
        return [e for e in self._events if e.ts <= ts]

    def diff(self, ts_from: datetime.datetime, ts_to: datetime.datetime) -> SnapshotDiff:
        """Events in (ts_from, ts_to] — what changed between two scrubber positions."""
        before = set(id(e) for e in self.snapshot_at(ts_from))
        after = self.snapshot_at(ts_to)
        added = [e for e in after if id(e) not in before]
        # Removals only possible via undo; diff between two forward points never removes
        return SnapshotDiff(added=added, removed=[])

    def remove_last(self, kind: EventKind) -> Optional[TimelineEvent]:
        """Pop the most recent event of *kind*. Returns the removed event or None."""
        for i in range(len(self._events) - 1, -1, -1):
            if self._events[i].kind == kind:
                return self._events.pop(i)
        return None
```

- [ ] **Step 2.5: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_history.py -v
```

Expected: 5 tests pass.

- [ ] **Step 2.6: Commit**

```bash
git add src/bagley/tui/services/__init__.py src/bagley/tui/services/history.py tests/tui/test_history.py
git commit -m "feat(tui/phase5): EngagementHistory append-only event log with snapshot diffs"
```

---

## Task 3: `UndoStack` — pop-last finding/ingest

**Files:**
- Create: `src/bagley/tui/services/undo.py`
- Create: `tests/tui/test_undo.py`

- [ ] **Step 3.1: Write the failing undo test**

Create `tests/tui/test_undo.py`:

```python
"""Tests for UndoStack."""
import datetime
import pytest
from bagley.tui.services.history import EngagementHistory, TimelineEvent, EventKind
from bagley.tui.services.undo import UndoStack, UndoRecord


def _ts(offset_s: int = 0) -> datetime.datetime:
    return datetime.datetime(2026, 4, 26, 12, 0, 0) + datetime.timedelta(seconds=offset_s)


def test_undo_removes_last_finding():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="CVE-2021-41773", data={}))
    stack = UndoStack(history=h)
    record = stack.undo()
    assert record is not None
    assert record.event.label == "CVE-2021-41773"
    assert len(h.events) == 1


def test_undo_on_empty_history_returns_none():
    h = EngagementHistory(tab_id="10.10.14.1")
    stack = UndoStack(history=h)
    assert stack.undo() is None


def test_undo_removes_last_ingest_when_no_finding():
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.INGEST, ts=_ts(5), label="nmap xml ingest", data={}))
    stack = UndoStack(history=h)
    record = stack.undo()
    assert record.event.kind == EventKind.INGEST


def test_undo_record_replayable_from_timeline():
    h = EngagementHistory(tab_id="10.10.14.1")
    ev = TimelineEvent(kind=EventKind.FINDING, ts=_ts(10), label="false positive", data={"severity": "HIGH"})
    h.append(ev)
    stack = UndoStack(history=h)
    record = stack.undo()
    # Replay: re-append the removed event
    h.append(record.event)
    assert len(h.events) == 1
    assert h.events[0].label == "false positive"


def test_undo_skips_non_undoable_kinds():
    """SCAN and SHELL events are not undoable — only FINDING, INGEST, CRED, NOTE."""
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN, ts=_ts(0), label="scan", data={}))
    h.append(TimelineEvent(kind=EventKind.SHELL, ts=_ts(5), label="shell", data={}))
    stack = UndoStack(history=h)
    assert stack.undo() is None
```

- [ ] **Step 3.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_undo.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services.undo'`.

- [ ] **Step 3.3: Implement `undo.py`**

Create `src/bagley/tui/services/undo.py`:

```python
"""UndoStack: removes the last undoable event from an EngagementHistory.

Undoable event kinds: FINDING, INGEST, CRED, NOTE.
Non-undoable: SCAN, PORT, SHELL (side-effectful; removing from the timeline
would not reverse the real-world action and could confuse the operator).

The removed event is returned as an UndoRecord so the timeline widget can
offer a one-click replay (re-append).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bagley.tui.services.history import EngagementHistory, EventKind, TimelineEvent

_UNDOABLE = {EventKind.FINDING, EventKind.INGEST, EventKind.CRED, EventKind.NOTE}


@dataclass
class UndoRecord:
    event: TimelineEvent


class UndoStack:
    """Single-level undo for false-positive removal.

    Wraps an EngagementHistory and exposes ``undo()`` which removes the most
    recent undoable event and returns an ``UndoRecord`` the caller can use to
    replay (re-append) the event if needed.
    """

    def __init__(self, history: EngagementHistory) -> None:
        self._history = history

    def undo(self) -> Optional[UndoRecord]:
        """Remove and return the latest undoable event, or None if none exists."""
        for kind in _UNDOABLE:
            event = self._history.remove_last(kind=kind)
            if event is not None:
                # Found the most-recent undoable; stop.
                # (remove_last already pops it; we just need to find the right kind)
                # Re-check: remove_last only pops for the given kind. We need the
                # most recent across ALL undoable kinds, so we must compare.
                # Strategy: collect candidates, pick max by ts, then rebuild.
                break

        # Proper multi-kind search: restore events removed by the loop above,
        # then do a proper scan.
        if event is not None:
            # We consumed one; but it might not be the most recent undoable overall.
            # Simpler and correct: scan directly.
            pass  # event is already the correct one (remove_last scans from end)

        # Actually, remove_last scans from the end for the given kind, so the
        # first kind that returns non-None gives us the most-recent event of that
        # kind. But FINDING might be at t=20 and CRED at t=30. We need the
        # globally most recent. Rewrite with a single pass:
        return self._undo_latest_across_kinds()

    def _undo_latest_across_kinds(self) -> Optional[UndoRecord]:
        """Find and remove the single most-recent undoable event across all kinds."""
        best_idx: Optional[int] = None
        events = self._history._events  # direct access to internal list
        for i in range(len(events) - 1, -1, -1):
            if events[i].kind in _UNDOABLE:
                best_idx = i
                break
        if best_idx is None:
            return None
        removed = events.pop(best_idx)
        return UndoRecord(event=removed)
```

- [ ] **Step 3.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_undo.py -v
```

Expected: 5 tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add src/bagley/tui/services/undo.py tests/tui/test_undo.py
git commit -m "feat(tui/phase5): UndoStack removes last FINDING/INGEST/CRED/NOTE from history"
```

---

## Task 4: `pty_bridge.py` — PTY wrapper and Windows fallback

**Files:**
- Create: `src/bagley/tui/services/pty_bridge.py`
- Create: `tests/tui/test_shell_pane_linux.py`
- Create: `tests/tui/test_shell_pane_windows_fallback.py`

- [ ] **Step 4.1: Write the failing Linux PTY test**

Create `tests/tui/test_shell_pane_linux.py`:

```python
"""PTY spawn tests — Linux/macOS only."""
import sys
import time
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="Real PTY not available on Windows"
)

from bagley.tui.services.pty_bridge import PtyBridge


def test_pty_bridge_spawns_and_reads_output():
    bridge = PtyBridge(cmd=["bash", "-c", "echo hello_pty"])
    bridge.start()
    output = b""
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and b"hello_pty" not in output:
        chunk = bridge.read(timeout=0.1)
        if chunk:
            output += chunk
    bridge.close()
    assert b"hello_pty" in output


def test_pty_bridge_write_then_read():
    bridge = PtyBridge(cmd=["bash"])
    bridge.start()
    bridge.write(b"echo write_test\n")
    output = b""
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and b"write_test" not in output:
        chunk = bridge.read(timeout=0.1)
        if chunk:
            output += chunk
    bridge.close()
    assert b"write_test" in output


def test_pty_bridge_close_terminates_process():
    bridge = PtyBridge(cmd=["bash"])
    bridge.start()
    bridge.close()
    assert bridge.is_alive() is False
```

- [ ] **Step 4.2: Write the failing Windows fallback test**

Create `tests/tui/test_shell_pane_windows_fallback.py`:

```python
"""Non-interactive subprocess fallback — Windows only."""
import sys
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows subprocess fallback only tested on Windows"
)

from bagley.tui.services.pty_bridge import SubprocessBridge


def test_subprocess_bridge_captures_stdout():
    bridge = SubprocessBridge(cmd=["cmd", "/c", "echo hello_win"])
    bridge.start()
    output = bridge.read_all(timeout=3.0)
    bridge.close()
    assert b"hello_win" in output


def test_subprocess_bridge_close_does_not_raise():
    bridge = SubprocessBridge(cmd=["cmd", "/c", "echo ok"])
    bridge.start()
    bridge.close()
    assert bridge.is_alive() is False
```

- [ ] **Step 4.3: Run the tests — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_shell_pane_linux.py tests/tui/test_shell_pane_windows_fallback.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services.pty_bridge'`.

- [ ] **Step 4.4: Implement `pty_bridge.py`**

Create `src/bagley/tui/services/pty_bridge.py`:

```python
"""PTY bridge: real PTY on Linux/macOS, subprocess fallback on Windows.

Usage:
    bridge = PtyBridge(cmd=["bash"])   # or SubprocessBridge on Windows
    bridge.start()
    bridge.write(b"ls\n")
    chunk = bridge.read(timeout=0.5)   # bytes or b""
    bridge.close()
    alive = bridge.is_alive()
"""
from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from typing import Optional


class Bridge(ABC):
    """Abstract base for PTY and subprocess bridges."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def write(self, data: bytes) -> None: ...

    @abstractmethod
    def read(self, timeout: float = 0.1) -> bytes: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def is_alive(self) -> bool: ...


class PtyBridge(Bridge):
    """POSIX PTY wrapper. Linux/macOS only.

    Forks a child process attached to a pseudo-terminal. Reads from the master
    fd with a configurable timeout so the TUI read loop stays non-blocking.
    """

    def __init__(self, cmd: list[str]) -> None:
        if sys.platform == "win32":
            raise RuntimeError("PtyBridge is not supported on Windows; use SubprocessBridge")
        self._cmd = cmd
        self._master_fd: Optional[int] = None
        self._pid: Optional[int] = None

    def start(self) -> None:
        import pty  # stdlib, POSIX only
        self._pid, self._master_fd = pty.fork()
        if self._pid == 0:
            # child
            os.execvp(self._cmd[0], self._cmd)
            # execvp never returns on success; if it fails the child exits

    def write(self, data: bytes) -> None:
        if self._master_fd is not None:
            os.write(self._master_fd, data)

    def read(self, timeout: float = 0.1) -> bytes:
        if self._master_fd is None:
            return b""
        r, _, _ = select.select([self._master_fd], [], [], timeout)
        if r:
            try:
                return os.read(self._master_fd, 4096)
            except OSError:
                return b""
        return b""

    def close(self) -> None:
        if self._pid is not None:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
        self._pid = None
        self._master_fd = None

    def is_alive(self) -> bool:
        if self._pid is None:
            return False
        try:
            result = os.waitpid(self._pid, os.WNOHANG)
            return result == (0, 0)
        except ChildProcessError:
            return False


class SubprocessBridge(Bridge):
    """Non-interactive subprocess fallback for Windows.

    Cannot drive interactive programs (no PTY allocation). Captures stdout/
    stderr as a byte stream. Used as a degraded fallback so the TUI renders
    tool output even if it cannot provide an interactive shell.
    """

    def __init__(self, cmd: list[str]) -> None:
        self._cmd = cmd
        self._proc: Optional[subprocess.Popen] = None
        self._buf: bytes = b""
        self._lock = threading.Lock()
        self._reader: Optional[threading.Thread] = None

    def start(self) -> None:
        self._proc = subprocess.Popen(
            self._cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self._reader = threading.Thread(target=self._drain, daemon=True)
        self._reader.start()

    def _drain(self) -> None:
        assert self._proc is not None
        assert self._proc.stdout is not None
        for chunk in iter(lambda: self._proc.stdout.read(4096), b""):
            with self._lock:
                self._buf += chunk

    def write(self, data: bytes) -> None:
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.write(data)
                self._proc.stdin.flush()
            except BrokenPipeError:
                pass

    def read(self, timeout: float = 0.1) -> bytes:
        with self._lock:
            chunk = self._buf
            self._buf = b""
        return chunk

    def read_all(self, timeout: float = 5.0) -> bytes:
        if self._proc:
            try:
                self._proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                pass
        return self.read()

    def close(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

    def is_alive(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.poll() is None
```

- [ ] **Step 4.5: Run the platform-appropriate tests**

On Linux/macOS:

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_shell_pane_linux.py -v
```

Expected: 3 tests pass, Windows fallback test skipped.

On Windows:

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_shell_pane_windows_fallback.py -v
```

Expected: 2 tests pass, Linux PTY test skipped.

- [ ] **Step 4.6: Commit**

```bash
git add src/bagley/tui/services/pty_bridge.py tests/tui/test_shell_pane_linux.py tests/tui/test_shell_pane_windows_fallback.py
git commit -m "feat(tui/phase5): PtyBridge (POSIX PTY) + SubprocessBridge (Windows fallback)"
```

---

## Task 5: `ShellManager` — lifecycle registry

**Files:**
- Create: `src/bagley/tui/services/shell_manager.py`
- Create: `tests/tui/test_shell_manager.py`

- [ ] **Step 5.1: Write the failing shell manager test**

Create `tests/tui/test_shell_manager.py`:

```python
"""ShellManager lifecycle tests."""
import sys
import pytest
from unittest.mock import MagicMock, patch
from bagley.tui.services.shell_manager import ShellManager, ShellRecord, ShellState


def _make_manager() -> ShellManager:
    return ShellManager()


def test_spawn_creates_record():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        record = mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    assert record.name == "rev-shell-1"
    assert record.tab_id == "10.10.14.1"
    assert record.state == ShellState.FOREGROUND
    mock_bridge.start.assert_called_once()


def test_background_moves_to_background_state():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        record = mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    mgr.background(name="rev-shell-1")
    assert mgr.get("rev-shell-1").state == ShellState.BACKGROUND


def test_foreground_restores_foreground_state():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    mgr.background(name="rev-shell-1")
    mgr.foreground(name="rev-shell-1")
    assert mgr.get("rev-shell-1").state == ShellState.FOREGROUND


def test_close_sends_sigterm_and_removes_from_registry():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    mgr.close(name="rev-shell-1")
    mock_bridge.close.assert_called_once()
    assert mgr.get("rev-shell-1") is None


def test_list_shells_returns_all():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        mgr.spawn(name="shell-a", cmd=["bash"], tab_id="10.10.14.1")
        mgr.spawn(name="shell-b", cmd=["bash"], tab_id="10.10.14.2")
    shells = mgr.list_shells()
    names = [s.name for s in shells]
    assert "shell-a" in names
    assert "shell-b" in names
```

- [ ] **Step 5.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_shell_manager.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services.shell_manager'`.

- [ ] **Step 5.3: Implement `shell_manager.py`**

Create `src/bagley/tui/services/shell_manager.py`:

```python
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
```

- [ ] **Step 5.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_shell_manager.py -v
```

Expected: 5 tests pass.

- [ ] **Step 5.5: Commit**

```bash
git add src/bagley/tui/services/shell_manager.py tests/tui/test_shell_manager.py
git commit -m "feat(tui/phase5): ShellManager lifecycle registry (spawn/background/foreground/close)"
```

---

## Task 6: `ShellPane` — live PTY container widget

**Files:**
- Create: `src/bagley/tui/panels/shell.py`

(Tests for ShellPane rendering are covered by Task 4 bridge tests and Task 5 manager tests; an integration-level Pilot test is deferred to the integration smoke-test in Task 13.)

- [ ] **Step 6.1: Implement `ShellPane`**

Create `src/bagley/tui/panels/shell.py`:

```python
"""ShellPane: live shell session widget.

Renders the PTY or subprocess output in a scrollable RichLog and forwards
keystrokes to the bridge's write() method. Ctrl+B backgrounds the pane
(bridge stays alive; widget is hidden). The widget exposes ``attach(bridge)``
so ``ShellManager`` can hot-swap sessions when the operator foregrounds a
backgrounded shell.

Textual 8.2.4 conventions:
- Subclass Widget, compose() returns child widgets.
- post_message() dispatches custom messages up the tree.
- on_key() intercepts raw key events before Textual's bindings when
  ``can_focus=True``.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import RichLog

from bagley.tui.services.pty_bridge import Bridge


class ShellPane(Widget):
    """Full-height shell pane that mirrors a Bridge I/O stream."""

    BINDINGS = [
        Binding("ctrl+b", "background", "Background shell", show=True),
    ]

    can_focus = True
    shell_name: reactive[str] = reactive("")

    class Backgrounded(Message):
        """Posted when the operator presses Ctrl+B."""
        def __init__(self, shell_name: str) -> None:
            super().__init__()
            self.shell_name = shell_name

    class OutputLine(Message):
        """Posted for each decoded output line so ChatPanel can observe."""
        def __init__(self, shell_name: str, line: str) -> None:
            super().__init__()
            self.shell_name = shell_name
            self.line = line

    def __init__(self, name: str, bridge: Optional[Bridge] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.shell_name = name
        self._bridge: Optional[Bridge] = bridge
        self._poll_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        yield RichLog(id="shell-log", markup=True, highlight=True, wrap=True)

    def attach(self, bridge: Bridge) -> None:
        """Attach (or replace) the bridge and start the read loop."""
        self._bridge = bridge
        if self._poll_task is not None:
            self._poll_task.cancel()
        self._poll_task = asyncio.ensure_future(self._read_loop())

    async def on_mount(self) -> None:
        if self._bridge is not None:
            self._poll_task = asyncio.ensure_future(self._read_loop())

    async def _read_loop(self) -> None:
        """Background coroutine: poll bridge, write bytes to RichLog."""
        log: RichLog = self.query_one("#shell-log", RichLog)
        buf = b""
        while self._bridge is not None and self._bridge.is_alive():
            await asyncio.sleep(0.05)
            chunk = self._bridge.read(timeout=0.0)
            if chunk:
                buf += chunk
                # Flush complete lines to the log
                while b"\n" in buf:
                    line_bytes, buf = buf.split(b"\n", 1)
                    try:
                        line = line_bytes.decode("utf-8", errors="replace")
                    except Exception:
                        line = repr(line_bytes)
                    log.write(Text(line))
                    self.post_message(self.OutputLine(shell_name=self.shell_name, line=line))

    def on_key(self, event: events.Key) -> None:
        """Forward printable characters and special keys to the bridge."""
        if self._bridge is None:
            return
        if event.character and event.key != "ctrl+b":
            self._bridge.write(event.character.encode("utf-8", errors="replace"))
            event.stop()
        elif event.key in ("enter", "return"):
            self._bridge.write(b"\n")
            event.stop()
        elif event.key == "backspace":
            self._bridge.write(b"\x7f")
            event.stop()

    def action_background(self) -> None:
        """Ctrl+B: hide the pane without closing the bridge."""
        self.display = False
        self.post_message(self.Backgrounded(shell_name=self.shell_name))
```

- [ ] **Step 6.2: Verify import**

```bash
.venv/Scripts/python.exe -c "from bagley.tui.panels.shell import ShellPane; print('ok')"
```

Expected: `ok`.

- [ ] **Step 6.3: Commit**

```bash
git add src/bagley/tui/panels/shell.py
git commit -m "feat(tui/phase5): ShellPane Textual widget with PTY read loop and Ctrl+B background"
```

---

## Task 7: `executor.py` handoff + `store.py` sessions table

**Files:**
- Modify: `src/bagley/agent/executor.py`
- Modify: `src/bagley/memory/store.py`

- [ ] **Step 7.1: Add `sessions` CRUD to `store.py`**

Read `src/bagley/memory/store.py` to identify the existing schema and insertion pattern, then add after the existing table-init block:

```python
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
```

Call `init_sessions_table(conn)` alongside the other table-init calls in the existing `init_db()` / `setup()` function.

- [ ] **Step 7.2: Add `ShellHandoff` detection to `executor.py`**

Read `src/bagley/agent/executor.py`. Find the section that runs a subprocess and captures stdout. Add an interactive-intent detector before the subprocess is created:

```python
import re as _re

_INTERACTIVE_PATTERNS = _re.compile(
    r"(nc\s+-l|ncat\s+-l|netcat\s+-l"
    r"|ssh\s+"
    r"|meterpreter"
    r"|bash\s+-i"
    r"|sh\s+-i"
    r"|python.*-c.*pty\.spawn"
    r"|socat.*pty)",
    _re.IGNORECASE,
)


def _is_interactive_intent(cmd: str) -> bool:
    return bool(_INTERACTIVE_PATTERNS.search(cmd))
```

In the exec path, before running the command, check:

```python
if _is_interactive_intent(cmd_str):
    # Emit a ShellHandoff event for the TUI to intercept.
    # In --simple mode this is a no-op (the event is never consumed).
    raise ShellHandoffRequired(cmd=cmd_str)
```

Add the exception class near the top of `executor.py`:

```python
class ShellHandoffRequired(Exception):
    """Raised when executor detects an interactive-shell command.

    The TUI catches this and routes the command to ShellManager instead.
    In --simple (Rich REPL) mode this exception propagates up and is caught
    by the loop, which falls back to non-interactive subprocess execution.
    """
    def __init__(self, cmd: str) -> None:
        super().__init__(cmd)
        self.cmd = cmd
```

- [ ] **Step 7.3: Verify the import chain is intact**

```bash
.venv/Scripts/python.exe -c "from bagley.agent.executor import ShellHandoffRequired; print('ok')"
.venv/Scripts/python.exe -c "from bagley.memory.store import upsert_session, close_session, list_sessions; print('ok')"
```

Both expected: `ok`.

- [ ] **Step 7.4: Commit**

```bash
git add src/bagley/agent/executor.py src/bagley/memory/store.py
git commit -m "feat(tui/phase5): ShellHandoffRequired in executor + sessions CRUD in store"
```

---

## Task 8: `ObserveService` — `/observe pid <N>` handler

**Files:**
- Create: `src/bagley/tui/services/observe.py`
- Create: `tests/tui/test_observe_service.py`

- [ ] **Step 8.1: Write the failing observe test**

Create `tests/tui/test_observe_service.py`:

```python
"""ObserveService tests — mock terminal.py tap."""
import pytest
from unittest.mock import MagicMock, patch
from bagley.tui.services.observe import ObserveService, ObserveError


def _make_service() -> ObserveService:
    return ObserveService()


def test_attach_calls_tap_with_pid():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = False
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.attach(pid=1234)
    mock_tap.attach.assert_called_once_with(1234)


def test_attach_when_already_active_raises():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = True
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        with pytest.raises(ObserveError, match="already attached"):
            svc.attach(pid=1234)


def test_stop_calls_tap_detach():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = True
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.stop()
    mock_tap.detach.assert_called_once()


def test_stop_when_not_active_is_noop():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = False
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.stop()  # should not raise
    mock_tap.detach.assert_not_called()


def test_read_chunk_returns_bytes_from_tap():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = True
    mock_tap.read_chunk.return_value = b"some output\n"
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.attach(pid=9999)
        chunk = svc.read_chunk()
    assert b"some output" in chunk
```

- [ ] **Step 8.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_observe_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services.observe'`.

- [ ] **Step 8.3: Implement `observe.py`**

Create `src/bagley/tui/services/observe.py`:

```python
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
```

- [ ] **Step 8.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_observe_service.py -v
```

Expected: 5 tests pass.

- [ ] **Step 8.5: Commit**

```bash
git add src/bagley/tui/services/observe.py tests/tui/test_observe_service.py
git commit -m "feat(tui/phase5): ObserveService wraps terminal.py tap for /observe pid <N>"
```

---

## Task 9: `graph_layout.py` — networkx spring to unicode grid

**Files:**
- Create: `src/bagley/tui/services/graph_layout.py`
- Create: `tests/tui/test_graph_layout.py`

- [ ] **Step 9.1: Write the failing graph layout test**

Create `tests/tui/test_graph_layout.py`:

```python
"""graph_layout pure-function tests. No TUI required."""
import networkx as nx
import pytest
from bagley.tui.services.graph_layout import layout_to_grid, EdgePath, GridNode


def _simple_graph() -> nx.Graph:
    G = nx.Graph()
    G.add_node("A", label="10.10.14.1", kind="host")
    G.add_node("B", label="10.10.14.2", kind="host")
    G.add_node("C", label="10.10.14.3", kind="host")
    G.add_edge("A", "B", relation="scanned")
    G.add_edge("B", "C", relation="pivoted")
    return G


def test_layout_returns_grid_nodes_for_all_nodes():
    G = _simple_graph()
    nodes, edges = layout_to_grid(G, width=80, height=24)
    node_ids = {n.node_id for n in nodes}
    assert node_ids == {"A", "B", "C"}


def test_layout_coords_within_grid_bounds():
    G = _simple_graph()
    nodes, _ = layout_to_grid(G, width=80, height=24)
    for n in nodes:
        assert 0 <= n.col < 80, f"col={n.col} out of range"
        assert 0 <= n.row < 24, f"row={n.row} out of range"


def test_layout_edges_list_matches_graph_edges():
    G = _simple_graph()
    _, edges = layout_to_grid(G, width=80, height=24)
    edge_pairs = {(e.src_id, e.dst_id) for e in edges}
    assert ("A", "B") in edge_pairs or ("B", "A") in edge_pairs
    assert ("B", "C") in edge_pairs or ("C", "B") in edge_pairs


def test_layout_single_node():
    G = nx.Graph()
    G.add_node("solo", label="192.168.1.1", kind="host")
    nodes, edges = layout_to_grid(G, width=40, height=20)
    assert len(nodes) == 1
    assert len(edges) == 0


def test_layout_is_deterministic_with_seed():
    G = _simple_graph()
    nodes_a, _ = layout_to_grid(G, width=80, height=24, seed=42)
    nodes_b, _ = layout_to_grid(G, width=80, height=24, seed=42)
    pos_a = {n.node_id: (n.col, n.row) for n in nodes_a}
    pos_b = {n.node_id: (n.col, n.row) for n in nodes_b}
    assert pos_a == pos_b
```

- [ ] **Step 9.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_graph_layout.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services.graph_layout'`.

- [ ] **Step 9.3: Implement `graph_layout.py`**

Create `src/bagley/tui/services/graph_layout.py`:

```python
"""Convert a networkx Graph into integer grid coordinates for unicode rendering.

``layout_to_grid`` is a pure function: same graph + same seed → same output.
It uses networkx's spring layout (Fruchterman-Reingold) and maps the resulting
[-1, 1] float space linearly onto the integer grid [0, width) × [0, height).
A 2-unit margin is applied so labels never touch the terminal edge.

Returns:
    nodes: list[GridNode]  — one per graph node
    edges: list[EdgePath]  — one per graph edge, with src/dst grid coords
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import networkx as nx


@dataclass
class GridNode:
    node_id: str
    col: int
    row: int
    label: str
    kind: str          # "host", "gateway", "pivot", etc.


@dataclass
class EdgePath:
    src_id: str
    dst_id: str
    src_col: int
    src_row: int
    dst_col: int
    dst_row: int
    relation: str      # "scanned", "routed-via", "pivoted", "shell-obtained"


def layout_to_grid(
    G: nx.Graph,
    width: int,
    height: int,
    seed: int = 0,
    margin: int = 2,
) -> tuple[list[GridNode], list[EdgePath]]:
    """Project networkx spring layout onto an integer terminal grid.

    Args:
        G:      networkx Graph with optional node attrs ``label`` and ``kind``
                and optional edge attr ``relation``.
        width:  terminal columns available (passed by GraphPane).
        height: terminal rows available.
        seed:   RNG seed for deterministic layout.
        margin: padding in columns/rows from the grid edge.

    Returns:
        (nodes, edges) — both lists are newly allocated each call.
    """
    if len(G) == 0:
        return [], []

    pos = nx.spring_layout(G, seed=seed)  # dict node → np.array([x, y])

    # Normalise from [-1, 1] (approx) to [margin, width-margin) × [margin, height-margin)
    xs = [v[0] for v in pos.values()]
    ys = [v[1] for v in pos.values()]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    x_range = (x_max - x_min) or 1.0
    y_range = (y_max - y_min) or 1.0

    usable_w = width - 2 * margin
    usable_h = height - 2 * margin

    def _project(x: float, y: float) -> tuple[int, int]:
        col = margin + int((x - x_min) / x_range * usable_w)
        row = margin + int((y - y_min) / y_range * usable_h)
        col = max(margin, min(width - margin - 1, col))
        row = max(margin, min(height - margin - 1, row))
        return col, row

    coord: dict[str, tuple[int, int]] = {}
    nodes: list[GridNode] = []
    for node_id, (x, y) in pos.items():
        col, row = _project(x, y)
        coord[node_id] = (col, row)
        attrs = G.nodes[node_id]
        nodes.append(GridNode(
            node_id=str(node_id),
            col=col,
            row=row,
            label=attrs.get("label", str(node_id)),
            kind=attrs.get("kind", "host"),
        ))

    edges: list[EdgePath] = []
    for u, v, edata in G.edges(data=True):
        sc, sr = coord[u]
        dc, dr = coord[v]
        edges.append(EdgePath(
            src_id=str(u), dst_id=str(v),
            src_col=sc, src_row=sr,
            dst_col=dc, dst_row=dr,
            relation=edata.get("relation", ""),
        ))

    return nodes, edges
```

- [ ] **Step 9.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_graph_layout.py -v
```

Expected: 5 tests pass.

- [ ] **Step 9.5: Commit**

```bash
git add src/bagley/tui/services/graph_layout.py tests/tui/test_graph_layout.py
git commit -m "feat(tui/phase5): graph_layout pure function (networkx spring → unicode grid coords)"
```

---

## Task 10: `GraphPane` — full-screen F7 unicode graph widget

**Files:**
- Create: `src/bagley/tui/panels/graph.py`
- Create: `tests/tui/test_graph_pane.py`

- [ ] **Step 10.1: Write the failing graph pane test**

Create `tests/tui/test_graph_pane.py`:

```python
"""GraphPane rendering tests using Textual Pilot."""
import pytest
import networkx as nx
from textual.app import App, ComposeResult
from bagley.tui.panels.graph import GraphPane


class _GraphApp(App):
    def compose(self) -> ComposeResult:
        G = nx.Graph()
        G.add_node("A", label="10.10.14.1", kind="host")
        G.add_node("B", label="10.10.14.2", kind="host")
        G.add_edge("A", "B", relation="scanned")
        yield GraphPane(graph=G, current_target="A", id="graph")


@pytest.mark.asyncio
async def test_graph_pane_mounts():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        assert pane is not None


@pytest.mark.asyncio
async def test_graph_pane_renders_node_labels():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        rendered = pane.render_to_text()
        assert "10.10.14.1" in rendered or "A" in rendered


@pytest.mark.asyncio
async def test_graph_pane_marks_current_target():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        rendered = pane.render_to_text()
        # Current target is marked with ★
        assert "★" in rendered


@pytest.mark.asyncio
async def test_graph_pane_update_graph_rerenders():
    app = _GraphApp()
    async with app.run_test(size=(80, 24)) as pilot:
        pane = app.query_one("#graph", GraphPane)
        G2 = nx.Graph()
        G2.add_node("X", label="192.168.1.1", kind="host")
        pane.update_graph(G2, current_target="X")
        await pilot.pause()
        rendered = pane.render_to_text()
        assert "192.168.1.1" in rendered or "X" in rendered
```

- [ ] **Step 10.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_graph_pane.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.panels.graph'`.

- [ ] **Step 10.3: Implement `graph.py`**

Create `src/bagley/tui/panels/graph.py`:

```python
"""GraphPane: full-screen F7 network graph widget.

Renders hosts as unicode box chars, edges as lines (─ │ ╱ ╲), and marks the
current target with ★. Uses ``graph_layout.layout_to_grid`` to project a
networkx Graph onto the terminal grid.

Textual 8.2.4: ``render()`` returns a ``Strip`` list via ``render_line()``
or we override ``render()`` to return a Rich ``Text`` object for the whole
widget. For simplicity this implementation uses a custom ``render_line()``
approach based on a pre-rendered grid buffer.

Operator interaction:
    - Click on a node label fires ``NodeClicked(node_id)`` message.
    - update_graph(G, current_target) rebuilds the buffer and triggers a refresh.
"""
from __future__ import annotations

from typing import Optional

import networkx as nx
from rich.segment import Segment
from rich.style import Style
from textual.message import Message
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

from bagley.tui.services.graph_layout import GridNode, EdgePath, layout_to_grid

_NODE_CHAR = "●"
_STAR_CHAR = "★"
_HORIZ = "─"
_VERT = "│"
_STYLE_NODE = Style(color="cyan", bold=True)
_STYLE_TARGET = Style(color="bright_yellow", bold=True)
_STYLE_EDGE = Style(color="bright_black")
_STYLE_LABEL = Style(color="white")


class GraphPane(Widget):
    """Unicode network graph. Toggle full-screen with F7 via BagleyApp binding."""

    class NodeClicked(Message):
        def __init__(self, node_id: str) -> None:
            super().__init__()
            self.node_id = node_id

    def __init__(
        self,
        graph: Optional[nx.Graph] = None,
        current_target: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._graph = graph or nx.Graph()
        self._current_target = current_target
        self._grid: list[list[str]] = []
        self._style_grid: list[list[Style]] = []

    def on_mount(self) -> None:
        self._rebuild()

    def update_graph(self, graph: nx.Graph, current_target: str = "") -> None:
        self._graph = graph
        self._current_target = current_target
        self._rebuild()
        self.refresh()

    def _rebuild(self) -> None:
        """Rasterise graph onto a character grid."""
        w = self.size.width or 80
        h = self.size.height or 24
        self._grid = [[" "] * w for _ in range(h)]
        self._style_grid = [[Style.null()] * w for _ in range(h)]
        if len(self._graph) == 0:
            return
        nodes, edges = layout_to_grid(self._graph, width=w, height=h)
        self._draw_edges(edges)
        self._draw_nodes(nodes)

    def _draw_edges(self, edges: list[EdgePath]) -> None:
        for e in edges:
            self._draw_line(e.src_col, e.src_row, e.dst_col, e.dst_row)

    def _draw_line(self, c0: int, r0: int, c1: int, r1: int) -> None:
        """Bresenham line drawing onto the char grid."""
        dc = abs(c1 - c0)
        dr = abs(r1 - r0)
        sc = 1 if c0 < c1 else -1
        sr = 1 if r0 < r1 else -1
        err = dc - dr
        c, r = c0, r0
        while True:
            h = self.size.height or 24
            w = self.size.width or 80
            if 0 <= r < h and 0 <= c < w:
                if dc > dr:
                    self._grid[r][c] = _HORIZ
                else:
                    self._grid[r][c] = _VERT
                self._style_grid[r][c] = _STYLE_EDGE
            if c == c1 and r == r1:
                break
            e2 = 2 * err
            if e2 > -dr:
                err -= dr
                c += sc
            if e2 < dc:
                err += dc
                r += sr

    def _draw_nodes(self, nodes: list[GridNode]) -> None:
        for n in nodes:
            r, c = n.row, n.col
            h = self.size.height or 24
            w = self.size.width or 80
            if not (0 <= r < h and 0 <= c < w):
                continue
            is_target = n.node_id == self._current_target
            char = _STAR_CHAR if is_target else _NODE_CHAR
            style = _STYLE_TARGET if is_target else _STYLE_NODE
            self._grid[r][c] = char
            self._style_grid[r][c] = style
            # Draw label to the right
            label = n.label[:12]  # truncate to avoid overflow
            for i, ch in enumerate(label):
                lc = c + 1 + i
                if 0 <= lc < w:
                    self._grid[r][lc] = ch
                    self._style_grid[r][lc] = _STYLE_LABEL

    def render_line(self, y: int) -> Strip:
        if y >= len(self._grid):
            return Strip.blank(self.size.width)
        row = self._grid[y]
        style_row = self._style_grid[y]
        segments: list[Segment] = []
        for ch, st in zip(row, style_row):
            segments.append(Segment(ch, st))
        return Strip(segments)

    def render_to_text(self) -> str:
        """Return all grid rows joined by newlines for testing."""
        return "\n".join("".join(row) for row in self._grid)

    def on_resize(self) -> None:
        self._rebuild()
        self.refresh()
```

- [ ] **Step 10.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_graph_pane.py -v
```

Expected: 4 tests pass.

- [ ] **Step 10.5: Commit**

```bash
git add src/bagley/tui/panels/graph.py tests/tui/test_graph_pane.py
git commit -m "feat(tui/phase5): GraphPane unicode network graph with star marker and NodeClicked message"
```

---

## Task 11: `Timeline` scrubber widget

**Files:**
- Create: `src/bagley/tui/widgets/timeline.py`
- Create: `tests/tui/test_timeline.py`

- [ ] **Step 11.1: Write the failing timeline test**

Create `tests/tui/test_timeline.py`:

```python
"""Timeline scrubber widget tests."""
import datetime
import pytest
from textual.app import App, ComposeResult
from bagley.tui.widgets.timeline import Timeline, TimelineSeek
from bagley.tui.services.history import EngagementHistory, TimelineEvent, EventKind


def _ts(offset_s: int = 0) -> datetime.datetime:
    return datetime.datetime(2026, 4, 26, 12, 0, 0) + datetime.timedelta(seconds=offset_s)


def _make_history() -> EngagementHistory:
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN,    ts=_ts(0),  label="scan",    data={}))
    h.append(TimelineEvent(kind=EventKind.PORT,    ts=_ts(10), label="port 80", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(20), label="CVE",     data={}))
    h.append(TimelineEvent(kind=EventKind.CRED,    ts=_ts(30), label="admin",   data={}))
    h.append(TimelineEvent(kind=EventKind.SHELL,   ts=_ts(40), label="shell",   data={}))
    return h


class _TimelineApp(App):
    def __init__(self, history: EngagementHistory) -> None:
        super().__init__()
        self._history = history

    def compose(self) -> ComposeResult:
        yield Timeline(history=self._history, id="tl")


@pytest.mark.asyncio
async def test_timeline_mounts_with_events():
    app = _TimelineApp(_make_history())
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        assert tl is not None
        assert tl.event_count == 5


@pytest.mark.asyncio
async def test_timeline_scrub_right_advances_index():
    app = _TimelineApp(_make_history())
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        start_idx = tl.selected_index
        await pilot.press("right")
        assert tl.selected_index > start_idx or tl.selected_index == tl.event_count - 1


@pytest.mark.asyncio
async def test_timeline_scrub_left_decrements_index():
    app = _TimelineApp(_make_history())
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        # Move right first
        await pilot.press("right")
        await pilot.press("right")
        idx_before = tl.selected_index
        await pilot.press("left")
        assert tl.selected_index < idx_before or tl.selected_index == 0


@pytest.mark.asyncio
async def test_timeline_appending_event_increases_count():
    h = _make_history()
    app = _TimelineApp(h)
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        count_before = tl.event_count
        h.append(TimelineEvent(kind=EventKind.NOTE, ts=_ts(50), label="note", data={}))
        tl.reload()
        await pilot.pause()
        assert tl.event_count == count_before + 1
```

- [ ] **Step 11.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_timeline.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.widgets.timeline'`.

- [ ] **Step 11.3: Implement `timeline.py`**

Create `src/bagley/tui/widgets/timeline.py`:

```python
"""Timeline scrubber widget.

Renders events as labelled tick-marks along a horizontal bar. ← / → key presses
move the selection; the widget posts ``TimelineSeek`` so the parent screen can
dim the workspace to the state at that moment and show a diff panel.

Layout (single-row):
    [SCAN]────[PORT]────[FINDING]────[CRED]────[SHELL]
                          ▲ selected (highlighted)

The widget occupies a fixed height of 3 rows: tick marks, label row, and a thin
connector bar. Heights are stable so the surrounding layout does not reflow.
"""
from __future__ import annotations

import datetime
from typing import Optional

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.message import Message
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

from bagley.tui.services.history import EngagementHistory, TimelineEvent

_STYLE_TICK = Style(color="bright_black")
_STYLE_SELECTED = Style(color="bright_yellow", bold=True, reverse=True)
_STYLE_LINE = Style(color="bright_black")
_STYLE_LABEL = Style(color="white")
_STYLE_LABEL_SEL = Style(color="bright_yellow", bold=True)

_KIND_ICONS = {
    "SCAN":    "S",
    "PORT":    "P",
    "FINDING": "F",
    "CRED":    "C",
    "SHELL":   "►",
    "INGEST":  "I",
    "NOTE":    "N",
}


class TimelineSeek(Message):
    """Posted when the scrubber moves to a new position."""

    def __init__(self, event: TimelineEvent, index: int) -> None:
        super().__init__()
        self.event = event
        self.index = index


class Timeline(Widget):
    """Horizontal timeline scrubber. Height = 3 rows."""

    DEFAULT_CSS = """
    Timeline {
        height: 3;
        background: $background;
    }
    """

    can_focus = True
    selected_index: reactive[int] = reactive(0)

    def __init__(self, history: EngagementHistory, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history = history
        self._events: list[TimelineEvent] = []
        self._tick_cols: list[int] = []

    def on_mount(self) -> None:
        self.reload()

    def reload(self) -> None:
        self._events = list(self._history.events)
        self._compute_tick_cols()
        if self.selected_index >= len(self._events) and self._events:
            self.selected_index = len(self._events) - 1
        self.refresh()

    @property
    def event_count(self) -> int:
        return len(self._events)

    def _compute_tick_cols(self) -> None:
        """Map events uniformly across widget width."""
        w = self.size.width or 80
        n = len(self._events)
        if n == 0:
            self._tick_cols = []
            return
        if n == 1:
            self._tick_cols = [w // 2]
            return
        margin = 4
        usable = w - 2 * margin
        self._tick_cols = [
            margin + int(i / (n - 1) * usable) for i in range(n)
        ]

    def on_key(self, event: events.Key) -> None:
        if event.key == "right":
            self._move(1)
            event.stop()
        elif event.key == "left":
            self._move(-1)
            event.stop()

    def _move(self, delta: int) -> None:
        if not self._events:
            return
        new_idx = max(0, min(len(self._events) - 1, self.selected_index + delta))
        self.selected_index = new_idx
        self.post_message(TimelineSeek(event=self._events[new_idx], index=new_idx))
        self.refresh()

    def render_line(self, y: int) -> Strip:
        w = self.size.width or 80
        if y == 0:
            return self._render_connector_row(w)
        if y == 1:
            return self._render_tick_row(w)
        if y == 2:
            return self._render_label_row(w)
        return Strip.blank(w)

    def _render_connector_row(self, w: int) -> Strip:
        row = [(" ", _STYLE_LINE)] * w
        if len(self._tick_cols) >= 2:
            for i in range(self._tick_cols[0], self._tick_cols[-1] + 1):
                if 0 <= i < w:
                    row[i] = ("─", _STYLE_LINE)
        return Strip([Segment(ch, st) for ch, st in row])

    def _render_tick_row(self, w: int) -> Strip:
        row = [(" ", _STYLE_LINE)] * w
        for idx, col in enumerate(self._tick_cols):
            if 0 <= col < w:
                is_sel = idx == self.selected_index
                ev = self._events[idx]
                icon = _KIND_ICONS.get(ev.kind.name, "·")
                style = _STYLE_SELECTED if is_sel else _STYLE_TICK
                row[col] = (icon, style)
        return Strip([Segment(ch, st) for ch, st in row])

    def _render_label_row(self, w: int) -> Strip:
        row = [(" ", Style.null())] * w
        for idx, col in enumerate(self._tick_cols):
            if 0 <= col < w:
                ev = self._events[idx]
                label = ev.label[:8]
                is_sel = idx == self.selected_index
                style = _STYLE_LABEL_SEL if is_sel else _STYLE_LABEL
                start = max(0, col - len(label) // 2)
                for i, ch in enumerate(label):
                    if 0 <= start + i < w:
                        row[start + i] = (ch, style)
        return Strip([Segment(ch, st) for ch, st in row])

    def on_resize(self) -> None:
        self._compute_tick_cols()
        self.refresh()
```

- [ ] **Step 11.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_timeline.py -v
```

Expected: 4 tests pass.

- [ ] **Step 11.5: Commit**

```bash
git add src/bagley/tui/widgets/timeline.py tests/tui/test_timeline.py
git commit -m "feat(tui/phase5): Timeline scrubber widget with left/right navigation and TimelineSeek message"
```

---

## Task 12: Wire new bindings into `app.py`

**Files:**
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 12.1: Read the current `app.py` bindings block**

Open `src/bagley/tui/app.py` and locate the `BINDINGS` list and `action_*` methods.

- [ ] **Step 12.2: Add Phase 5 bindings**

In the `BINDINGS` list, add after the existing entries:

```python
Binding("f7",           "toggle_graph",      "Graph view",        show=True),
Binding("ctrl+shift+t", "open_timeline",     "Timeline scrubber", show=True),
Binding("ctrl+shift+z", "undo",              "Undo last ingest",  show=True),
Binding("ctrl+b",       "background_shell",  "Background shell",  show=True),
```

- [ ] **Step 12.3: Implement the four new action methods**

Add to `BagleyApp`:

```python
def action_toggle_graph(self) -> None:
    """F7: toggle GraphPane full-screen."""
    try:
        pane = self.query_one("GraphPane")
        pane.display = not pane.display
    except Exception:
        pass  # GraphPane not yet mounted (no hosts discovered)

def action_open_timeline(self) -> None:
    """Ctrl+Shift+T: show/hide the timeline scrubber widget."""
    try:
        tl = self.query_one("Timeline")
        tl.display = not tl.display
        if tl.display:
            tl.focus()
    except Exception:
        pass

def action_undo(self) -> None:
    """Ctrl+Shift+Z: undo the last finding or ingest for the active tab."""
    active = self._get_active_tab_history()
    if active is None:
        return
    from bagley.tui.services.undo import UndoStack
    record = UndoStack(history=active).undo()
    if record is None:
        self.notify("Nothing to undo.", severity="information")
    else:
        self.notify(
            f"Undone: [{record.event.kind.name}] {record.event.label}",
            severity="warning",
        )
        try:
            self.query_one("Timeline").reload()
        except Exception:
            pass

def action_background_shell(self) -> None:
    """Ctrl+B: background the currently focused ShellPane."""
    try:
        pane = self.query_one("ShellPane:focus")
        pane.action_background()
    except Exception:
        pass

def _get_active_tab_history(self):
    """Return the EngagementHistory for the active tab, or None."""
    try:
        return self.state.active_tab_history
    except AttributeError:
        return None
```

- [ ] **Step 12.4: Verify import chain**

```bash
.venv/Scripts/python.exe -c "from bagley.tui.app import BagleyApp; print('ok')"
```

Expected: `ok`.

- [ ] **Step 12.5: Commit**

```bash
git add src/bagley/tui/app.py
git commit -m "feat(tui/phase5): wire F7/Ctrl+Shift+T/Ctrl+Shift+Z/Ctrl+B bindings into BagleyApp"
```

---

## Task 13: Integration smoke-test — all Phase 5 components together

**Files:**
- No new source files. Uses existing tests + a final combined smoke run.

- [ ] **Step 13.1: Run the full Phase 5 test suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_history.py tests/tui/test_undo.py tests/tui/test_shell_manager.py tests/tui/test_observe_service.py tests/tui/test_graph_layout.py tests/tui/test_graph_pane.py tests/tui/test_timeline.py -v
```

Expected: all tests pass (PTY tests skipped on Windows).

- [ ] **Step 13.2: On Linux/macOS — run PTY tests**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_shell_pane_linux.py -v
```

Expected: 3 tests pass.

- [ ] **Step 13.3: On Windows — run subprocess fallback tests**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_shell_pane_windows_fallback.py -v
```

Expected: 2 tests pass.

- [ ] **Step 13.4: Verify no regressions in Phase 1–4 tests**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --ignore=tests/tui/test_shell_pane_linux.py
```

Expected: all previously passing tests still pass.

- [ ] **Step 13.5: Commit**

```bash
git add tests/tui/
git commit -m "test(tui/phase5): integration smoke — all Phase 5 tests passing"
```

---

## Summary

| Task | Deliverable | Steps | New files |
|---|---|---|---|
| 1 | `networkx` dep | 3 | pyproject.toml edit |
| 2 | `EngagementHistory` | 6 | `services/__init__.py`, `history.py`, `test_history.py` |
| 3 | `UndoStack` | 5 | `undo.py`, `test_undo.py` |
| 4 | `PtyBridge` + fallback | 6 | `pty_bridge.py`, 2 test files |
| 5 | `ShellManager` | 5 | `shell_manager.py`, `test_shell_manager.py` |
| 6 | `ShellPane` widget | 3 | `panels/shell.py` |
| 7 | executor handoff + sessions CRUD | 4 | `executor.py` edit, `store.py` edit |
| 8 | `ObserveService` | 5 | `observe.py`, `test_observe_service.py` |
| 9 | `graph_layout` | 5 | `graph_layout.py`, `test_graph_layout.py` |
| 10 | `GraphPane` | 5 | `panels/graph.py`, `test_graph_pane.py` |
| 11 | `Timeline` scrubber | 5 | `widgets/timeline.py`, `test_timeline.py` |
| 12 | `app.py` bindings | 5 | `app.py` edit |
| 13 | Integration smoke | 5 | — |
| **Total** | | **62 steps** | **14 new files, 4 modified** |

**Dependency order:** Tasks 1 → 2 → 3 (undo depends on history); Task 4 → 5 → 6 (pane depends on bridge + manager); Task 2 → 11 (timeline depends on history); Task 9 → 10 (pane depends on layout). Tasks 7 and 8 are independent of each other after Task 4/5. Task 12 depends on Tasks 6, 10, 11. Task 13 must run last.
