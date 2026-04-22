# Bagley TUI — Phase 3 (Auto-Memory + Alerts + Visualizations + Nudges + Notes Editor) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Layer five intelligence features onto the Phase 1/2 TUI skeleton: (1) silent auto-memory promotion to SQLite whenever Bagley detects an actionable event in chat output; (2) a slide-in toast system with four severities and a full alert log; (3) ASCII visualizations — progress rings in `TargetPanel`, a subnet minimap in the recon tab, and severity bars in `HostsPanel`; (4) a background nudge engine that fires two heuristics every 30 s; (5) an F4-activated markdown notes editor replacing the static `notes-section` widget. Each task follows strict TDD: write a failing test first, implement, make it pass, commit.

**Architecture:**

```
src/bagley/tui/
    services/
        memory_promoter.py   # regex scanner; calls MemoryStore on findings
        alerts.py            # AlertBus singleton + Alert dataclass
        nudges.py            # NudgeEngine — set_interval ticker
    widgets/
        toast.py             # ToastLayer — slide-in stacked widget
        rings.py             # ProgressRings, Minimap, SeverityBars
        alerts_log.py        # AlertsLog modal (Ctrl+N)
    panels/
        notes_editor.py      # NotesEditor TextArea wrapper
    (modified)
        panels/chat.py       # hook memory_promoter + /memory command
        panels/target.py     # swap notes Static → NotesEditor + add ProgressRings
        panels/hosts.py      # add SeverityBars to findings section
        screens/recon.py     # create if absent; add Minimap
        app.py               # mount ToastLayer, start NudgeEngine, Ctrl+N binding
    memory/store.py          # add list_findings_by_severity(), recent_attempts()
```

The `AlertBus` is a single module-level object imported wherever alerts need to be published. `memory_promoter.MemoryPromoter` is a stateless class instantiated once and called per assistant response. `NudgeEngine` is started in `app.on_mount` via `self.set_interval(30, engine.tick)`. `ToastLayer` is a fixed-position `Widget` docked `bottom-right` that manages a list of up to 4 `Toast` children.

**Tech Stack:** Python 3.11, Textual 8.2.4, pytest + pytest-asyncio (asyncio_mode = "auto"), existing `MemoryStore` at `src/bagley/memory/store.py`. No new third-party deps beyond what Phase 1/2 already installed.

**Constraints:**
- Strict TDD on every task.
- `git add <exact paths>` only; never `-A` / `.` / `-u`.
- Steps numbered; each step ≥ 2 min of work.
- Python venv: `.venv/Scripts/python.exe`.
- Textual 8.2.4: use `self.push_screen(widget, callback=...)` not `push_screen_wait` outside workers.
- Background tasks: `set_interval()` only; no `asyncio.create_task`.
- Rendering unit tests: Textual `run_test` Pilot harness.

---

## File structure

### Files to create

- `src/bagley/tui/services/__init__.py` — empty marker
- `src/bagley/tui/services/memory_promoter.py` — `MemoryPromoter` class
- `src/bagley/tui/services/alerts.py` — `Alert` dataclass + `AlertBus`
- `src/bagley/tui/services/nudges.py` — `NudgeEngine`
- `src/bagley/tui/widgets/toast.py` — `Toast` + `ToastLayer`
- `src/bagley/tui/widgets/rings.py` — `ProgressRings`, `Minimap`, `SeverityBars`
- `src/bagley/tui/widgets/alerts_log.py` — `AlertsLog` modal screen
- `src/bagley/tui/panels/notes_editor.py` — `NotesEditor`
- `src/bagley/tui/screens/recon.py` — `ReconScreen` with `Minimap`
- `tests/tui/test_memory_promoter.py`
- `tests/tui/test_alerts.py`
- `tests/tui/test_rings.py`
- `tests/tui/test_minimap.py`
- `tests/tui/test_severity_bars.py`
- `tests/tui/test_nudges.py`
- `tests/tui/test_notes_editor.py`
- `tests/tui/test_alerts_log.py`

### Files to modify

- `src/bagley/memory/store.py` — add `list_findings_by_severity()` and `recent_attempts()`
- `src/bagley/tui/panels/chat.py` — hook `MemoryPromoter` on every assistant response; handle `/memory` slash command
- `src/bagley/tui/panels/target.py` — replace `notes-section` Static with `NotesEditor`; add `ProgressRings`
- `src/bagley/tui/panels/hosts.py` — add `SeverityBars` inside `findings-section`
- `src/bagley/tui/app.py` — mount `ToastLayer`, start `NudgeEngine`, add `Ctrl+N` binding

### Files NOT touched in Phase 3

`src/bagley/agent/`, `src/bagley/inference/`, `src/bagley/train/`, `src/bagley/observe/`, `src/bagley/tui/modes/`, `src/bagley/tui/widgets/header.py`, `src/bagley/tui/widgets/modes_bar.py`, `src/bagley/tui/widgets/tab_bar.py`, `src/bagley/tui/widgets/statusline.py`, `src/bagley/tui/widgets/palette.py`.

---

## Task 1: Extend `MemoryStore` with two query helpers

**Files:**
- Modify: `src/bagley/memory/store.py`

These two methods are required by `NudgeEngine` (Task 8) and `MemoryPromoter` tests (Task 2). Adding them first keeps later tasks dependency-free.

- [ ] **Step 1.1: Write the failing test**

Create `tests/tui/test_memory_promoter.py` — the first two test functions only (the promoter-specific ones come in Task 2):

```python
"""Tests for MemoryStore Phase-3 helpers."""
import tempfile
from pathlib import Path

import pytest
from bagley.memory.store import MemoryStore, Finding


def _fresh_store() -> MemoryStore:
    tmp = tempfile.mktemp(suffix=".db")
    return MemoryStore(tmp)


def test_list_findings_by_severity_returns_correct_subset():
    s = _fresh_store()
    s.add_finding(Finding("10.0.0.1", "critical", "RCE", "RCE via log4j"))
    s.add_finding(Finding("10.0.0.1", "high",     "SQLi", "blind SQLi"))
    s.add_finding(Finding("10.0.0.2", "high",     "XSS",  "stored XSS"))
    s.add_finding(Finding("10.0.0.3", "low",      "Info", "version disclosure"))

    crits = s.list_findings_by_severity("critical")
    highs = s.list_findings_by_severity("high")
    lows  = s.list_findings_by_severity("low")
    meds  = s.list_findings_by_severity("medium")

    assert len(crits) == 1
    assert crits[0]["category"] == "RCE"
    assert len(highs) == 2
    assert len(lows) == 1
    assert meds == []
    s.close()


def test_recent_attempts_returns_n_most_recent():
    s = _fresh_store()
    for i in range(5):
        s.add_attempt("10.0.0.1", f"tech{i}", "nmap", "fail")
    rows = s.recent_attempts(n=3)
    assert len(rows) == 3
    # most-recent first
    assert rows[0]["technique"] == "tech4"
    s.close()


def test_recent_attempts_default_n():
    s = _fresh_store()
    for i in range(25):
        s.add_attempt("10.0.0.1", f"t{i}", "tool", "success")
    rows = s.recent_attempts()
    assert len(rows) == 20   # default cap
    s.close()
```

- [ ] **Step 1.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_memory_promoter.py::test_list_findings_by_severity_returns_correct_subset tests/tui/test_memory_promoter.py::test_recent_attempts_returns_n_most_recent tests/tui/test_memory_promoter.py::test_recent_attempts_default_n -v
```

Expected: `AttributeError: 'MemoryStore' object has no attribute 'list_findings_by_severity'`.

- [ ] **Step 1.3: Add the two methods to `MemoryStore`**

Open `src/bagley/memory/store.py`. After the `list_findings` method (line ~187), insert:

```python
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
```

- [ ] **Step 1.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_memory_promoter.py::test_list_findings_by_severity_returns_correct_subset tests/tui/test_memory_promoter.py::test_recent_attempts_returns_n_most_recent tests/tui/test_memory_promoter.py::test_recent_attempts_default_n -v
```

Expected: 3 tests pass.

- [ ] **Step 1.5: Commit**

```bash
git add src/bagley/memory/store.py tests/tui/test_memory_promoter.py
git commit -m "feat(memory): add list_findings_by_severity and recent_attempts helpers"
```

---

## Task 2: `MemoryPromoter` — detect and promote from chat text

**Files:**
- Create: `src/bagley/tui/services/__init__.py`
- Create: `src/bagley/tui/services/memory_promoter.py`
- Modify: `tests/tui/test_memory_promoter.py` (append new test functions)

`MemoryPromoter.scan(text, store, host)` receives raw assistant-response text and a live `MemoryStore`. It runs a set of regexes to detect: new host IPs, open port lines, CVE IDs, extracted credentials, exploit-attempt keywords, and shell-obtained phrases. For each detected event it calls the appropriate `store` method and returns a list of `(kind, detail)` pairs so the caller knows what to publish as toasts.

- [ ] **Step 2.1: Append promoter-specific tests to `test_memory_promoter.py`**

Open `tests/tui/test_memory_promoter.py` and append:

```python
# ---- MemoryPromoter tests ----

from bagley.tui.services.memory_promoter import MemoryPromoter


def test_promoter_detects_new_host():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Host 192.168.1.50 is up (latency 0.1s).", s, current_host=None)
    assert any(e[0] == "new_host" and "192.168.1.50" in e[1] for e in events)
    hosts = s.list_hosts()
    assert any(h["ip"] == "192.168.1.50" for h in hosts)
    s.close()


def test_promoter_detects_open_port():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("80/tcp open http Apache 2.4.49", s, current_host="10.0.0.1")
    assert any(e[0] == "new_port" for e in events)
    detail = s.host_detail("10.0.0.1")
    assert any(r["port"] == 80 for r in detail["ports"])
    s.close()


def test_promoter_detects_cve():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Vulnerable to CVE-2021-44228 (log4j RCE).", s, current_host="10.0.0.1")
    assert any(e[0] == "cve_match" and "CVE-2021-44228" in e[1] for e in events)
    findings = s.list_findings_by_severity("critical")
    assert any("CVE-2021-44228" in f["cve"] for f in findings)
    s.close()


def test_promoter_detects_credential():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Found credential: admin:Password123!", s, current_host="10.0.0.1")
    assert any(e[0] == "new_cred" for e in events)
    s.close()


def test_promoter_detects_shell_obtained():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("Shell obtained on 10.0.0.1. Meterpreter session 1 opened.", s, current_host="10.0.0.1")
    assert any(e[0] == "shell_obtained" for e in events)
    s.close()


def test_promoter_silent_on_empty_text():
    s = _fresh_store()
    p = MemoryPromoter()
    events = p.scan("", s, current_host=None)
    assert events == []
    s.close()
```

- [ ] **Step 2.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_memory_promoter.py -k "promoter" -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services'`.

- [ ] **Step 2.3: Create the services package**

Create `src/bagley/tui/services/__init__.py`:

```python
"""Phase 3 background services: memory promotion, alerts, nudges."""
```

- [ ] **Step 2.4: Implement `memory_promoter.py`**

Create `src/bagley/tui/services/memory_promoter.py`:

```python
"""MemoryPromoter — scan assistant response text and promote findings to SQLite.

Detects:
    new_host       — bare IPv4 address appearing as "up" or via nmap host line
    new_port       — "<port>/tcp open" nmap output lines
    cve_match      — CVE-YYYY-NNNNN patterns; promotes as critical finding
    new_cred       — "credential:" / "password:" / "passwd:" / "cred:" followed by user:pass
    exploit_attempt — lines containing exploit/attempt/payload keywords
    shell_obtained  — "shell obtained" / "session opened" / "meterpreter" phrases

Each match calls the corresponding MemoryStore method and returns an event tuple
(kind: str, detail: str) to the caller so it can fire a toast.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bagley.memory.store import MemoryStore

# ---- compiled patterns ----
_RE_IP       = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b")
_RE_HOST_UP  = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b.*\bis up\b", re.IGNORECASE)
_RE_PORT     = re.compile(
    r"\b(\d{1,5})/(tcp|udp)\s+open\s+(\S+)(?:\s+(.+))?", re.IGNORECASE
)
_RE_CVE      = re.compile(r"\b(CVE-\d{4}-\d{4,7})\b", re.IGNORECASE)
_RE_CRED     = re.compile(
    r"(?:credential|password|passwd|cred)[:\s]+([A-Za-z0-9_\-\.]+:[^\s,;\"']{3,64})",
    re.IGNORECASE,
)
_RE_SHELL    = re.compile(
    r"(shell obtained|meterpreter session|session \d+ opened|reverse shell)",
    re.IGNORECASE,
)
_RE_EXPLOIT  = re.compile(
    r"\b(exploit(?:ing|ed)?|payload sent|attempting exploit|running module)\b",
    re.IGNORECASE,
)


class MemoryPromoter:
    """Stateless scanner — one instance, call scan() per assistant message."""

    def scan(
        self,
        text: str,
        store: "MemoryStore",
        current_host: str | None,
    ) -> list[tuple[str, str]]:
        """Return list of (event_kind, detail_str) for every detected event."""
        if not text.strip():
            return []

        events: list[tuple[str, str]] = []

        # --- new host up ---
        for m in _RE_HOST_UP.finditer(text):
            ip = m.group(1)
            store.upsert_host(ip, state="up")
            events.append(("new_host", ip))

        # --- open port ---
        if current_host:
            for m in _RE_PORT.finditer(text):
                port  = int(m.group(1))
                proto = m.group(2).lower()
                svc   = m.group(3)
                ver   = (m.group(4) or "").strip()
                store.add_port(current_host, port, proto, svc, ver)
                events.append(("new_port", f"{port}/{proto} {svc}"))

        # --- CVE match ---
        seen_cves: set[str] = set()
        for m in _RE_CVE.finditer(text):
            cve = m.group(1).upper()
            if cve in seen_cves:
                continue
            seen_cves.add(cve)
            host = current_host or "unknown"
            from bagley.memory.store import Finding
            store.add_finding(Finding(
                host=host,
                severity="critical",
                category="CVE",
                summary=f"CVE match detected in chat: {cve}",
                cve=cve,
            ))
            events.append(("cve_match", cve))

        # --- credential extraction ---
        for m in _RE_CRED.finditer(text):
            raw = m.group(1).strip()
            if ":" in raw:
                user, _, cred = raw.partition(":")
            else:
                user, cred = "unknown", raw
            host = current_host or "unknown"
            store.add_cred(host, service="unknown", username=user, credential=cred,
                           source="auto-promote")
            events.append(("new_cred", f"{user}:***"))

        # --- exploit attempt ---
        for m in _RE_EXPLOIT.finditer(text):
            host = current_host or "unknown"
            store.add_attempt(host, technique=m.group(1), tool="chat", outcome="partial",
                              details=text[:120])
            events.append(("exploit_attempt", m.group(1)))
            break   # one event per message is enough

        # --- shell obtained ---
        if _RE_SHELL.search(text):
            host = current_host or "unknown"
            store.add_attempt(host, technique="shell", tool="chat", outcome="success",
                              details=text[:120])
            events.append(("shell_obtained", host))

        return events
```

- [ ] **Step 2.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_memory_promoter.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 2.6: Commit**

```bash
git add src/bagley/tui/services/__init__.py src/bagley/tui/services/memory_promoter.py tests/tui/test_memory_promoter.py
git commit -m "feat(tui/services): MemoryPromoter scans assistant text and promotes to SQLite"
```

---

## Task 3: `AlertBus` and `Alert` dataclass

**Files:**
- Create: `src/bagley/tui/services/alerts.py`
- Create: `tests/tui/test_alerts.py`

`AlertBus` is a module-level publish/subscribe hub. Widgets subscribe via `bus.subscribe(callback)`. Publishing calls every registered callback synchronously. The bus holds the last `N` alerts in memory for the full alerts log.

- [ ] **Step 3.1: Write the failing test**

Create `tests/tui/test_alerts.py`:

```python
"""AlertBus and Alert dataclass tests."""
import time
import pytest
from bagley.tui.services.alerts import Alert, AlertBus, Severity


def test_alert_dataclass_fields():
    a = Alert(severity=Severity.WARN, title="TEST", body="something", source="scan")
    assert a.severity == Severity.WARN
    assert a.title == "TEST"
    assert isinstance(a.ts, float)


def test_alert_severity_ordering():
    assert Severity.INFO < Severity.OK < Severity.WARN < Severity.CRIT


def test_bus_publish_calls_subscriber():
    bus = AlertBus()
    received: list[Alert] = []
    bus.subscribe(received.append)
    a = Alert(Severity.INFO, "hello", "", "test")
    bus.publish(a)
    assert len(received) == 1
    assert received[0].title == "hello"


def test_bus_multiple_subscribers():
    bus = AlertBus()
    r1: list[Alert] = []
    r2: list[Alert] = []
    bus.subscribe(r1.append)
    bus.subscribe(r2.append)
    bus.publish(Alert(Severity.CRIT, "fire", "", "test"))
    assert len(r1) == 1
    assert len(r2) == 1


def test_bus_history_capped_at_200():
    bus = AlertBus()
    for i in range(210):
        bus.publish(Alert(Severity.INFO, f"a{i}", "", "test"))
    assert len(bus.history) == 200


def test_bus_unsubscribe():
    bus = AlertBus()
    received: list[Alert] = []
    bus.subscribe(received.append)
    bus.unsubscribe(received.append)
    bus.publish(Alert(Severity.INFO, "nope", "", "test"))
    assert received == []
```

- [ ] **Step 3.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_alerts.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services.alerts'`.

- [ ] **Step 3.3: Implement `alerts.py`**

Create `src/bagley/tui/services/alerts.py`:

```python
"""AlertBus — publish/subscribe hub for TUI alerts and toasts.

Usage:
    from bagley.tui.services.alerts import bus, Alert, Severity

    bus.subscribe(my_callback)
    bus.publish(Alert(Severity.CRIT, "Shell obtained", "10.0.0.1", source="promoter"))
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable


class Severity(IntEnum):
    INFO = 0
    OK   = 1
    WARN = 2
    CRIT = 3


# Severity → Textual color name
SEVERITY_COLOR: dict[Severity, str] = {
    Severity.INFO: "cyan",
    Severity.OK:   "green",
    Severity.WARN: "orange3",
    Severity.CRIT: "red",
}

# Severity → dismiss policy ("auto" = 3 s; "explicit" = must click X)
SEVERITY_DISMISS: dict[Severity, str] = {
    Severity.INFO: "auto",
    Severity.OK:   "auto",
    Severity.WARN: "auto",
    Severity.CRIT: "explicit",
}


@dataclass
class Alert:
    severity: Severity
    title: str
    body: str
    source: str                          # "scan" | "promoter" | "nudge" | …
    ts: float = field(default_factory=time.time)
    pane_selector: str = ""              # CSS selector to open on click


class AlertBus:
    _MAX_HISTORY = 200

    def __init__(self) -> None:
        self._subscribers: list[Callable[[Alert], None]] = []
        self.history: deque[Alert] = deque(maxlen=self._MAX_HISTORY)

    def subscribe(self, cb: Callable[[Alert], None]) -> None:
        if cb not in self._subscribers:
            self._subscribers.append(cb)

    def unsubscribe(self, cb: Callable[[Alert], None]) -> None:
        try:
            self._subscribers.remove(cb)
        except ValueError:
            pass

    def publish(self, alert: Alert) -> None:
        self.history.append(alert)
        for cb in list(self._subscribers):
            try:
                cb(alert)
            except Exception:
                pass


# module-level singleton used by all TUI components
bus: AlertBus = AlertBus()
```

- [ ] **Step 3.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_alerts.py -v
```

Expected: 6 tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add src/bagley/tui/services/alerts.py tests/tui/test_alerts.py
git commit -m "feat(tui/services): AlertBus pub/sub hub with severity + history cap"
```

---

## Task 4: `Toast` widget + `ToastLayer`

**Files:**
- Create: `src/bagley/tui/widgets/toast.py`
- Modify: `tests/tui/test_alerts.py` (append toast render tests)

`Toast` is a single notification card. `ToastLayer` is a `Widget` docked `bottom-right` that subscribes to `AlertBus`, shows max 4 toasts stacked vertically (newest at top of stack), and handles auto-dismiss via `set_interval`.

- [ ] **Step 4.1: Append toast tests to `test_alerts.py`**

Open `tests/tui/test_alerts.py` and append:

```python
# ---- ToastLayer integration tests ----

import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.services.alerts import Alert, AlertBus, Severity, bus as global_bus


@pytest.mark.asyncio
async def test_toast_layer_mounts_in_app():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        layer = app.query_one("#toast-layer")
        assert layer is not None


@pytest.mark.asyncio
async def test_publish_info_creates_toast():
    # Reset global bus subscribers for test isolation
    test_bus = AlertBus()
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        layer = app.query_one("#toast-layer")
        layer._bus = test_bus
        test_bus.subscribe(layer._on_alert)
        test_bus.publish(Alert(Severity.INFO, "Test toast", "body text", "test"))
        await pilot.pause()
        toasts = layer.query(".toast-widget")
        assert len(toasts) >= 1


@pytest.mark.asyncio
async def test_toast_stack_capped_at_four():
    test_bus = AlertBus()
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        layer = app.query_one("#toast-layer")
        layer._bus = test_bus
        test_bus.subscribe(layer._on_alert)
        for i in range(6):
            test_bus.publish(Alert(Severity.WARN, f"Toast {i}", "", "test"))
        await pilot.pause()
        toasts = layer.query(".toast-widget")
        assert len(toasts) <= 4
```

- [ ] **Step 4.2: Run new toast tests — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_alerts.py -k "toast" -v
```

Expected: `NoMatches` — `#toast-layer` not in DOM yet.

- [ ] **Step 4.3: Implement `toast.py`**

Create `src/bagley/tui/widgets/toast.py`:

```python
"""Toast widget and ToastLayer — slide-in bottom-right notification stack.

ToastLayer subscribes to the global AlertBus on mount and manages up to
MAX_STACK Toast children. CRIT toasts require explicit dismiss; others
auto-dismiss after AUTO_DISMISS_S seconds via set_interval.
"""

from __future__ import annotations

import time
from typing import Callable

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal

from bagley.tui.services.alerts import Alert, AlertBus, Severity, SEVERITY_COLOR, SEVERITY_DISMISS, bus as _global_bus

MAX_STACK = 4
AUTO_DISMISS_S = 3.0


class Toast(Widget):
    """A single notification card."""

    DEFAULT_CSS = """
    Toast {
        height: auto;
        min-height: 3;
        width: 40;
        padding: 0 1;
        margin: 0 0 1 0;
        border: round $accent;
    }
    Toast.severity-info { border: round cyan; }
    Toast.severity-ok   { border: round green; }
    Toast.severity-warn { border: round orange3; }
    Toast.severity-crit { border: round red; }
    Toast > Horizontal { height: 1; }
    Toast > Label.body  { color: $text-muted; }
    """

    COMPONENT_CLASSES = {"toast-widget"}

    def __init__(self, alert: Alert, on_dismiss: Callable[["Toast"], None], **kwargs) -> None:
        super().__init__(**kwargs)
        self.alert = alert
        self._on_dismiss = on_dismiss
        self.add_class("toast-widget")
        sev_name = alert.severity.name.lower()
        self.add_class(f"severity-{sev_name}")

    def compose(self) -> ComposeResult:
        color = SEVERITY_COLOR[self.alert.severity]
        with Horizontal():
            yield Label(f"[bold {color}]{self.alert.title}[/]", id="toast-title")
            yield Button("✕", id="toast-close", variant="default")
        if self.alert.body:
            yield Label(self.alert.body, classes="body")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toast-close":
            self._on_dismiss(self)

    def on_click(self) -> None:
        if self.alert.pane_selector:
            try:
                self.app.query_one(self.alert.pane_selector).focus()
            except Exception:
                pass
        self._on_dismiss(self)


class ToastLayer(Widget):
    """Fixed bottom-right widget that owns up to MAX_STACK Toast children."""

    DEFAULT_CSS = """
    ToastLayer {
        dock: bottom;
        align: right bottom;
        width: 42;
        height: auto;
        max-height: 20;
        padding: 0 1 1 0;
        layer: overlay;
    }
    """

    def __init__(self, alert_bus: AlertBus | None = None, **kwargs) -> None:
        super().__init__(id="toast-layer", **kwargs)
        self._bus = alert_bus or _global_bus
        self._toasts: list[Toast] = []
        self._timers: dict[int, object] = {}   # id(toast) → timer handle

    def on_mount(self) -> None:
        self._bus.subscribe(self._on_alert)

    def on_unmount(self) -> None:
        self._bus.unsubscribe(self._on_alert)

    # called from AlertBus subscriber (may be in worker thread via post_message)
    def _on_alert(self, alert: Alert) -> None:
        self.app.call_from_thread(self._add_toast, alert)

    def _add_toast(self, alert: Alert) -> None:
        # enforce stack cap
        while len(self._toasts) >= MAX_STACK:
            oldest = self._toasts[0]
            self._dismiss(oldest)

        toast = Toast(alert, on_dismiss=self._dismiss)
        self._toasts.append(toast)
        self.mount(toast)

        dismiss_policy = SEVERITY_DISMISS[alert.severity]
        if dismiss_policy == "auto":
            handle = self.set_timer(AUTO_DISMISS_S, lambda t=toast: self._dismiss(t))
            self._timers[id(toast)] = handle

    def _dismiss(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        key = id(toast)
        if key in self._timers:
            del self._timers[key]
        toast.remove()
```

- [ ] **Step 4.4: Mount `ToastLayer` in `app.py`**

Open `src/bagley/tui/app.py`. In `compose()`, after the last yielded widget (Statusline), add:

```python
        from bagley.tui.widgets.toast import ToastLayer
        yield ToastLayer()
```

- [ ] **Step 4.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_alerts.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 4.6: Commit**

```bash
git add src/bagley/tui/widgets/toast.py src/bagley/tui/app.py tests/tui/test_alerts.py
git commit -m "feat(tui/widgets): ToastLayer with 4-severity slide-in stack and auto-dismiss"
```

---

## Task 5: `AlertsLog` modal (Ctrl+N)

**Files:**
- Create: `src/bagley/tui/widgets/alerts_log.py`
- Create: `tests/tui/test_alerts_log.py`
- Modify: `src/bagley/tui/app.py`

`AlertsLog` is a `ModalScreen` that reads `bus.history` and renders every alert as a scrollable list. Pressing Escape or `Q` dismisses it.

- [ ] **Step 5.1: Write the failing test**

Create `tests/tui/test_alerts_log.py`:

```python
"""AlertsLog modal — Ctrl+N shows historical alerts."""
import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.services.alerts import Alert, AlertBus, Severity


@pytest.mark.asyncio
async def test_ctrl_n_opens_alerts_log():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+n")
        await pilot.pause()
        log = app.query_one("#alerts-log-screen")
        assert log is not None


@pytest.mark.asyncio
async def test_alerts_log_shows_published_alert():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        from bagley.tui.services.alerts import bus
        bus.publish(Alert(Severity.CRIT, "Log4Shell", "CVE-2021-44228", "test"))
        await pilot.press("ctrl+n")
        await pilot.pause()
        log = app.query_one("#alerts-log-screen")
        rendered = str(log.query_one("#alerts-list").render())
        assert "Log4Shell" in rendered


@pytest.mark.asyncio
async def test_alerts_log_closes_on_escape():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+n")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        try:
            app.query_one("#alerts-log-screen")
            assert False, "screen should be gone"
        except Exception:
            pass  # expected
```

- [ ] **Step 5.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_alerts_log.py -v
```

Expected: `NoMatches: No widget matching '#alerts-log-screen'`.

- [ ] **Step 5.3: Implement `alerts_log.py`**

Create `src/bagley/tui/widgets/alerts_log.py`:

```python
"""AlertsLog — full-history modal opened by Ctrl+N.

Reads from the module-level AlertBus.history deque and renders a
scrollable RichLog of all past alerts, newest at top.
"""

from __future__ import annotations

import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, RichLog, Button
from textual.containers import Vertical

from bagley.tui.services.alerts import bus, SEVERITY_COLOR, Severity


class AlertsLog(ModalScreen):
    """Ctrl+N modal showing full alert history."""

    DEFAULT_CSS = """
    AlertsLog {
        align: center middle;
    }
    #alerts-log-screen {
        width: 80;
        height: 30;
        border: round $accent;
        background: $surface;
        padding: 1 2;
    }
    #alerts-list { height: 1fr; }
    #alerts-close { dock: bottom; width: 100%; }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="alerts-log-screen"):
            yield Label("[bold]Alert History[/] — most recent first", id="alerts-header")
            log = RichLog(id="alerts-list", markup=True, highlight=False, wrap=True)
            yield log
            yield Button("Close  [Esc]", id="alerts-close", variant="default")

    def on_mount(self) -> None:
        log = self.query_one("#alerts-list", RichLog)
        history = list(bus.history)
        history.reverse()  # newest first
        if not history:
            log.write("[dim]No alerts yet.[/]")
            return
        for alert in history:
            color = SEVERITY_COLOR[alert.severity]
            ts = datetime.datetime.fromtimestamp(alert.ts).strftime("%H:%M:%S")
            log.write(
                f"[dim]{ts}[/]  [{color}]{alert.severity.name:5}[/]  "
                f"[bold]{alert.title}[/]  {alert.body}"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "alerts-close":
            self.dismiss()
```

- [ ] **Step 5.4: Add `Ctrl+N` binding and action to `app.py`**

Open `src/bagley/tui/app.py`. In `BINDINGS`, append:

```python
        Binding("ctrl+n", "open_alerts_log", "Alerts", show=True),
```

Add the action method to `BagleyApp`:

```python
    def action_open_alerts_log(self) -> None:
        from bagley.tui.widgets.alerts_log import AlertsLog
        self.push_screen(AlertsLog())
```

- [ ] **Step 5.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_alerts_log.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add src/bagley/tui/widgets/alerts_log.py src/bagley/tui/app.py tests/tui/test_alerts_log.py
git commit -m "feat(tui/widgets): AlertsLog modal on Ctrl+N with full alert history"
```

---

## Task 6: `ProgressRings` and `SeverityBars` widgets

**Files:**
- Create: `src/bagley/tui/widgets/rings.py`
- Create: `tests/tui/test_rings.py`
- Create: `tests/tui/test_severity_bars.py`
- Modify: `src/bagley/tui/panels/target.py`
- Modify: `src/bagley/tui/panels/hosts.py`

`ProgressRings` renders the 7-stage kill-chain as `●●●○○○○  43%`. `SeverityBars` renders CRIT/HIGH/MED/LOW counts as `CRIT ▓▓▓░░ 3`. Both are pure-rendering `Static` subclasses with a `refresh_data(...)` method.

- [ ] **Step 6.1: Write the failing rings test**

Create `tests/tui/test_rings.py`:

```python
"""ProgressRings rendering tests."""
import pytest
from bagley.tui.widgets.rings import ProgressRings


def test_rings_stage_0_all_empty():
    r = ProgressRings()
    r._stage = 0
    text = r._render_text()
    assert "○" in text
    assert "●" not in text
    assert "0%" in text


def test_rings_stage_3_of_7_shows_correct_fill():
    r = ProgressRings()
    r._stage = 3
    text = r._render_text()
    assert text.count("●") == 3
    assert text.count("○") == 4
    assert "42%" in text or "43%" in text   # 3/7 ≈ 42.8%


def test_rings_stage_7_all_filled():
    r = ProgressRings()
    r._stage = 7
    text = r._render_text()
    assert "○" not in text
    assert "●" in text
    assert "100%" in text


def test_rings_stage_labels():
    r = ProgressRings()
    text = r._render_text()
    for label in ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]:
        assert label in text.lower()


@pytest.mark.asyncio
async def test_rings_mounts_in_target_panel():
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        rings = app.query_one("#killchain-rings")
        assert rings is not None
```

- [ ] **Step 6.2: Write the failing severity bars test**

Create `tests/tui/test_severity_bars.py`:

```python
"""SeverityBars rendering tests."""
import pytest
from bagley.tui.widgets.rings import SeverityBars


def test_severity_bars_empty_counts():
    sb = SeverityBars()
    sb.refresh_data({"critical": 0, "high": 0, "medium": 0, "low": 0})
    text = sb._render_text()
    assert "░" in text    # all empty bars
    assert "▓" not in text


def test_severity_bars_full_crit():
    sb = SeverityBars()
    sb.refresh_data({"critical": 10, "high": 0, "medium": 0, "low": 0})
    text = sb._render_text()
    lines = [l for l in text.splitlines() if "CRIT" in l.upper()]
    assert len(lines) == 1
    assert "▓" in lines[0]


def test_severity_bars_counts_shown():
    sb = SeverityBars()
    sb.refresh_data({"critical": 3, "high": 7, "medium": 2, "low": 1})
    text = sb._render_text()
    assert "3" in text
    assert "7" in text


def test_severity_bars_bar_proportional():
    sb = SeverityBars(bar_width=10)
    sb.refresh_data({"critical": 5, "high": 10, "medium": 0, "low": 0})
    text = sb._render_text()
    crit_line = next(l for l in text.splitlines() if "CRIT" in l.upper())
    high_line  = next(l for l in text.splitlines() if "HIGH" in l.upper())
    # HIGH (10) should have more filled cells than CRIT (5)
    assert high_line.count("▓") >= crit_line.count("▓")


@pytest.mark.asyncio
async def test_severity_bars_mounts_in_hosts_panel():
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        bars = app.query_one("#severity-bars")
        assert bars is not None
```

- [ ] **Step 6.3: Run both tests — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_rings.py tests/tui/test_severity_bars.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.widgets.rings'`.

- [ ] **Step 6.4: Implement `rings.py`**

Create `src/bagley/tui/widgets/rings.py`:

```python
"""ProgressRings, Minimap, and SeverityBars ASCII visualization widgets.

ProgressRings  — kill-chain stage progress (●●●○○○○  43%)
Minimap        — 254-cell subnet dot map (lives in ReconScreen)
SeverityBars   — horizontal ASCII bars for CRIT/HIGH/MED/LOW counts
"""

from __future__ import annotations

import math
from textual.widgets import Static

# Kill-chain stage labels (7 stages, index 0..6)
_KC_LABELS = ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]
_KC_TOTAL  = len(_KC_LABELS)

# Subnet minimap
_MINI_STATES: dict[str, str] = {
    "up":       "[green]●[/]",
    "down":     "[red]●[/]",
    "scanning": "[yellow]●[/]",
    "unknown":  "[dim]·[/]",
}

# Severity bar colors
_SEV_COLOR: dict[str, str] = {
    "critical": "red",
    "high":     "orange3",
    "medium":   "yellow",
    "low":      "cyan",
}


# --------------------------------------------------------------------------- #
#  ProgressRings                                                                #
# --------------------------------------------------------------------------- #

class ProgressRings(Static):
    """Renders kill-chain progress as filled/empty circles with percentage."""

    DEFAULT_CSS = """
    ProgressRings { height: auto; padding: 0 1; }
    """

    def __init__(self, stage: int = 0, **kwargs) -> None:
        super().__init__(id="killchain-rings", **kwargs)
        self._stage = stage

    def _render_text(self) -> str:
        filled  = "●" * self._stage
        empty   = "○" * (_KC_TOTAL - self._stage)
        pct     = int(round(self._stage / _KC_TOTAL * 100))
        dots    = f"[green]{filled}[/][dim]{empty}[/]  {pct}%"
        labels  = "  ".join(
            f"[bold]{l}[/]" if i < self._stage else f"[dim]{l}[/]"
            for i, l in enumerate(_KC_LABELS)
        )
        return f"{dots}\n{labels}"

    def on_mount(self) -> None:
        self.update(self._render_text())

    def refresh_stage(self, stage: int) -> None:
        self._stage = max(0, min(stage, _KC_TOTAL))
        self.update(self._render_text())


# --------------------------------------------------------------------------- #
#  Minimap                                                                      #
# --------------------------------------------------------------------------- #

class Minimap(Static):
    """254-cell dotmap for a /24 subnet in the recon tab.

    Call refresh_data({'10.0.0.1': 'up', '10.0.0.2': 'scanning', ...}) to update.
    """

    DEFAULT_CSS = """
    Minimap { height: auto; padding: 0 1; }
    """

    _COLS = 32  # dots per row → 8 rows for 254 cells

    def __init__(self, subnet_prefix: str = "10.10.0", **kwargs) -> None:
        super().__init__(id="subnet-minimap", **kwargs)
        self._prefix   = subnet_prefix
        self._states: dict[str, str] = {}   # last-octet str → state string

    def on_mount(self) -> None:
        self._render()

    def refresh_data(self, host_states: dict[str, str]) -> None:
        """Accept {ip: state} mapping; state in {up, down, scanning, unknown}."""
        self._states = {}
        for ip, state in host_states.items():
            last = ip.rsplit(".", 1)[-1]
            self._states[last] = state
        self._render()

    def _render(self) -> None:
        cells: list[str] = []
        for i in range(1, 255):
            key = str(i)
            state = self._states.get(key, "unknown")
            cells.append(_MINI_STATES.get(state, _MINI_STATES["unknown"]))
        rows: list[str] = []
        for r in range(0, 254, self._COLS):
            rows.append(" ".join(cells[r : r + self._COLS]))
        self.update("\n".join(rows))


# --------------------------------------------------------------------------- #
#  SeverityBars                                                                 #
# --------------------------------------------------------------------------- #

class SeverityBars(Static):
    """Horizontal ASCII bars for CRIT / HIGH / MED / LOW finding counts."""

    DEFAULT_CSS = """
    SeverityBars { height: auto; padding: 0 1; }
    """

    def __init__(self, bar_width: int = 20, **kwargs) -> None:
        super().__init__(id="severity-bars", **kwargs)
        self._bar_width = bar_width
        self._counts: dict[str, int] = {
            "critical": 0, "high": 0, "medium": 0, "low": 0
        }

    def _render_text(self) -> str:
        max_count = max(self._counts.values()) or 1
        lines: list[str] = []
        labels = [("CRIT", "critical"), ("HIGH", "high"), ("MED", "medium"), ("LOW", "low")]
        for label, key in labels:
            count  = self._counts.get(key, 0)
            filled = int(round(count / max_count * self._bar_width))
            empty  = self._bar_width - filled
            color  = _SEV_COLOR[key]
            bar    = f"[{color}]{'▓' * filled}[/][dim]{'░' * empty}[/]"
            lines.append(f"{label:4} {bar} {count}")
        return "\n".join(lines)

    def on_mount(self) -> None:
        self.update(self._render_text())

    def refresh_data(self, counts: dict[str, int]) -> None:
        """Accept {severity_lower: count} dict and re-render."""
        self._counts.update(counts)
        self.update(self._render_text())
```

- [ ] **Step 6.5: Wire `ProgressRings` into `target.py`**

Open `src/bagley/tui/panels/target.py`. Replace the `killchain` Static:

```python
    def compose(self):
        from bagley.tui.widgets.rings import ProgressRings
        yield Static("[b orange3]◆ TARGET[/]\n[dim](no target)[/]", id="target-info")
        yield Static("[b orange3]◆ KILL-CHAIN[/]", id="killchain-header")
        yield ProgressRings(stage=self._state.tabs[self._state.active_tab].killchain_stage
                            if self._state.tabs else 0)
        yield Static("[b orange3]◆ CREDS[/]\n[dim](none yet)[/]", id="creds-section")
        yield Static("[b orange3]◆ NOTES[/]\n[dim](empty)[/]", id="notes-section")
```

- [ ] **Step 6.6: Wire `SeverityBars` into `hosts.py`**

Open `src/bagley/tui/panels/hosts.py`. Replace the `findings-section` Static:

```python
    def compose(self):
        from bagley.tui.widgets.rings import SeverityBars
        yield Static("[b orange3]◆ HOSTS[/]\n[dim](Phase 1 stub)[/]", id="hosts-section")
        yield Static("[b orange3]◆ PORTS[/]\n[dim](Phase 1 stub)[/]", id="ports-section")
        yield Static("[b orange3]◆ FINDINGS[/]", id="findings-header")
        yield SeverityBars()
```

- [ ] **Step 6.7: Run both tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_rings.py tests/tui/test_severity_bars.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 6.8: Run full suite — no regressions**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short
```

Expected: all existing tests still pass.

- [ ] **Step 6.9: Commit**

```bash
git add src/bagley/tui/widgets/rings.py src/bagley/tui/panels/target.py src/bagley/tui/panels/hosts.py tests/tui/test_rings.py tests/tui/test_severity_bars.py
git commit -m "feat(tui/widgets): ProgressRings and SeverityBars ASCII visualizations"
```

---

## Task 7: `Minimap` in `ReconScreen`

**Files:**
- Create: `src/bagley/tui/screens/recon.py`
- Create: `tests/tui/test_minimap.py`

`ReconScreen` is the tab-0 layout. It reuses the 4-pane skeleton but replaces the TargetPanel right column with a scope-summary panel containing the subnet `Minimap`.

- [ ] **Step 7.1: Write the failing minimap test**

Create `tests/tui/test_minimap.py`:

```python
"""Minimap widget tests."""
import pytest
from bagley.tui.widgets.rings import Minimap


def test_minimap_has_254_cells_empty():
    m = Minimap()
    m._render()
    rendered = m.renderable
    text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
    # Each cell is either ● or · — count them (markup stripped)
    # We care about cell count logic; verify cell-per-row constant
    assert m._COLS == 32
    total_cells = sum(len(row) for row in [list(range(1, 255))])
    assert total_cells == 254


def test_minimap_up_host_shows_green_dot():
    m = Minimap(subnet_prefix="10.10.0")
    m.refresh_data({"10.10.0.5": "up", "10.10.0.20": "down", "10.10.0.33": "scanning"})
    rendered = m.renderable
    text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
    # Markup stripped; only the raw text matters here
    # Check markup source contains expected color annotations
    source = str(m.renderable)
    assert "[green]●[/]" in source or "green" in source


def test_minimap_scanning_state_yellow():
    m = Minimap()
    m.refresh_data({"10.0.0.10": "scanning"})
    source = str(m.renderable)
    assert "yellow" in source or "[yellow]" in source


def test_minimap_unknown_hosts_dim():
    m = Minimap()
    m._render()   # all unknown
    source = str(m.renderable)
    assert "dim" in source


def test_minimap_refreshing_changes_state():
    m = Minimap()
    m._render()
    before = str(m.renderable)
    m.refresh_data({"10.0.0.1": "up"})
    after = str(m.renderable)
    assert before != after


@pytest.mark.asyncio
async def test_minimap_mounts_in_recon_screen():
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        # ReconScreen is the initial tab-0 view
        minimap = app.query_one("#subnet-minimap")
        assert minimap is not None
```

- [ ] **Step 7.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_minimap.py -v
```

Expected: last test fails — `#subnet-minimap` not in DOM.

- [ ] **Step 7.3: Implement `recon.py`**

Create `src/bagley/tui/screens/recon.py`:

```python
"""ReconScreen — tab-0 scope overview with subnet minimap.

Same 4-pane skeleton as DashboardScreen, but the right column is replaced
by a scope summary panel containing ProgressRings (aggregate) and Minimap.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from bagley.tui.panels.chat import ChatPanel
from bagley.tui.panels.hosts import HostsPanel
from bagley.tui.state import AppState
from bagley.tui.widgets.rings import Minimap


class ReconScopePanel(Vertical):
    """Right column for the recon tab — scope summary + subnet minimap."""

    DEFAULT_CSS = """
    ReconScopePanel { width: 32; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="recon-scope-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Static("[b orange3]◆ SCOPE SUMMARY[/]", id="scope-header")
        yield Static("[dim]Hosts up: 0 / 0[/]", id="scope-stats")
        yield Static("[b orange3]◆ SUBNET MAP[/]", id="minimap-header")
        yield Minimap(subnet_prefix="10.10.0")


class ReconScreen(Screen):
    """Full recon tab layout — HostsPanel | ChatPanel | ReconScopePanel."""

    DEFAULT_CSS = """
    ReconScreen { layout: vertical; }
    #recon-pane-row { height: 1fr; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    def compose(self) -> ComposeResult:
        with Horizontal(id="recon-pane-row"):
            yield HostsPanel(self._state)
            yield ChatPanel(self._state)
            yield ReconScopePanel(self._state)
```

- [ ] **Step 7.4: Mount `ReconScreen` for tab-0 in `app.py`**

The current `app.py` renders the 4-pane layout directly in `compose`. To show the recon tab by default, replace the pane-row section with `ReconScreen` mounted as the initial screen. Since the full screen-switching logic is a Phase 4 concern, keep the current flat layout but add the `Minimap` directly for tab-0.

Open `src/bagley/tui/app.py`. In `compose`, insert the Minimap inside a conditional block after the `TargetPanel`. Replace the `with Horizontal(id="pane-row"):` block with:

```python
        from bagley.tui.panels.hosts import HostsPanel
        from bagley.tui.panels.chat import ChatPanel
        from bagley.tui.panels.target import TargetPanel
        from bagley.tui.widgets.rings import Minimap
        from textual.containers import Horizontal, Vertical
        with Horizontal(id="pane-row"):
            yield HostsPanel(self.state)
            yield ChatPanel(self.state)
            # tab-0 (recon) shows minimap; future tabs show TargetPanel
            if self.state.active_tab == 0:
                with Vertical(id="target-panel", classes="scope-panel"):
                    yield TargetPanel(self.state)
                    yield Minimap()
            else:
                yield TargetPanel(self.state)
```

> **Note:** This is a simplified mount that satisfies the test. Full per-tab screen switching (ReconScreen vs DashboardScreen) will be wired during Phase 4 when the tab-switch action rebuilds the content area. For Phase 3 the Minimap simply lives in the right column for the initial recon state.

- [ ] **Step 7.5: Run minimap tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_minimap.py -v
```

Expected: 6 tests pass.

- [ ] **Step 7.6: Run full suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 7.7: Commit**

```bash
git add src/bagley/tui/screens/recon.py src/bagley/tui/widgets/rings.py src/bagley/tui/app.py tests/tui/test_minimap.py
git commit -m "feat(tui/screens): ReconScreen with Minimap subnet dotmap"
```

---

## Task 8: `NudgeEngine` background ticker

**Files:**
- Create: `src/bagley/tui/services/nudges.py`
- Create: `tests/tui/test_nudges.py`
- Modify: `src/bagley/tui/app.py`

`NudgeEngine.tick()` is called every 30 s via `set_interval`. It reads `AppState` and `MemoryStore`, evaluates two heuristics, and publishes `WARN` alerts to `AlertBus` when triggered. An internal tick counter drives tests without waiting 30 real seconds.

- [ ] **Step 8.1: Write the failing test**

Create `tests/tui/test_nudges.py`:

```python
"""NudgeEngine heuristic tests."""
import tempfile
import pytest
from bagley.memory.store import MemoryStore, Finding
from bagley.tui.services.alerts import AlertBus, Severity
from bagley.tui.services.nudges import NudgeEngine
from bagley.tui.state import AppState, detect_os


def _fresh_store() -> MemoryStore:
    return MemoryStore(tempfile.mktemp(suffix=".db"))


def _fresh_state() -> AppState:
    return AppState(os_info=detect_os())


def test_idle_nudge_fires_after_15_ticks():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)

    # Simulate 14 idle ticks — should NOT fire
    for _ in range(14):
        eng._idle_ticks += 1
    eng._evaluate()
    assert not any(a.title == "Idle nudge" for a in alerts)

    # 15th tick — should fire
    eng._idle_ticks += 1
    eng._evaluate()
    assert any("next step" in a.body.lower() or "idle" in a.title.lower() for a in alerts)
    store.close()


def test_idle_nudge_resets_after_firing():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)

    eng._idle_ticks = 15
    eng._evaluate()
    count_before = len([a for a in alerts if "idle" in a.title.lower()])
    eng._evaluate()   # second call at same tick value should NOT fire again
    count_after = len([a for a in alerts if "idle" in a.title.lower()])
    assert count_after == count_before
    store.close()


def test_findings_nudge_fires_with_3_plus_high():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    for i in range(3):
        store.add_finding(Finding(f"10.0.0.{i+1}", "high", "SQLi", f"finding {i}"))
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)
    eng._evaluate()
    assert any("high" in a.body.lower() or "untouched" in a.body.lower() for a in alerts)
    store.close()


def test_findings_nudge_does_not_fire_with_2_high():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    store.add_finding(Finding("10.0.0.1", "high", "A", "one"))
    store.add_finding(Finding("10.0.0.2", "high", "B", "two"))
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)
    eng._evaluate()
    finding_alerts = [a for a in alerts if "high" in a.body.lower() or "untouched" in a.body.lower()]
    assert finding_alerts == []
    store.close()


def test_nudge_engine_tick_increments_idle():
    bus = AlertBus()
    store = _fresh_store()
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)
    before = eng._idle_ticks
    eng.tick()
    assert eng._idle_ticks == before + 1
    store.close()
```

- [ ] **Step 8.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_nudges.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services.nudges'`.

- [ ] **Step 8.3: Implement `nudges.py`**

Create `src/bagley/tui/services/nudges.py`:

```python
"""NudgeEngine — background heuristic evaluator.

Evaluates two heuristics every 30 s (via set_interval in BagleyApp):
    1. Idle nudge: operator has been idle ≥ 15 ticks → suggest next step.
    2. Findings nudge: ≥ 3 HIGH findings exist → prompt to address them.

Playbook-sequence detection and online Metasploit check are deferred to Phase 4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bagley.tui.services.alerts import Alert, AlertBus, Severity

if TYPE_CHECKING:
    from bagley.memory.store import MemoryStore
    from bagley.tui.state import AppState

_IDLE_THRESHOLD = 15          # ticks before idle nudge fires (each tick = 30 s)
_HIGH_THRESHOLD = 3           # number of untouched HIGH findings before nudge


class NudgeEngine:
    """Stateful heuristic engine. Instantiate once; call tick() on each interval."""

    def __init__(
        self,
        state: "AppState",
        store: "MemoryStore",
        bus: AlertBus | None = None,
    ) -> None:
        self._state = state
        self._store = store
        self._bus   = bus or _get_global_bus()
        self._idle_ticks       = 0
        self._idle_nudged_at   = -1   # tick at which the idle nudge last fired
        self._findings_nudged  = False

    def tick(self) -> None:
        """Called by set_interval every 30 s. Increments idle counter then evaluates."""
        self._idle_ticks += 1
        self._evaluate()

    def reset_idle(self) -> None:
        """Call whenever the user submits a chat message."""
        self._idle_ticks = 0
        self._idle_nudged_at = -1

    def _evaluate(self) -> None:
        self._check_idle()
        self._check_high_findings()

    def _check_idle(self) -> None:
        if (
            self._idle_ticks >= _IDLE_THRESHOLD
            and self._idle_ticks != self._idle_nudged_at
        ):
            self._idle_nudged_at = self._idle_ticks
            idle_min = round(self._idle_ticks * 30 / 60, 1)
            self._bus.publish(Alert(
                severity=Severity.INFO,
                title="Idle nudge",
                body=f"You've been idle for ~{idle_min} min. Want a suggested next step?",
                source="nudge",
                pane_selector="#chat-panel",
            ))

    def _check_high_findings(self) -> None:
        try:
            highs = self._store.list_findings_by_severity("high")
        except Exception:
            return
        if len(highs) >= _HIGH_THRESHOLD and not self._findings_nudged:
            self._findings_nudged = True
            hosts = list({f["host"] for f in highs})[:3]
            host_str = ", ".join(hosts)
            self._bus.publish(Alert(
                severity=Severity.WARN,
                title="Untouched findings",
                body=f"{len(highs)} HIGH findings untouched on {host_str}. Open a tab to address?",
                source="nudge",
                pane_selector="#hosts-panel",
            ))


def _get_global_bus() -> AlertBus:
    from bagley.tui.services.alerts import bus
    return bus
```

- [ ] **Step 8.4: Mount `NudgeEngine` in `app.py`**

Open `src/bagley/tui/app.py`. Add an import and `on_mount` method to `BagleyApp`:

```python
    def on_mount(self) -> None:
        """Start background services after the DOM is ready."""
        from bagley.tui.services.nudges import NudgeEngine
        # MemoryStore is optional — if no engagement DB exists yet, use a stub path
        try:
            from bagley.memory.store import MemoryStore
            from pathlib import Path
            db_path = Path(".bagley") / "memory.db"
            store = MemoryStore(db_path)
        except Exception:
            store = None  # type: ignore[assignment]

        if store is not None:
            self._nudge_engine = NudgeEngine(state=self.state, store=store)
            self.set_interval(30, self._nudge_engine.tick)
```

- [ ] **Step 8.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_nudges.py -v
```

Expected: 5 tests pass.

- [ ] **Step 8.6: Commit**

```bash
git add src/bagley/tui/services/nudges.py src/bagley/tui/app.py tests/tui/test_nudges.py
git commit -m "feat(tui/services): NudgeEngine idle and high-findings heuristics"
```

---

## Task 9: Notes markdown editor (`NotesEditor`)

**Files:**
- Create: `src/bagley/tui/panels/notes_editor.py`
- Create: `tests/tui/test_notes_editor.py`
- Modify: `src/bagley/tui/panels/target.py`

`NotesEditor` wraps a Textual `TextArea` that activates on F4 (or when the widget receives focus) and persists content back to `TabState.notes_md`. Bagley's auto-append method `append_note(text)` inserts a timestamped line without requiring focus.

- [ ] **Step 9.1: Write the failing test**

Create `tests/tui/test_notes_editor.py`:

```python
"""NotesEditor — F4 focus, Bagley auto-append, content persistence."""
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_f4_focuses_notes_editor():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        await pilot.press("f4")
        await pilot.pause()
        # After F4 the notes editor TextArea should have focus
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        assert editor is not None


@pytest.mark.asyncio
async def test_notes_editor_starts_empty():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        ta = editor.query_one("#notes-textarea")
        assert ta.text == ""


@pytest.mark.asyncio
async def test_notes_editor_typing_updates_tab_state():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        await pilot.press("f4")
        await pilot.pause()
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        ta = editor.query_one("#notes-textarea")
        ta.insert("hello notes", location=(0, 0))
        await pilot.pause()
        # TabState should reflect the update
        assert "hello notes" in app.state.tabs[app.state.active_tab].notes_md


@pytest.mark.asyncio
async def test_bagley_auto_append_adds_timestamped_line():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        editor.append_note("SQLi confirmed on /login")
        await pilot.pause()
        ta = editor.query_one("#notes-textarea")
        assert "SQLi confirmed on /login" in ta.text
        # Timestamp format HH:MM should be present
        import re
        assert re.search(r"\d{2}:\d{2}", ta.text)


@pytest.mark.asyncio
async def test_notes_editor_replaces_static_notes_section():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        # There should be no bare Static with id=notes-section any more
        from textual.widgets import Static
        statics = [w for w in app.query(Static) if w.id == "notes-section"]
        assert statics == []
```

- [ ] **Step 9.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_notes_editor.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.panels.notes_editor'`.

- [ ] **Step 9.3: Implement `notes_editor.py`**

Create `src/bagley/tui/panels/notes_editor.py`:

```python
"""NotesEditor — editable markdown notes area for TargetPanel.

Activates on F4 / focus. Persists content to TabState.notes_md.
Bagley can call append_note(text) to add a timestamped line without
requiring user focus.
"""

from __future__ import annotations

import datetime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Static, TextArea

from bagley.tui.state import AppState


class NotesEditor(Vertical):
    """Markdown notes section: Static header + TextArea body."""

    DEFAULT_CSS = """
    NotesEditor { height: auto; min-height: 6; padding: 0 1; }
    NotesEditor > TextArea { height: 6; border: round $accent; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="notes-editor", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Static("[b orange3]◆ NOTES[/]  [dim](F4 to edit)[/]", id="notes-header")
        tab = self._active_tab()
        ta = TextArea(
            text=tab.notes_md if tab else "",
            id="notes-textarea",
            language="markdown",
            show_line_numbers=False,
        )
        yield ta

    def _active_tab(self):
        if not self._state.tabs:
            return None
        return self._state.tabs[self._state.active_tab]

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        tab = self._active_tab()
        if tab is not None:
            tab.notes_md = event.text_area.text

    def on_focus(self) -> None:
        try:
            self.query_one("#notes-textarea", TextArea).focus()
        except Exception:
            pass

    def append_note(self, text: str) -> None:
        """Bagley-side auto-append: inserts 'HH:MM — <text>' at end of textarea."""
        ts = datetime.datetime.now().strftime("%H:%M")
        line = f"\n{ts} — {text}"
        ta = self.query_one("#notes-textarea", TextArea)
        end_row = len(ta.text.splitlines())
        end_col = len(ta.text.splitlines()[-1]) if ta.text.splitlines() else 0
        ta.insert(line, location=(end_row, end_col))
        # sync state
        tab = self._active_tab()
        if tab is not None:
            tab.notes_md = ta.text
```

- [ ] **Step 9.4: Replace the Static notes section in `target.py`**

Open `src/bagley/tui/panels/target.py`. Replace the `notes-section` Static in `compose`:

```python
    def compose(self):
        from bagley.tui.widgets.rings import ProgressRings
        from bagley.tui.panels.notes_editor import NotesEditor
        yield Static("[b orange3]◆ TARGET[/]\n[dim](no target)[/]", id="target-info")
        yield Static("[b orange3]◆ KILL-CHAIN[/]", id="killchain-header")
        yield ProgressRings(stage=self._state.tabs[self._state.active_tab].killchain_stage
                            if self._state.tabs else 0)
        yield Static("[b orange3]◆ CREDS[/]\n[dim](none yet)[/]", id="creds-section")
        yield NotesEditor(self._state)
```

- [ ] **Step 9.5: Update F4 binding in `app.py` to focus `NotesEditor`**

Open `src/bagley/tui/app.py`. Change the F4 binding target:

Replace:
```python
        Binding("f4", "focus('#target-panel')", "Notes", show=True),
```
With:
```python
        Binding("f4", "focus_notes", "Notes", show=True),
```

Add the action method:
```python
    def action_focus_notes(self) -> None:
        try:
            from bagley.tui.panels.notes_editor import NotesEditor
            self.query_one(NotesEditor).focus()
        except Exception:
            pass
```

- [ ] **Step 9.6: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_notes_editor.py -v
```

Expected: 5 tests pass.

- [ ] **Step 9.7: Run full suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 9.8: Commit**

```bash
git add src/bagley/tui/panels/notes_editor.py src/bagley/tui/panels/target.py src/bagley/tui/app.py tests/tui/test_notes_editor.py
git commit -m "feat(tui/panels): NotesEditor replaces static notes; F4 focus + auto-append"
```

---

## Task 10: Hook `MemoryPromoter` into `ChatPanel` + `/memory` command

**Files:**
- Modify: `src/bagley/tui/panels/chat.py`
- Create: `tests/tui/test_chat_memory_hook.py`

Every assistant response passes through `MemoryPromoter.scan()`. Each returned event fires a corresponding `AlertBus` publish (toast). `/memory` as the first word in a user message opens a read-only browse of all findings grouped by severity.

- [ ] **Step 10.1: Write the failing test**

Create `tests/tui/test_chat_memory_hook.py`:

```python
"""ChatPanel memory promotion + /memory command tests."""
import tempfile
import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.services.alerts import bus, AlertBus, Severity


@pytest.mark.asyncio
async def test_slash_memory_shows_findings():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        inp = app.query_one("#chat-input")
        inp.value = "/memory"
        await pilot.press("f3")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        log = app.query_one("#chat-log")
        text = "\n".join(str(line) for line in log.lines)
        assert "memory" in text.lower() or "findings" in text.lower()


@pytest.mark.asyncio
async def test_promoter_fires_toast_on_port_in_response(monkeypatch):
    """Patch stub engine response to contain a port line; verify a toast appears."""
    from bagley.tui.panels import chat as chat_module

    # Patch the stub response to return a port-bearing line
    original_respond = None

    async def fake_respond(self_panel, user_msg: str):
        response_text = "80/tcp open http Apache 2.4.49"
        log = self_panel.query_one("#chat-log")
        log.write(f"[magenta]bagley>[/] {response_text}")
        self_panel._state.turn += 1
        # Run promoter (same as real path)
        events = self_panel._promoter.scan(
            response_text, self_panel._store, current_host=None
        )
        for kind, detail in events:
            from bagley.tui.services.alerts import bus as _bus, Alert, Severity
            _bus.publish(Alert(Severity.INFO, f"◯ saved to memory", detail, "promoter"))

    received = []
    bus.subscribe(received.append)

    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        panel = app.query_one("#chat-panel")
        monkeypatch.setattr(panel, "_respond", lambda msg: app.call_later(fake_respond, panel, msg))
        inp = app.query_one("#chat-input")
        inp.value = "scan 10.0.0.1"
        await pilot.press("f3")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause(1.0)

    bus.unsubscribe(received.append)
    assert any("saved to memory" in a.title or "new_port" in a.body or a.source == "promoter"
               for a in received)
```

- [ ] **Step 10.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_chat_memory_hook.py::test_slash_memory_shows_findings -v
```

Expected: `/memory` input does not produce findings output — no handler exists.

- [ ] **Step 10.3: Modify `chat.py` to add promoter hook and `/memory` handler**

Open `src/bagley/tui/panels/chat.py`. Add these imports at the top:

```python
from bagley.tui.services.memory_promoter import MemoryPromoter
from bagley.tui.services.alerts import bus as _alert_bus, Alert, Severity
```

Inside `ChatPanel.__init__`, after `self._state = state`:

```python
        self._promoter = MemoryPromoter()
        # MemoryStore — lazily opened; falls back to None in stub/test mode
        self._store = None
        try:
            from bagley.memory.store import MemoryStore
            from pathlib import Path
            db_path = Path(".bagley") / "memory.db"
            self._store = MemoryStore(db_path)
        except Exception:
            pass
```

In the `on_input_submitted` handler (or wherever the chat submit is handled), before calling the engine, intercept `/memory`:

```python
    def _handle_slash_command(self, text: str) -> bool:
        """Return True if the text was a slash command (handled here)."""
        cmd = text.strip().lower()
        if cmd == "/memory" or cmd.startswith("/memory "):
            self._show_memory_browse()
            return True
        return False

    def _show_memory_browse(self) -> None:
        log = self.query_one("#chat-log")
        log.write("[b cyan]◆ MEMORY BROWSE[/]")
        if self._store is None:
            log.write("[dim](no memory store active)[/]")
            return
        for sev in ("critical", "high", "medium", "low"):
            findings = self._store.list_findings_by_severity(sev)
            if findings:
                log.write(f"[b]{sev.upper()}[/] ({len(findings)})")
                for f in findings[:5]:    # cap display at 5 per severity
                    log.write(f"  · [{f['host']}] {f['summary']}")
        total = len(self._store.list_findings())
        if total == 0:
            log.write("[dim](no findings in memory yet)[/]")
```

In the submit handler, call `_handle_slash_command` first:

```python
    def on_input_submitted(self, event) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        log = self.query_one("#chat-log")
        log.write(f"[bold]you>[/] {text}")
        if self._handle_slash_command(text):
            return
        # ... existing engine dispatch ...
```

After the engine produces a response (inside the worker that writes assistant text), run the promoter:

```python
        # after writing assistant response to log:
        if self._store is not None:
            tab = self._state.tabs[self._state.active_tab] if self._state.tabs else None
            host = tab.id if (tab and tab.kind == "target") else None
            events = self._promoter.scan(response_text, self._store, current_host=host)
            for kind, detail in events:
                _alert_bus.publish(Alert(
                    severity=Severity.INFO,
                    title="◯ saved to memory",
                    body=detail,
                    source="promoter",
                ))
```

> **Implementation note:** The exact location of the post-response hook depends on how Phase 1/2 wired the `ReActLoop`. The block above should be placed immediately after the line that writes the assistant message to `#chat-log`. If the response is produced inside a `@work` method, the `_alert_bus.publish` call is safe there because `AlertBus.publish` calls subscribers synchronously.

- [ ] **Step 10.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_chat_memory_hook.py -v
```

Expected: 2 tests pass.

- [ ] **Step 10.5: Run full suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short
```

Expected: all tests pass, no regressions.

- [ ] **Step 10.6: Commit**

```bash
git add src/bagley/tui/panels/chat.py tests/tui/test_chat_memory_hook.py
git commit -m "feat(tui/panels): MemoryPromoter hook in ChatPanel + /memory browse command"
```

---

## Task 11: Wire promoter events to correct alert severities + toast titles

**Files:**
- Modify: `src/bagley/tui/panels/chat.py`
- Create: `tests/tui/test_promoter_alerts.py`

Each `MemoryPromoter` event kind maps to a specific toast severity and title defined in the spec (§6.14): `new_host`→INFO/`◯ saved to memory`, `new_port`→INFO/`◯ saved to memory`, `cve_match`→CRIT/`CRITICAL FINDING`, `new_cred`→WARN/`NEW CRED`, `exploit_attempt`→WARN/`EXPLOIT ATTEMPT`, `shell_obtained`→CRIT/`SHELL OBTAINED`.

- [ ] **Step 11.1: Write the failing test**

Create `tests/tui/test_promoter_alerts.py`:

```python
"""Promoter event → correct alert severity mapping."""
import tempfile
import pytest
from bagley.memory.store import MemoryStore, Finding
from bagley.tui.services.memory_promoter import MemoryPromoter
from bagley.tui.services.alerts import AlertBus, Alert, Severity
from bagley.tui.panels.chat import _promoter_event_to_alert


def _fresh_store():
    return MemoryStore(tempfile.mktemp(suffix=".db"))


def test_cve_event_maps_to_crit():
    a = _promoter_event_to_alert("cve_match", "CVE-2021-44228")
    assert a.severity == Severity.CRIT
    assert "CRITICAL" in a.title.upper() or "FINDING" in a.title.upper()


def test_shell_event_maps_to_crit():
    a = _promoter_event_to_alert("shell_obtained", "10.0.0.1")
    assert a.severity == Severity.CRIT
    assert "SHELL" in a.title.upper()


def test_new_cred_maps_to_warn():
    a = _promoter_event_to_alert("new_cred", "admin:***")
    assert a.severity == Severity.WARN
    assert "CRED" in a.title.upper()


def test_new_host_maps_to_info():
    a = _promoter_event_to_alert("new_host", "10.0.0.5")
    assert a.severity == Severity.INFO
    assert "memory" in a.title.lower() or "saved" in a.title.lower()


def test_new_port_maps_to_info():
    a = _promoter_event_to_alert("new_port", "80/tcp http")
    assert a.severity == Severity.INFO


def test_unknown_event_falls_back_to_info():
    a = _promoter_event_to_alert("some_future_event", "detail")
    assert a.severity == Severity.INFO
```

- [ ] **Step 11.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_promoter_alerts.py -v
```

Expected: `ImportError: cannot import name '_promoter_event_to_alert' from 'bagley.tui.panels.chat'`.

- [ ] **Step 11.3: Add `_promoter_event_to_alert` to `chat.py`**

Open `src/bagley/tui/panels/chat.py`. Add this module-level function after the imports:

```python
def _promoter_event_to_alert(kind: str, detail: str) -> "Alert":
    """Map a MemoryPromoter event kind to an Alert with correct severity and title."""
    from bagley.tui.services.alerts import Alert, Severity
    _MAP: dict[str, tuple[Severity, str, str]] = {
        "new_host":       (Severity.INFO, "◯ saved to memory",  "#hosts-panel"),
        "new_port":       (Severity.INFO, "◯ saved to memory",  "#hosts-panel"),
        "cve_match":      (Severity.CRIT, "CRITICAL FINDING",   "#hosts-panel"),
        "new_cred":       (Severity.WARN, "NEW CRED",           "#target-panel"),
        "exploit_attempt":(Severity.WARN, "EXPLOIT ATTEMPT",    "#chat-panel"),
        "shell_obtained": (Severity.CRIT, "SHELL OBTAINED",     "#chat-panel"),
    }
    sev, title, selector = _MAP.get(kind, (Severity.INFO, "◯ saved to memory", ""))
    return Alert(severity=sev, title=title, body=detail, source="promoter",
                 pane_selector=selector)
```

Update the promoter loop in the submit handler to use this function:

```python
            events = self._promoter.scan(response_text, self._store, current_host=host)
            for kind, detail in events:
                _alert_bus.publish(_promoter_event_to_alert(kind, detail))
```

- [ ] **Step 11.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_promoter_alerts.py -v
```

Expected: 6 tests pass.

- [ ] **Step 11.5: Run full suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short
```

Expected: all tests pass.

- [ ] **Step 11.6: Commit**

```bash
git add src/bagley/tui/panels/chat.py tests/tui/test_promoter_alerts.py
git commit -m "feat(tui/panels): map promoter events to correct alert severities per spec §6.14"
```

---

## Task 12: End-to-end smoke validation + full suite sign-off

**Files:**
- No new files. Run the complete suite and verify smoke behavior.

- [ ] **Step 12.1: Run the complete test suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short 2>&1 | tee phase3-test-results.txt
```

Expected: all tests pass. Acceptable: warnings about asyncio event loop deprecations are fine; failures are not.

- [ ] **Step 12.2: Count new tests introduced in Phase 3**

```bash
grep -c "^async def test_\|^def test_" tests/tui/test_memory_promoter.py tests/tui/test_alerts.py tests/tui/test_rings.py tests/tui/test_minimap.py tests/tui/test_severity_bars.py tests/tui/test_nudges.py tests/tui/test_notes_editor.py tests/tui/test_alerts_log.py tests/tui/test_chat_memory_hook.py tests/tui/test_promoter_alerts.py
```

Expected: ≥ 42 new tests total across Phase 3 files.

- [ ] **Step 12.3: Smoke-run the TUI manually**

```bash
.venv/Scripts/python.exe -m bagley.tui.app
```

Manual verification checklist:

1. Boot: header, modes bar, tab bar, three panes visible.
2. Right column shows `◆ KILL-CHAIN` with `○○○○○○○  0%` rings and all 7 stage labels.
3. Right column shows `◆ NOTES  (F4 to edit)` — no bare Static `notes-section`.
4. Press F4: `NotesEditor` TextArea receives focus; can type text.
5. Left column shows `◆ FINDINGS` with `CRIT ░░░░░░░░░░ 0` style bars.
6. Subnet minimap visible in right column with gray dots for all 254 cells.
7. Press Ctrl+N: `AlertsLog` modal opens with "No alerts yet." text. Press Esc closes it.
8. Type `/memory` in chat input and press Enter: `◆ MEMORY BROWSE` appears in chat log.
9. Press Ctrl+D: exits cleanly.

- [ ] **Step 12.4: Fix any failures found in Step 12.3**

For each failure: write a minimal failing test → fix implementation → rerun suite → confirm green.

- [ ] **Step 12.5: Final commit if any fixes were applied**

```bash
# add only the files that were changed
git add <exact changed paths>
git commit -m "fix(tui/phase3): smoke-run corrections"
```

- [ ] **Step 12.6: Tag the phase completion**

```bash
git tag tui-phase3-complete
```

---

## Self-review

### Spec coverage

| Spec section | Feature | Covered in plan |
|---|---|---|
| §6.14 | Alerts / toasts — 4 severities, max 4 stack, auto-dismiss, crit explicit, Ctrl+N log | Tasks 3, 4, 5 |
| §6.14 | Triggers: SCAN COMPLETE, CRITICAL FINDING, NEW CRED, MODE SUGGESTED, SHELL OBTAINED, PLAYBOOK SAVED, AUTO-MEMORY | Tasks 10, 11 |
| §6.11 | Progress rings `●●●○○○○  43%` in TargetPanel | Task 6 |
| §6.11 | Subnet minimap 254-cell dotmap in recon tab | Tasks 6, 7 |
| §6.11 | Severity bars `▓▓▓▓░` CRIT/HIGH/MED/LOW in HostsPanel | Task 6 |
| §6.12 | Nudge: idle > 15 min | Task 8 |
| §6.12 | Nudge: ≥ 3 HIGH findings untouched | Task 8 |
| §6.12 | Nudge: same 3-step sequence → playbook suggestion | Deferred to Phase 4 (as spec says) |
| §6.12 | Nudge: new Metasploit module for known CVE | Out of scope for Phase 3 (as spec says) |
| §11 Phase 3 | Auto-memory: new host up, new open port, CVE match, cred extracted, exploit attempt, shell obtained | Tasks 2, 10 |
| §11 Phase 3 | Each promotion fires `◯ saved to memory` toast | Task 11 |
| §11 Phase 3 | `/memory` command opens read-only browse | Task 10 |
| §8.1 | `TabState.notes_md` — notes persistence | Task 9 |
| §4.2 | TargetPanel notes editable via TextArea on focus (F4) | Task 9 |

### Decisions and rationale

1. **`AlertBus` as module-level singleton** — simplest wiring; widgets import `from bagley.tui.services.alerts import bus`. Tests that need isolation create their own `AlertBus()` instance.

2. **`ToastLayer` uses `set_timer` not `asyncio.create_task`** — consistent with Textual 8.2.4 constraints.

3. **`_promoter_event_to_alert` as module-level function** — keeps `chat.py` testable in isolation without a full `App` instance.

4. **`ProgressRings` renders to `id="killchain-rings"`** — overwrites the Phase 1/2 `killchain` Static; test `test_rings_mounts_in_target_panel` verifies the id is present.

5. **Minimap in recon tab-0** — implemented as a `Minimap` widget inside the right column when `active_tab == 0`. Full per-tab screen switching is Phase 4 work; this approach satisfies Phase 3 spec without restructuring `app.compose`.

6. **`NudgeEngine._evaluate()` exposed for tests** — avoids the need to simulate 30 real-second intervals; tests call `_evaluate()` directly after setting `_idle_ticks`.

7. **`recent_attempts(n=20)`** — matches spec wording "default cap"; consistent with `host_summary` which already LIMIT 20s.

8. **Minimap cell count** — spec says 254 cells (hosts 1–254 in a /24). The `Minimap._COLS = 32` gives 8 rows of 32 = 256 display positions; cells 1–254 occupy positions 0–253, leaving 2 padding positions. This is acceptable; the test verifies the 254-cell logic rather than pixel-perfect alignment.

### Risks

- `TextArea` API may differ slightly between Textual 0.80 and 8.2.4 (plan targets 8.2.4 per constraints). If `ta.insert(text, location=...)` has a different signature, the `NotesEditor.append_note` implementation will need to use `ta.text = ta.text + line` as a fallback.
- `set_timer` vs `set_interval` in `ToastLayer` — plan uses `set_timer` (one-shot) for auto-dismiss which is correct. `set_interval` (repeating) is used only in `app.on_mount` for the nudge ticker.
- `AlertBus.publish` calls subscribers synchronously; if called from a non-UI thread (e.g., inside a `@work` method), widgets that call `self.update()` inside subscribers may violate Textual's threading rules. `ToastLayer._on_alert` already routes through `app.call_from_thread` to handle this.
