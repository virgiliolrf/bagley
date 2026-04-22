# Bagley TUI — Phase 4 (Plan Mode + Playbooks + Bang + @ Mentions + Smart Paste) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the five "superpowers" interaction layer on top of the Phase 1-3 TUI skeleton: (1) Alt+P plan mode — Bagley generates a structured `Plan` with `Step` objects, rendered as a full-screen-ish overlay where the user navigates, approves, edits, and skips; (2) `.playbooks/*.yml` loader and runner that feeds steps through plan mode; (3) bang re-exec (`!!`, `!N`, `!prefix`) that expands history shortcuts before the message reaches the model; (4) `@` mention popup with fuzzy filtering and inline token substitution; (5) smart-paste classifier chain (nmap → parse ports → memory; hash list → creds; CVE ID → inspector; URL → hint; IP list → scope after confirm). Ship with full TDD: every feature has a failing test written before its implementation.

**Prerequisites:** Phase 1 (`BagleyApp`, `AppState/TabState`, `ChatPanel`, `palette.py`) and Phase 3 (auto-memory, `memory/store.py` write path) must be complete. Textual 0.80+ and PyYAML must be installed.

**Tech Stack:** Python 3.11, Textual 0.80+ (`push_screen(callback=...)` not `push_screen_wait` outside workers — see constraint below), PyYAML 6.0+, pytest + pytest-asyncio (Pilot harness), existing `ReActLoop`/`LocalEngine`/`OllamaEngine` backbone.

**Critical Textual constraint:** `push_screen_wait` is only safe inside a `worker`. Outside workers use `push_screen(callback=...)` with a result-callback. Every plan/overlay interaction follows this pattern.

---

## File structure

### Files to create

- `src/bagley/tui/plan_mode/__init__.py` — empty marker
- `src/bagley/tui/plan_mode/plan.py` — `Step` and `Plan` dataclasses
- `src/bagley/tui/plan_mode/generator.py` — prompts Bagley via `ReActLoop` with a special system suffix to produce a `Plan`
- `src/bagley/tui/plan_mode/overlay.py` — full-screen-ish `PlanOverlay` Textual `Container` widget
- `src/bagley/tui/plan_mode/persistence.py` — YAML save/load for `.bagley/plans/<tab>-<ts>.yml`
- `src/bagley/tui/playbooks/__init__.py` — empty marker
- `src/bagley/tui/playbooks/loader.py` — scan `.playbooks/`, parse and validate YAML, return `list[Playbook]`
- `src/bagley/tui/playbooks/runner.py` — execute playbook steps through plan mode, evaluate `if` conditions
- `src/bagley/tui/interactions/bang.py` — `BangExpander`: `!!`, `!N`, `!prefix` expansion from `TabState.cmd_history`
- `src/bagley/tui/interactions/mentions.py` — `MentionPopup` widget + `MentionSubstitutor`
- `src/bagley/tui/interactions/smart_paste.py` — `SmartPasteDispatcher` + individual classifier functions
- `src/bagley/tui/parsers/__init__.py` — empty marker
- `src/bagley/tui/parsers/nmap.py` — minimal nmap `-sV` text output → `list[Host]`
- `src/bagley/tui/parsers/shodan.py` — Shodan JSON → `list[Host]`
- `src/bagley/tui/parsers/hashes.py` — hash type detection via length + charset
- `tests/tui/test_plan_generator.py` — generator produces `Plan` from a goal string (stubbed engine)
- `tests/tui/test_plan_overlay.py` — Alt+P opens overlay, ↑↓ nav, Enter advances, Esc closes
- `tests/tui/test_plan_persistence.py` — save/load YAML roundtrip
- `tests/tui/test_playbook_loader.py` — parse minimal playbook YAML, validate schema
- `tests/tui/test_playbook_runner.py` — runner executes steps via plan mode, handles `if` conditions
- `tests/tui/test_bang_expansion.py` — `!!`, `!2`, `!ping` each resolve correctly
- `tests/tui/test_mentions_popup.py` — `@` opens popup, Tab confirms, token substituted on submit
- `tests/tui/test_smart_paste_nmap.py` — nmap output parse + memory promote
- `tests/tui/test_smart_paste_hash.py` — MD5/SHA1/SHA256 detected correctly
- `tests/tui/test_smart_paste_ip_list.py` — IP list → scope after confirm
- `tests/tui/test_smart_paste_cve_url.py` — CVE and URL dispatch

### Files to modify

- `pyproject.toml` — add `pyyaml>=6.0` to `[project.dependencies]`
- `src/bagley/tui/app.py` — bind Alt+P to `action_toggle_plan`, bind Ctrl+Shift+V to `action_smart_paste`
- `src/bagley/tui/panels/chat.py` — call `BangExpander` + `MentionSubstitutor` in `on_input_submitted`; forward paste events to `SmartPasteDispatcher`
- `src/bagley/tui/widgets/palette.py` — add "Run playbook …" action group; wire to `PlaybookRunner`

### Files NOT touched in Phase 4

`src/bagley/agent/cli.py`, `src/bagley/agent/loop.py`, `src/bagley/agent/executor.py`, `src/bagley/inference/`, `src/bagley/memory/store.py` (read-only from Phase 4 parsers). Phase 5 features (ShellPane, PTY, `/observe`, graph view, timeline scrubber) are out of scope.

---

## Task 1: Add PyYAML dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1.1: Add PyYAML to project dependencies**

Open `pyproject.toml`. In the `[project].dependencies` list, append:

```toml
    "pyyaml>=6.0",
```

- [ ] **Step 1.2: Install in the existing venv**

```bash
.venv/Scripts/python.exe -m pip install "pyyaml>=6.0"
```

Verify:

```bash
.venv/Scripts/python.exe -c "import yaml; print(yaml.__version__)"
```

Expected: a version string `6.x.x`.

- [ ] **Step 1.3: Create parser package markers**

Create `src/bagley/tui/parsers/__init__.py`:

```python
"""Bagley TUI — paste/import parsers."""
```

Create `src/bagley/tui/plan_mode/__init__.py`:

```python
"""Bagley TUI — plan mode package."""
```

Create `src/bagley/tui/playbooks/__init__.py`:

```python
"""Bagley TUI — playbooks package."""
```

- [ ] **Step 1.4: Commit**

```bash
git add pyproject.toml src/bagley/tui/parsers/__init__.py src/bagley/tui/plan_mode/__init__.py src/bagley/tui/playbooks/__init__.py
git commit -m "deps(tui-p4): add pyyaml>=6.0, scaffold plan_mode/playbooks/parsers packages"
```

---

## Task 2: `Plan` and `Step` dataclasses

**Files:**
- Create: `src/bagley/tui/plan_mode/plan.py`
- Create: `tests/tui/test_plan_generator.py` (partial — dataclass assertions only for now)

- [ ] **Step 2.1: Write the failing test**

Create `tests/tui/test_plan_generator.py`:

```python
"""Tests for plan dataclasses and generator."""

from bagley.tui.plan_mode.plan import Plan, Step, StepStatus


def test_step_defaults():
    s = Step(kind="run", cmd="nmap -sV 10.10.14.1", description="Port scan target")
    assert s.status == StepStatus.PENDING
    assert s.kind == "run"
    assert s.cmd == "nmap -sV 10.10.14.1"
    assert s.description == "Port scan target"


def test_plan_empty():
    p = Plan(goal="recon 10.10.14.1", steps=[])
    assert p.goal == "recon 10.10.14.1"
    assert p.steps == []
    assert p.current_index == 0


def test_plan_current_step():
    steps = [
        Step(kind="run", cmd="nmap -sV 10.10.14.1", description="Scan"),
        Step(kind="run", cmd="gobuster ...", description="Dir bust"),
    ]
    p = Plan(goal="test", steps=steps)
    assert p.current_step() is steps[0]


def test_plan_advance():
    steps = [
        Step(kind="run", cmd="cmd1", description="d1"),
        Step(kind="run", cmd="cmd2", description="d2"),
    ]
    p = Plan(goal="test", steps=steps)
    p.advance()
    assert p.current_index == 1
    assert steps[0].status == StepStatus.DONE


def test_plan_skip():
    steps = [
        Step(kind="run", cmd="cmd1", description="d1"),
        Step(kind="run", cmd="cmd2", description="d2"),
    ]
    p = Plan(goal="test", steps=steps)
    p.skip()
    assert p.current_index == 1
    assert steps[0].status == StepStatus.SKIPPED


def test_plan_is_done_when_all_advanced():
    steps = [Step(kind="run", cmd="c", description="d")]
    p = Plan(goal="test", steps=steps)
    assert not p.is_done()
    p.advance()
    assert p.is_done()
```

- [ ] **Step 2.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_generator.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.plan_mode.plan'`.

- [ ] **Step 2.3: Implement `plan.py`**

Create `src/bagley/tui/plan_mode/plan.py`:

```python
"""Plan and Step dataclasses for plan mode."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class Step:
    kind: str                           # "run" | "prompt" | "if"
    cmd: str                            # shell command or prompt text
    description: str
    status: StepStatus = StepStatus.PENDING
    condition: Optional[str] = None     # raw condition string for "if" steps
    output: Optional[str] = None        # captured stdout after execution


@dataclass
class Plan:
    goal: str
    steps: list[Step]
    current_index: int = 0
    tab_id: str = "recon"
    timestamp: str = ""                 # ISO-8601, filled on persist

    def current_step(self) -> Optional[Step]:
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def advance(self) -> None:
        """Mark current step DONE and move to next."""
        if self.current_index < len(self.steps):
            self.steps[self.current_index].status = StepStatus.DONE
            self.current_index += 1

    def skip(self) -> None:
        """Mark current step SKIPPED and move to next."""
        if self.current_index < len(self.steps):
            self.steps[self.current_index].status = StepStatus.SKIPPED
            self.current_index += 1

    def is_done(self) -> bool:
        return self.current_index >= len(self.steps)

    def status_icon(self, index: int) -> str:
        """Return ▶ / ✓ / · / ✗ / ↷ for a step by index."""
        if index == self.current_index:
            return "▶"
        step = self.steps[index]
        return {
            StepStatus.DONE: "✓",
            StepStatus.SKIPPED: "↷",
            StepStatus.FAILED: "✗",
            StepStatus.PENDING: "·",
            StepStatus.RUNNING: "▶",
        }.get(step.status, "·")
```

- [ ] **Step 2.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_generator.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 2.5: Commit**

```bash
git add src/bagley/tui/plan_mode/plan.py tests/tui/test_plan_generator.py
git commit -m "feat(tui-p4): Plan/Step/StepStatus dataclasses with advance/skip/is_done"
```

---

## Task 3: Plan persistence (YAML save/load)

**Files:**
- Create: `src/bagley/tui/plan_mode/persistence.py`
- Create: `tests/tui/test_plan_persistence.py`

- [ ] **Step 3.1: Write the failing test**

Create `tests/tui/test_plan_persistence.py`:

```python
"""Tests for plan YAML persistence."""

import os
import tempfile
from pathlib import Path

from bagley.tui.plan_mode.plan import Plan, Step, StepStatus
from bagley.tui.plan_mode.persistence import save_plan, load_plan, plan_dir


def _make_plan() -> Plan:
    steps = [
        Step(kind="run", cmd="nmap -sV 10.0.0.1", description="Port scan"),
        Step(kind="prompt", cmd="summarize", description="Ask Bagley to summarize"),
    ]
    return Plan(goal="recon 10.0.0.1", steps=steps, tab_id="10.0.0.1")


def test_save_creates_file(tmp_path):
    p = _make_plan()
    saved = save_plan(p, base_dir=tmp_path)
    assert saved.exists()
    assert saved.suffix == ".yml"
    assert "10.0.0.1" in saved.name


def test_roundtrip(tmp_path):
    original = _make_plan()
    saved = save_plan(original, base_dir=tmp_path)
    restored = load_plan(saved)
    assert restored.goal == original.goal
    assert len(restored.steps) == len(original.steps)
    assert restored.steps[0].cmd == "nmap -sV 10.0.0.1"
    assert restored.steps[0].kind == "run"
    assert restored.steps[1].kind == "prompt"


def test_roundtrip_preserves_status(tmp_path):
    p = _make_plan()
    p.steps[0].status = StepStatus.DONE
    p.steps[1].status = StepStatus.SKIPPED
    saved = save_plan(p, base_dir=tmp_path)
    restored = load_plan(saved)
    assert restored.steps[0].status == StepStatus.DONE
    assert restored.steps[1].status == StepStatus.SKIPPED


def test_plan_dir_default():
    d = plan_dir()
    assert d.name == "plans"
    assert ".bagley" in str(d)
```

- [ ] **Step 3.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_persistence.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3.3: Implement `persistence.py`**

Create `src/bagley/tui/plan_mode/persistence.py`:

```python
"""Save and load Plan objects to/from .bagley/plans/*.yml."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from bagley.tui.plan_mode.plan import Plan, Step, StepStatus


def plan_dir(base: Optional[Path] = None) -> Path:
    """Return the default plans directory (.bagley/plans/)."""
    root = base or Path.cwd() / ".bagley"
    d = root / "plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_plan(plan: Plan, base_dir: Optional[Path] = None) -> Path:
    """Serialize *plan* to YAML and write to base_dir.

    File is named ``<tab_id>-<iso_ts>.yml`` with colons replaced so it
    is safe on Windows.
    """
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
    plan.timestamp = ts
    safe_tab = plan.tab_id.replace("/", "_").replace(":", "_")
    filename = f"{safe_tab}-{ts}.yml"

    dest = (base_dir or plan_dir()) / filename

    data = {
        "goal": plan.goal,
        "tab_id": plan.tab_id,
        "timestamp": plan.timestamp,
        "current_index": plan.current_index,
        "steps": [
            {
                "kind": s.kind,
                "cmd": s.cmd,
                "description": s.description,
                "status": s.status.value,
                "condition": s.condition,
                "output": s.output,
            }
            for s in plan.steps
        ],
    }

    dest.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return dest


def load_plan(path: Path) -> Plan:
    """Deserialize a YAML plan file back into a *Plan* object."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = [
        Step(
            kind=s["kind"],
            cmd=s["cmd"],
            description=s["description"],
            status=StepStatus(s.get("status", "pending")),
            condition=s.get("condition"),
            output=s.get("output"),
        )
        for s in data.get("steps", [])
    ]
    return Plan(
        goal=data["goal"],
        steps=steps,
        tab_id=data.get("tab_id", "unknown"),
        current_index=data.get("current_index", 0),
        timestamp=data.get("timestamp", ""),
    )
```

- [ ] **Step 3.4: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_persistence.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add src/bagley/tui/plan_mode/persistence.py tests/tui/test_plan_persistence.py
git commit -m "feat(tui-p4): plan YAML persistence — save_plan/load_plan roundtrip"
```

---

## Task 4: Plan generator

**Files:**
- Create: `src/bagley/tui/plan_mode/generator.py`
- Extend: `tests/tui/test_plan_generator.py` (append generator tests)

- [ ] **Step 4.1: Append generator tests to the existing file**

Open `tests/tui/test_plan_generator.py` and append:

```python
# ── Generator tests ─────────────────────────────────────────────────────────

from bagley.tui.plan_mode.generator import PlanGenerator, PLAN_SYSTEM_SUFFIX


class _StubEngine:
    """Returns a hard-coded JSON plan string regardless of input."""

    PLAN_JSON = """
    {
      "goal": "recon 10.0.0.1",
      "steps": [
        {"kind": "run", "cmd": "nmap -sV 10.0.0.1", "description": "Port scan"},
        {"kind": "prompt", "cmd": "summarize attack surface", "description": "Ask Bagley"}
      ]
    }
    """

    def generate(self, messages, system="", **kwargs):
        return self.PLAN_JSON


def test_generator_produces_plan():
    gen = PlanGenerator(engine=_StubEngine())
    plan = gen.generate(goal="recon 10.0.0.1", tab_id="10.0.0.1")
    assert isinstance(plan, Plan)
    assert plan.goal == "recon 10.0.0.1"
    assert len(plan.steps) == 2
    assert plan.steps[0].kind == "run"
    assert plan.steps[1].kind == "prompt"
    assert plan.tab_id == "10.0.0.1"


def test_generator_system_suffix_present():
    assert "JSON" in PLAN_SYSTEM_SUFFIX
    assert "steps" in PLAN_SYSTEM_SUFFIX


def test_generator_bad_json_raises():
    class _BadEngine:
        def generate(self, messages, system="", **kwargs):
            return "NOT JSON AT ALL }{{"

    gen = PlanGenerator(engine=_BadEngine())
    import pytest as _pytest
    with _pytest.raises(ValueError, match="parse"):
        gen.generate(goal="anything", tab_id="tab0")
```

- [ ] **Step 4.2: Run the new tests — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_generator.py -v -k "generator"
```

Expected: `ModuleNotFoundError` for `generator`.

- [ ] **Step 4.3: Implement `generator.py`**

Create `src/bagley/tui/plan_mode/generator.py`:

```python
"""Generate a Plan by prompting Bagley with a structured system suffix."""

from __future__ import annotations

import json
import re
from typing import Any

from bagley.tui.plan_mode.plan import Plan, Step

PLAN_SYSTEM_SUFFIX = """
You are in PLAN MODE. Your entire response MUST be a single valid JSON object and
nothing else — no prose before or after. Schema:

{
  "goal": "<the goal restated>",
  "steps": [
    {"kind": "run",    "cmd": "<shell command>",  "description": "<one sentence>"},
    {"kind": "prompt", "cmd": "<question/task>",  "description": "<one sentence>"},
    {"kind": "if",     "cmd": "<shell command>",  "description": "<one sentence>",
     "condition": "<python-evaluable condition using variables: ports, hosts>"}
  ]
}

Only use kinds: run, prompt, if.
Do not add commentary outside the JSON block.
"""


class PlanGenerator:
    """Ask the Bagley engine to generate a Plan for *goal*."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def generate(self, goal: str, tab_id: str = "recon") -> Plan:
        messages = [{"role": "user", "content": f"Generate a plan to: {goal}"}]
        raw = self.engine.generate(messages, system=PLAN_SYSTEM_SUFFIX)

        # Strip markdown fences if model wrapped the JSON
        raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\n?```$", "", raw.strip(), flags=re.MULTILINE)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse plan JSON from model: {exc}") from exc

        steps = [
            Step(
                kind=s["kind"],
                cmd=s["cmd"],
                description=s.get("description", ""),
                condition=s.get("condition"),
            )
            for s in data.get("steps", [])
        ]
        return Plan(goal=data.get("goal", goal), steps=steps, tab_id=tab_id)
```

- [ ] **Step 4.4: Run all generator tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_generator.py -v
```

Expected: all 9 tests pass (6 dataclass + 3 generator).

- [ ] **Step 4.5: Commit**

```bash
git add src/bagley/tui/plan_mode/generator.py tests/tui/test_plan_generator.py
git commit -m "feat(tui-p4): PlanGenerator — structured JSON plan from engine + suffix"
```

---

## Task 5: Plan mode overlay widget

**Files:**
- Create: `src/bagley/tui/plan_mode/overlay.py`
- Create: `tests/tui/test_plan_overlay.py`

- [ ] **Step 5.1: Write the failing overlay tests**

Create `tests/tui/test_plan_overlay.py`:

```python
"""Tests for PlanOverlay widget — navigation, approve, skip, edit, Esc."""

import pytest
from textual.app import App, ComposeResult

from bagley.tui.plan_mode.overlay import PlanOverlay
from bagley.tui.plan_mode.plan import Plan, Step


def _make_plan() -> Plan:
    return Plan(
        goal="recon 10.0.0.1",
        steps=[
            Step(kind="run", cmd="nmap -sV 10.0.0.1", description="Port scan"),
            Step(kind="run", cmd="gobuster dir ...", description="Dir bust"),
            Step(kind="run", cmd="enum4linux-ng ...", description="SMB enum"),
        ],
        tab_id="10.0.0.1",
    )


class _TestApp(App):
    def compose(self) -> ComposeResult:
        yield PlanOverlay(_make_plan(), id="overlay")


@pytest.mark.asyncio
async def test_overlay_renders_steps():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        text = overlay.render_steps_text()
        assert "▶" in text
        assert "Port scan" in text
        assert "·" in text


@pytest.mark.asyncio
async def test_overlay_enter_advances():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        await pilot.press("enter")
        await pilot.pause()
        assert overlay.plan.current_index == 1


@pytest.mark.asyncio
async def test_overlay_skip_advances_without_run():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        await pilot.press("s")
        await pilot.pause()
        from bagley.tui.plan_mode.plan import StepStatus
        assert overlay.plan.steps[0].status == StepStatus.SKIPPED
        assert overlay.plan.current_index == 1


@pytest.mark.asyncio
async def test_overlay_approve_all():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        await pilot.press("A")
        await pilot.pause()
        assert overlay.plan.is_done()


@pytest.mark.asyncio
async def test_overlay_esc_posts_message():
    dismissed = []

    class _TrackApp(App):
        def compose(self) -> ComposeResult:
            yield PlanOverlay(_make_plan(), id="overlay")

        def on_plan_overlay_dismissed(self, event) -> None:
            dismissed.append(True)

    app = _TrackApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("escape")
        await pilot.pause()
    assert dismissed


@pytest.mark.asyncio
async def test_overlay_up_down_navigation():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        # Cursor starts at 0; pressing down moves to 1
        await pilot.press("down")
        await pilot.pause()
        assert overlay.cursor == 1
        await pilot.press("up")
        await pilot.pause()
        assert overlay.cursor == 0
```

- [ ] **Step 5.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_overlay.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 5.3: Implement `overlay.py`**

Create `src/bagley/tui/plan_mode/overlay.py`:

```python
"""PlanOverlay — full-screen-ish Textual widget for plan mode."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

from bagley.tui.plan_mode.plan import Plan, StepStatus


class PlanOverlay(Container):
    """Displays and drives user interaction with a Plan.

    Keyboard:
      ↑↓        — move cursor
      Enter     — approve + run current step (posts ApproveStep)
      s         — skip current step
      e         — edit command (posts EditStep)
      A         — approve all remaining steps
      Esc       — dismiss (posts Dismissed)
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
        Binding("enter", "approve", "Approve"),
        Binding("s", "skip", "Skip"),
        Binding("e", "edit", "Edit"),
        Binding("A", "approve_all", "Approve All"),
        Binding("escape", "dismiss_overlay", "Exit"),
    ]

    DEFAULT_CSS = """
    PlanOverlay {
        layer: overlay;
        background: $surface;
        border: heavy $primary;
        padding: 1 2;
        width: 80%;
        height: auto;
        max-height: 80%;
        align: center middle;
    }
    PlanOverlay .plan-title { color: $primary; text-style: bold; }
    PlanOverlay .step-current { color: $success; text-style: bold; }
    PlanOverlay .step-done { color: $text-muted; }
    PlanOverlay .step-pending { color: $text; }
    """

    cursor: reactive[int] = reactive(0)

    # ── Messages ──────────────────────────────────────────────────────────────

    class ApproveStep(Message):
        """Emitted when the user presses Enter to run a step."""
        def __init__(self, cmd: str) -> None:
            super().__init__()
            self.cmd = cmd

    class EditStep(Message):
        """Emitted when the user presses 'e' to edit the current step's cmd."""
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    class Dismissed(Message):
        """Emitted when the overlay is closed via Esc."""

    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, plan: Plan, **kwargs) -> None:
        super().__init__(**kwargs)
        self.plan = plan
        self.cursor = plan.current_index

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]Plan:[/] {self.plan.goal}", classes="plan-title")
        yield Label("", id="steps-label")

    def on_mount(self) -> None:
        self._refresh_steps()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render_steps_text(self) -> str:
        lines: list[str] = []
        for i, step in enumerate(self.plan.steps):
            icon = self.plan.status_icon(i)
            marker = "▶" if i == self.cursor else " "
            lines.append(f"  {marker} {icon}  {step.description}  [{step.cmd}]")
        return "\n".join(lines)

    def _refresh_steps(self) -> None:
        try:
            label = self.query_one("#steps-label", Label)
            label.update(self.render_steps_text())
        except Exception:
            pass

    def watch_cursor(self, _: int) -> None:
        self._refresh_steps()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_cursor_up(self) -> None:
        if self.cursor > 0:
            self.cursor -= 1

    def action_cursor_down(self) -> None:
        if self.cursor < len(self.plan.steps) - 1:
            self.cursor += 1

    def action_approve(self) -> None:
        step = self.plan.current_step()
        if step is None:
            return
        self.post_message(self.ApproveStep(cmd=step.cmd))
        self.plan.advance()
        self.cursor = self.plan.current_index
        self._refresh_steps()

    def action_skip(self) -> None:
        self.plan.skip()
        self.cursor = self.plan.current_index
        self._refresh_steps()

    def action_edit(self) -> None:
        self.post_message(self.EditStep(index=self.plan.current_index))

    def action_approve_all(self) -> None:
        while not self.plan.is_done():
            step = self.plan.current_step()
            if step:
                self.post_message(self.ApproveStep(cmd=step.cmd))
            self.plan.advance()
        self.cursor = self.plan.current_index
        self._refresh_steps()

    def action_dismiss_overlay(self) -> None:
        self.post_message(self.Dismissed())
```

- [ ] **Step 5.4: Run the tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_plan_overlay.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5.5: Commit**

```bash
git add src/bagley/tui/plan_mode/overlay.py tests/tui/test_plan_overlay.py
git commit -m "feat(tui-p4): PlanOverlay widget — nav/approve/skip/edit/approve-all/Esc"
```

---

## Task 6: Wire Alt+P into `app.py` and `chat.py`

**Files:**
- Modify: `src/bagley/tui/app.py`
- Modify: `src/bagley/tui/panels/chat.py`

- [ ] **Step 6.1: Add Alt+P binding to `app.py`**

Open `src/bagley/tui/app.py`. In the `BINDINGS` list, append:

```python
Binding("alt+p", "toggle_plan", "Plan mode"),
```

Add the action method to `BagleyApp`:

```python
def action_toggle_plan(self) -> None:
    """Toggle plan mode overlay in the active ChatPanel."""
    try:
        chat = self.query_one("ChatPanel")
        chat.toggle_plan_mode()
    except Exception:
        self.notify("No chat panel active", severity="warning")
```

- [ ] **Step 6.2: Add `toggle_plan_mode` to `ChatPanel`**

Open `src/bagley/tui/panels/chat.py`. Add these imports at the top:

```python
from bagley.tui.plan_mode.generator import PlanGenerator
from bagley.tui.plan_mode.overlay import PlanOverlay
from bagley.tui.plan_mode.persistence import save_plan
```

Add inside the `ChatPanel` class:

```python
_plan_overlay: PlanOverlay | None = None

def toggle_plan_mode(self) -> None:
    """Show plan overlay if hidden; remove it if already shown."""
    if self._plan_overlay is not None:
        self._plan_overlay.remove()
        self._plan_overlay = None
        self.styles.opacity = "1"
        return

    # Use last user message as goal, fallback to generic text
    goal = "recon current target"
    if self.app.state.tabs:
        tab = self.app.state.tabs[self.app.state.active_tab]
        if tab.chat:
            last_user = next(
                (m["content"] for m in reversed(tab.chat) if m["role"] == "user"),
                goal,
            )
            goal = last_user

    # Use stub/real engine from app state
    engine = getattr(self.app, "engine", None)
    if engine is None:
        self.notify("No engine available for plan mode", severity="error")
        return

    gen = PlanGenerator(engine=engine)
    try:
        plan = gen.generate(goal=goal, tab_id=self.app.state.tabs[self.app.state.active_tab].id)
    except ValueError as exc:
        self.notify(str(exc), severity="error")
        return

    overlay = PlanOverlay(plan, id="plan-overlay")
    self._plan_overlay = overlay
    self.styles.opacity = "0.4"
    self.mount(overlay)
    overlay.focus()

def on_plan_overlay_approve_step(self, event: PlanOverlay.ApproveStep) -> None:
    """Run the approved step's command by submitting it to the loop."""
    self._submit_to_loop(event.cmd)

def on_plan_overlay_dismissed(self, event: PlanOverlay.Dismissed) -> None:
    """Save plan and clean up overlay on Esc."""
    if self._plan_overlay is not None:
        try:
            save_plan(self._plan_overlay.plan)
        except Exception:
            pass
        self._plan_overlay.remove()
        self._plan_overlay = None
        self.styles.opacity = "1"
```

- [ ] **Step 6.3: Verify existing boot tests still pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_app_boot.py tests/tui/test_chat_panel.py -v
```

Expected: all existing tests pass unchanged.

- [ ] **Step 6.4: Commit**

```bash
git add src/bagley/tui/app.py src/bagley/tui/panels/chat.py
git commit -m "feat(tui-p4): wire Alt+P plan mode toggle into app + ChatPanel"
```

---

## Task 7: Playbook loader

**Files:**
- Create: `src/bagley/tui/playbooks/loader.py`
- Create: `tests/tui/test_playbook_loader.py`

- [ ] **Step 7.1: Write the failing loader test**

Create `tests/tui/test_playbook_loader.py`:

```python
"""Tests for playbook YAML loader."""

import textwrap
from pathlib import Path

import pytest

from bagley.tui.playbooks.loader import (
    PlaybookStep,
    Playbook,
    load_playbook,
    scan_playbooks,
    PlaybookValidationError,
)


MINIMAL_YAML = textwrap.dedent("""
    name: HTB initial recon
    description: Fast first pass
    target: "{target}"
    steps:
      - run: "nmap -sV {target}"
      - if: "80 in ports"
        run: "gobuster dir -u http://{target} -w common.txt"
      - prompt: "summarize attack surface"
""").strip()


def test_load_minimal_playbook(tmp_path):
    f = tmp_path / "recon.yml"
    f.write_text(MINIMAL_YAML, encoding="utf-8")
    pb = load_playbook(f)
    assert pb.name == "HTB initial recon"
    assert pb.target_template == "{target}"
    assert len(pb.steps) == 3


def test_step_kinds(tmp_path):
    f = tmp_path / "recon.yml"
    f.write_text(MINIMAL_YAML, encoding="utf-8")
    pb = load_playbook(f)
    assert pb.steps[0].kind == "run"
    assert pb.steps[0].run == "nmap -sV {target}"
    assert pb.steps[1].kind == "if"
    assert pb.steps[1].condition == "80 in ports"
    assert pb.steps[2].kind == "prompt"
    assert pb.steps[2].prompt == "summarize attack surface"


def test_missing_name_raises(tmp_path):
    bad = "target: '{target}'\nsteps:\n  - run: 'nmap {target}'"
    f = tmp_path / "bad.yml"
    f.write_text(bad, encoding="utf-8")
    with pytest.raises(PlaybookValidationError, match="name"):
        load_playbook(f)


def test_scan_playbooks(tmp_path):
    (tmp_path / "a.yml").write_text(MINIMAL_YAML, encoding="utf-8")
    (tmp_path / "b.yml").write_text(MINIMAL_YAML.replace("HTB initial recon", "b"), encoding="utf-8")
    pbs = scan_playbooks(tmp_path)
    assert len(pbs) == 2
    names = {pb.name for pb in pbs}
    assert "HTB initial recon" in names
    assert "b" in names


def test_scan_empty_dir_returns_empty(tmp_path):
    assert scan_playbooks(tmp_path) == []
```

- [ ] **Step 7.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_playbook_loader.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 7.3: Implement `loader.py`**

Create `src/bagley/tui/playbooks/loader.py`:

```python
"""Load and validate .playbooks/*.yml files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


class PlaybookValidationError(ValueError):
    """Raised when a playbook YAML fails schema validation."""


@dataclass
class PlaybookStep:
    kind: str                           # "run" | "if" | "prompt"
    run: Optional[str] = None           # shell command (run / if steps)
    condition: Optional[str] = None     # if-step condition
    prompt: Optional[str] = None        # prompt step text


@dataclass
class Playbook:
    name: str
    description: str
    target_template: str
    steps: list[PlaybookStep] = field(default_factory=list)
    source: Optional[Path] = None


def _parse_step(raw: dict) -> PlaybookStep:
    if "prompt" in raw:
        return PlaybookStep(kind="prompt", prompt=raw["prompt"])
    if "if" in raw:
        return PlaybookStep(kind="if", condition=raw["if"], run=raw.get("run", ""))
    if "run" in raw:
        return PlaybookStep(kind="run", run=raw["run"])
    raise PlaybookValidationError(f"Unknown step schema: {raw}")


def load_playbook(path: Path) -> Playbook:
    """Parse a single playbook YAML file and return a Playbook."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PlaybookValidationError("Playbook must be a YAML mapping")
    if "name" not in data:
        raise PlaybookValidationError("Playbook is missing required field 'name'")

    steps = [_parse_step(s) for s in data.get("steps", [])]
    return Playbook(
        name=data["name"],
        description=data.get("description", ""),
        target_template=data.get("target", "{target}"),
        steps=steps,
        source=path,
    )


def scan_playbooks(directory: Optional[Path] = None) -> list[Playbook]:
    """Scan *directory* (default: .playbooks/) for *.yml files and load them."""
    d = directory or (Path.cwd() / ".playbooks")
    if not d.exists():
        return []
    playbooks: list[Playbook] = []
    for yml in sorted(d.glob("*.yml")):
        try:
            playbooks.append(load_playbook(yml))
        except (PlaybookValidationError, yaml.YAMLError):
            pass  # Skip malformed files silently; caller can log
    return playbooks
```

- [ ] **Step 7.4: Run the tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_playbook_loader.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 7.5: Commit**

```bash
git add src/bagley/tui/playbooks/loader.py tests/tui/test_playbook_loader.py
git commit -m "feat(tui-p4): playbook YAML loader — scan, parse, validate steps"
```

---

## Task 8: Playbook runner

**Files:**
- Create: `src/bagley/tui/playbooks/runner.py`
- Create: `tests/tui/test_playbook_runner.py`

- [ ] **Step 8.1: Write the failing runner test**

Create `tests/tui/test_playbook_runner.py`:

```python
"""Tests for playbook runner — step execution and if-condition evaluation."""

from bagley.tui.playbooks.loader import Playbook, PlaybookStep
from bagley.tui.playbooks.runner import PlaybookRunner, substitute_vars, eval_condition


def test_substitute_vars_basic():
    assert substitute_vars("nmap -sV {target}", {"target": "10.0.0.1"}) == "nmap -sV 10.0.0.1"


def test_substitute_vars_multiple():
    assert substitute_vars("{a} {b}", {"a": "hello", "b": "world"}) == "hello world"


def test_eval_condition_ports_in():
    # Simple expression: "80 in ports"
    context = {"ports": [22, 80, 443]}
    assert eval_condition("80 in ports", context) is True
    assert eval_condition("8080 in ports", context) is False


def test_eval_condition_invalid_returns_false():
    assert eval_condition("INVALID SYNTAX !!!{}", {}) is False


def test_runner_converts_to_plan(tmp_path):
    pb = Playbook(
        name="test",
        description="",
        target_template="{target}",
        steps=[
            PlaybookStep(kind="run", run="nmap -sV {target}"),
            PlaybookStep(kind="prompt", prompt="summarize"),
        ],
    )
    runner = PlaybookRunner(playbook=pb, variables={"target": "10.0.0.1"})
    plan = runner.to_plan(tab_id="10.0.0.1")
    assert plan.goal == "test"
    assert len(plan.steps) == 2
    assert plan.steps[0].cmd == "nmap -sV 10.0.0.1"
    assert plan.steps[1].kind == "prompt"
    assert plan.steps[1].cmd == "summarize"


def test_runner_if_step_becomes_conditional_step(tmp_path):
    pb = Playbook(
        name="test",
        description="",
        target_template="{target}",
        steps=[
            PlaybookStep(kind="if", condition="80 in ports", run="gobuster dir -u http://{target}"),
        ],
    )
    runner = PlaybookRunner(playbook=pb, variables={"target": "10.0.0.1"})
    plan = runner.to_plan(tab_id="10.0.0.1")
    assert plan.steps[0].kind == "if"
    assert plan.steps[0].condition == "80 in ports"
    assert "gobuster" in plan.steps[0].cmd
```

- [ ] **Step 8.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_playbook_runner.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 8.3: Implement `runner.py`**

Create `src/bagley/tui/playbooks/runner.py`:

```python
"""Execute a Playbook by converting it to a Plan."""

from __future__ import annotations

import re
from typing import Any

from bagley.tui.plan_mode.plan import Plan, Step
from bagley.tui.playbooks.loader import Playbook


def substitute_vars(template: str, variables: dict[str, str]) -> str:
    """Replace ``{key}`` placeholders with *variables* values."""
    result = template
    for k, v in variables.items():
        result = result.replace(f"{{{k}}}", v)
    return result


def eval_condition(condition: str, context: dict[str, Any]) -> bool:
    """Safely evaluate a simple boolean condition string.

    *context* provides variable bindings (e.g. ``ports``, ``hosts``).
    Only allows ``in``, ``not in``, ``and``, ``or``, ``not`` and literals.
    Returns False on any evaluation error.
    """
    # Whitelist-based check: only allow safe tokens
    allowed = re.compile(r"^[\w\s\d\.\[\]\"\'\_\(\)]+$")
    if not allowed.match(condition):
        return False
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))  # noqa: S307
    except Exception:
        return False


class PlaybookRunner:
    """Converts a Playbook (with variable substitution) into a Plan."""

    def __init__(self, playbook: Playbook, variables: dict[str, str]) -> None:
        self.playbook = playbook
        self.variables = variables

    def to_plan(self, tab_id: str = "recon") -> Plan:
        """Build a Plan from the playbook steps with variables substituted."""
        steps: list[Step] = []
        for s in self.playbook.steps:
            if s.kind == "run":
                cmd = substitute_vars(s.run or "", self.variables)
                steps.append(Step(kind="run", cmd=cmd, description=f"Run: {cmd}"))
            elif s.kind == "prompt":
                steps.append(
                    Step(kind="prompt", cmd=s.prompt or "", description=f"Ask: {s.prompt}")
                )
            elif s.kind == "if":
                cmd = substitute_vars(s.run or "", self.variables)
                steps.append(
                    Step(
                        kind="if",
                        cmd=cmd,
                        description=f"If ({s.condition}): {cmd}",
                        condition=s.condition,
                    )
                )
        return Plan(goal=self.playbook.name, steps=steps, tab_id=tab_id)
```

- [ ] **Step 8.4: Run the tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_playbook_runner.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 8.5: Commit**

```bash
git add src/bagley/tui/playbooks/runner.py tests/tui/test_playbook_runner.py
git commit -m "feat(tui-p4): PlaybookRunner — substitute vars, eval conditions, to_plan"
```

---

## Task 9: Wire "Run playbook" into the command palette

**Files:**
- Modify: `src/bagley/tui/widgets/palette.py`

- [ ] **Step 9.1: Add "Run playbook …" action to the palette action list**

Open `src/bagley/tui/widgets/palette.py`. Find the list (or dict) where palette actions are registered. Add a new group or section:

```python
# Inside your action list/dict — exact structure matches Phase 1 style
PaletteAction(
    label="Run playbook …",
    description="Load a playbook from .playbooks/ and execute via plan mode",
    group="Playbooks",
    callback="run_playbook",
),
```

- [ ] **Step 9.2: Add `run_playbook` handler**

In the palette class (or `BagleyApp`), add:

```python
def action_run_playbook(self) -> None:
    from bagley.tui.playbooks.loader import scan_playbooks
    from bagley.tui.playbooks.runner import PlaybookRunner

    playbooks = scan_playbooks()
    if not playbooks:
        self.app.notify("No playbooks found in .playbooks/", severity="warning")
        return

    # Build list of (label, playbook) for a selection screen.
    # Use push_screen with callback — NOT push_screen_wait (Textual constraint).
    from bagley.tui.screens.playbook_select import PlaybookSelectScreen

    def _on_selected(result) -> None:
        if result is None:
            return
        playbook, target = result
        runner = PlaybookRunner(playbook=playbook, variables={"target": target})
        tab = self.app.state.tabs[self.app.state.active_tab]
        plan = runner.to_plan(tab_id=tab.id)
        try:
            chat = self.app.query_one("ChatPanel")
            chat.load_plan(plan)
        except Exception:
            self.app.notify("Could not load plan into chat panel", severity="error")

    self.app.push_screen(PlaybookSelectScreen(playbooks), callback=_on_selected)
```

- [ ] **Step 9.3: Verify palette tests still pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_palette.py -v
```

Expected: all existing palette tests pass unchanged.

- [ ] **Step 9.4: Commit**

```bash
git add src/bagley/tui/widgets/palette.py
git commit -m "feat(tui-p4): add 'Run playbook' action to command palette"
```

---

## Task 10: Bang re-exec expansion

**Files:**
- Create: `src/bagley/tui/interactions/bang.py`
- Create: `tests/tui/test_bang_expansion.py`

- [ ] **Step 10.1: Write the failing test**

Create `tests/tui/test_bang_expansion.py`:

```python
"""Tests for bang re-exec expansion: !!, !N, !prefix."""

import pytest

from bagley.tui.interactions.bang import BangExpander, BangExpansionError


HISTORY = ["nmap -sV 10.0.0.1", "gobuster dir ...", "ping 10.0.0.1", "nmap -p 80 10.0.0.1"]


def test_double_bang_returns_last():
    exp = BangExpander(cmd_history=HISTORY)
    assert exp.expand("!!") == "nmap -p 80 10.0.0.1"


def test_bang_n_returns_nth():
    exp = BangExpander(cmd_history=HISTORY)
    # !1 == index 0 (1-based)
    assert exp.expand("!1") == "nmap -sV 10.0.0.1"
    assert exp.expand("!2") == "gobuster dir ..."
    assert exp.expand("!4") == "nmap -p 80 10.0.0.1"


def test_bang_prefix_returns_last_matching():
    exp = BangExpander(cmd_history=HISTORY)
    assert exp.expand("!nmap") == "nmap -p 80 10.0.0.1"
    assert exp.expand("!ping") == "ping 10.0.0.1"
    assert exp.expand("!gob") == "gobuster dir ..."


def test_bang_prefix_no_match_raises():
    exp = BangExpander(cmd_history=HISTORY)
    with pytest.raises(BangExpansionError, match="No command"):
        exp.expand("!zzz")


def test_bang_n_out_of_range_raises():
    exp = BangExpander(cmd_history=HISTORY)
    with pytest.raises(BangExpansionError, match="index"):
        exp.expand("!99")


def test_non_bang_string_returned_as_is():
    exp = BangExpander(cmd_history=HISTORY)
    assert exp.expand("hello world") == "hello world"
    assert exp.expand("!") == "!"   # bare ! is not a valid bang


def test_empty_history_double_bang_raises():
    exp = BangExpander(cmd_history=[])
    with pytest.raises(BangExpansionError, match="empty"):
        exp.expand("!!")
```

- [ ] **Step 10.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_bang_expansion.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 10.3: Implement `bang.py`**

Create `src/bagley/tui/interactions/bang.py`:

```python
"""Bang re-exec: !!, !N, !prefix expansion from tab command history."""

from __future__ import annotations

import re


class BangExpansionError(ValueError):
    """Raised when a bang expression cannot be resolved."""


class BangExpander:
    """Expand bash-style history shortcuts against a command history list.

    History is ordered oldest-first; index 1 = first command.
    """

    _DOUBLE_BANG = re.compile(r"^!!$")
    _BANG_N = re.compile(r"^!(\d+)$")
    _BANG_PREFIX = re.compile(r"^!([A-Za-z0-9_/\-\.]+)$")

    def __init__(self, cmd_history: list[str]) -> None:
        self.cmd_history = cmd_history

    def expand(self, text: str) -> str:
        """Return the expanded string, or *text* unchanged if not a bang expr."""
        if self._DOUBLE_BANG.match(text):
            if not self.cmd_history:
                raise BangExpansionError("History is empty — cannot expand !!")
            return self.cmd_history[-1]

        m = self._BANG_N.match(text)
        if m:
            n = int(m.group(1))
            if n < 1 or n > len(self.cmd_history):
                raise BangExpansionError(
                    f"History index {n} out of range (1..{len(self.cmd_history)})"
                )
            return self.cmd_history[n - 1]

        m = self._BANG_PREFIX.match(text)
        if m:
            prefix = m.group(1)
            for cmd in reversed(self.cmd_history):
                if cmd.startswith(prefix):
                    return cmd
            raise BangExpansionError(
                f"No command in history starts with '{prefix}'"
            )

        return text  # Not a bang expression
```

- [ ] **Step 10.4: Run the tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_bang_expansion.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 10.5: Wire into `on_input_submitted` in `ChatPanel`**

Open `src/bagley/tui/panels/chat.py`. At the top:

```python
from bagley.tui.interactions.bang import BangExpander, BangExpansionError
```

Inside `on_input_submitted` (or equivalent submit handler), before the message is forwarded to the loop:

```python
# Bang expansion
tab = self.app.state.tabs[self.app.state.active_tab]
expander = BangExpander(cmd_history=tab.cmd_history)
try:
    message = expander.expand(message)
except BangExpansionError as exc:
    self._post_system_message(f"[bang error] {exc}")
    return
```

- [ ] **Step 10.6: Commit**

```bash
git add src/bagley/tui/interactions/bang.py tests/tui/test_bang_expansion.py src/bagley/tui/panels/chat.py
git commit -m "feat(tui-p4): bang re-exec — !!, !N, !prefix expansion in ChatPanel"
```

---

## Task 11: @ mention popup and token substitution

**Files:**
- Create: `src/bagley/tui/interactions/mentions.py`
- Create: `tests/tui/test_mentions_popup.py`

- [ ] **Step 11.1: Write the failing test**

Create `tests/tui/test_mentions_popup.py`:

```python
"""Tests for @ mention popup and token substitution."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input

from bagley.tui.interactions.mentions import MentionSubstitutor, build_mention_entries


# ── MentionSubstitutor unit tests ────────────────────────────────────────────

CONTEXT = {
    "hosts": ["10.0.0.1", "10.0.0.2"],
    "creds": {"admin": "admin:s3cr3t", "root": "root:toor"},
    "scan_last": "nmap -sV 10.0.0.1 result: open 22/tcp 80/tcp",
    "findings": {"CVE-2021-41773": "Apache path traversal"},
    "playbooks": ["htb-recon", "smb-enum"],
}


def test_substitutor_ip():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("scan @10.0.0.1 now")
    assert "10.0.0.1" in result  # IP mention resolves to the IP itself


def test_substitutor_creds_user():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("try @creds.admin on the form")
    assert "admin:s3cr3t" in result


def test_substitutor_creds_all():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("use @creds for hydra")
    assert "admin:s3cr3t" in result or "admin" in result


def test_substitutor_scan_last():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("review @scan.last findings")
    assert "nmap" in result


def test_substitutor_finding():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("exploit @finding.CVE-2021-41773")
    assert "Apache" in result


def test_substitutor_unknown_token_kept():
    sub = MentionSubstitutor(context=CONTEXT)
    result = sub.substitute("check @unknown.thing here")
    assert "@unknown.thing" in result  # Unknown tokens are preserved


def test_build_mention_entries_includes_ips():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@10.0.0.1" in labels
    assert "@10.0.0.2" in labels


def test_build_mention_entries_includes_creds():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@creds" in labels
    assert "@creds.admin" in labels


def test_build_mention_entries_includes_scan_last():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@scan.last" in labels


def test_build_mention_entries_includes_playbooks():
    entries = build_mention_entries(context=CONTEXT)
    labels = [e["label"] for e in entries]
    assert "@playbook.htb-recon" in labels
```

- [ ] **Step 11.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mentions_popup.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 11.3: Implement `mentions.py`**

Create `src/bagley/tui/interactions/mentions.py`:

```python
"""@ mention popup entries and token substitution for ChatPanel."""

from __future__ import annotations

import re
from typing import Any


# ── Entry builder ─────────────────────────────────────────────────────────────

def build_mention_entries(context: dict[str, Any]) -> list[dict]:
    """Build the full list of @-completable entries from current session state."""
    entries: list[dict] = []

    # Scope IPs
    for ip in context.get("hosts", []):
        entries.append({"label": f"@{ip}", "kind": "host", "value": ip})

    # Credentials (all + per-user)
    creds: dict = context.get("creds", {})
    entries.append({"label": "@creds", "kind": "creds", "value": "\n".join(creds.values())})
    for user in creds:
        entries.append({"label": f"@creds.{user}", "kind": "cred_user", "value": creds[user]})

    # Last scan
    if context.get("scan_last"):
        entries.append({"label": "@scan.last", "kind": "scan", "value": context["scan_last"]})

    # Findings
    for cve, desc in context.get("findings", {}).items():
        entries.append({"label": f"@finding.{cve}", "kind": "finding", "value": desc})

    # Playbooks
    for pb_name in context.get("playbooks", []):
        entries.append({"label": f"@playbook.{pb_name}", "kind": "playbook", "value": pb_name})

    return entries


# ── Token substitutor ─────────────────────────────────────────────────────────

_MENTION_RE = re.compile(r"@([\w\.\-]+)")


class MentionSubstitutor:
    """Replace ``@token`` patterns in a message with their concrete content."""

    def __init__(self, context: dict[str, Any]) -> None:
        self._entries: dict[str, str] = {
            e["label"].lstrip("@"): e["value"]
            for e in build_mention_entries(context)
        }

    def substitute(self, text: str) -> str:
        """Return *text* with every known @token replaced by its value."""

        def _replace(m: re.Match) -> str:
            token = m.group(1)
            return self._entries.get(token, m.group(0))

        return _MENTION_RE.sub(_replace, text)


# ── Fuzzy filter helper ───────────────────────────────────────────────────────

def fuzzy_filter(entries: list[dict], query: str) -> list[dict]:
    """Return entries whose label contains every character of *query* in order."""
    q = query.lower()
    result = []
    for e in entries:
        label = e["label"].lower()
        idx = 0
        for ch in q:
            pos = label.find(ch, idx)
            if pos == -1:
                break
            idx = pos + 1
        else:
            result.append(e)
    return result
```

- [ ] **Step 11.4: Run the tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mentions_popup.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 11.5: Wire mention substitution into `ChatPanel.on_input_submitted`**

Open `src/bagley/tui/panels/chat.py`. Add import:

```python
from bagley.tui.interactions.mentions import MentionSubstitutor, build_mention_entries
```

After the bang expansion block in `on_input_submitted`, add:

```python
# @ mention substitution
tab = self.app.state.tabs[self.app.state.active_tab]
context = {
    "hosts": list(self.app.state.scope_hosts),
    "creds": {c["user"]: f"{c['user']}:{c['pass']}" for c in tab.creds},
    "scan_last": tab.react_history[-1].get("output", "") if tab.react_history else "",
    "findings": {},   # TODO Phase 3 auto-memory populates this
    "playbooks": [],  # populated from scan_playbooks() lazily
}
substitutor = MentionSubstitutor(context=context)
message = substitutor.substitute(message)
```

- [ ] **Step 11.6: Commit**

```bash
git add src/bagley/tui/interactions/mentions.py tests/tui/test_mentions_popup.py src/bagley/tui/panels/chat.py
git commit -m "feat(tui-p4): @ mention entries, fuzzy filter, token substitution in ChatPanel"
```

---

## Task 12: Nmap and hash parsers

**Files:**
- Create: `src/bagley/tui/parsers/nmap.py`
- Create: `src/bagley/tui/parsers/hashes.py`
- Create: `tests/tui/test_smart_paste_nmap.py`
- Create: `tests/tui/test_smart_paste_hash.py`

- [ ] **Step 12.1: Write the failing nmap parser test**

Create `tests/tui/test_smart_paste_nmap.py`:

```python
"""Tests for nmap text output parser."""

from bagley.tui.parsers.nmap import parse_nmap_output, Host

NMAP_OUTPUT = """
Starting Nmap 7.94 ( https://nmap.org )
Nmap scan report for 10.10.14.5
Host is up (0.045s latency).

PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 8.9p1 Ubuntu
80/tcp   open  http     Apache httpd 2.4.52
443/tcp  closed https
3306/tcp open  mysql    MySQL 8.0.32

Nmap scan report for 10.10.14.6
Host is up (0.030s latency).

PORT   STATE SERVICE
22/tcp open  ssh

Nmap done: 2 IP addresses (2 hosts up) scanned
""".strip()


def test_parse_returns_hosts():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    assert len(hosts) == 2


def test_parse_first_host_ip():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    assert hosts[0].ip == "10.10.14.5"


def test_parse_first_host_ports():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    ports = {p.number for p in hosts[0].ports}
    assert 22 in ports
    assert 80 in ports
    assert 443 in ports
    assert 3306 in ports


def test_parse_open_ports_only_flag():
    hosts = parse_nmap_output(NMAP_OUTPUT, open_only=True)
    ports = {p.number for p in hosts[0].ports}
    assert 22 in ports
    assert 443 not in ports


def test_parse_service_version():
    hosts = parse_nmap_output(NMAP_OUTPUT)
    ssh_port = next(p for p in hosts[0].ports if p.number == 22)
    assert ssh_port.service == "ssh"
    assert "OpenSSH" in ssh_port.version


def test_parse_empty_returns_empty():
    assert parse_nmap_output("") == []
```

- [ ] **Step 12.2: Write the failing hash parser test**

Create `tests/tui/test_smart_paste_hash.py`:

```python
"""Tests for hash type detection."""

from bagley.tui.parsers.hashes import detect_hash_type, parse_hash_list, HashType

MD5    = "5d41402abc4b2a76b9719d911017c592"
SHA1   = "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"
SHA256 = "2c624232cdd221771294dfbb310acbc8abb9d04d8814c3b4b2f9f5b4c2d7d45b"
NTLM   = "b4b9b02e6f09a9bd760f388b67351e2b"  # same length as MD5, lowercase hex


def test_md5_detected():
    assert detect_hash_type(MD5) == HashType.MD5


def test_sha1_detected():
    assert detect_hash_type(SHA1) == HashType.SHA1


def test_sha256_detected():
    assert detect_hash_type(SHA256) == HashType.SHA256


def test_unknown_returns_none():
    assert detect_hash_type("notahash") is None
    assert detect_hash_type("") is None


def test_parse_hash_list_multiline():
    text = f"{MD5}\n{SHA1}\n{SHA256}\nnot-a-hash\n"
    results = parse_hash_list(text)
    assert len(results) == 3
    assert results[0] == (MD5, HashType.MD5)
    assert results[1] == (SHA1, HashType.SHA1)
    assert results[2] == (SHA256, HashType.SHA256)
```

- [ ] **Step 12.3: Run both tests — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_smart_paste_nmap.py tests/tui/test_smart_paste_hash.py -v
```

Expected: `ModuleNotFoundError` for both parsers.

- [ ] **Step 12.4: Implement `nmap.py`**

Create `src/bagley/tui/parsers/nmap.py`:

```python
"""Minimal nmap -sV text output parser."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    number: int
    protocol: str        # "tcp" | "udp"
    state: str           # "open" | "closed" | "filtered"
    service: str
    version: str = ""


@dataclass
class Host:
    ip: str
    ports: list[Port] = field(default_factory=list)

    def open_ports(self) -> list[Port]:
        return [p for p in self.ports if p.state == "open"]


_HOST_RE = re.compile(r"Nmap scan report for ([\d\.]+)")
_PORT_RE = re.compile(
    r"^(\d+)/(tcp|udp)\s+(open|closed|filtered)\s+(\S+)(?:\s+(.+))?$"
)


def parse_nmap_output(text: str, open_only: bool = False) -> list[Host]:
    """Parse nmap -sV plain-text output into a list of Host objects."""
    hosts: list[Host] = []
    current: Optional[Host] = None

    for line in text.splitlines():
        line = line.strip()
        m = _HOST_RE.match(line)
        if m:
            current = Host(ip=m.group(1))
            hosts.append(current)
            continue

        if current is not None:
            pm = _PORT_RE.match(line)
            if pm:
                number = int(pm.group(1))
                protocol = pm.group(2)
                state = pm.group(3)
                service = pm.group(4)
                version = (pm.group(5) or "").strip()
                if open_only and state != "open":
                    continue
                current.ports.append(
                    Port(number=number, protocol=protocol, state=state,
                         service=service, version=version)
                )

    return hosts
```

- [ ] **Step 12.5: Implement `hashes.py`**

Create `src/bagley/tui/parsers/hashes.py`:

```python
"""Hash type detection by length and character set."""

from __future__ import annotations

import enum
import re


class HashType(str, enum.Enum):
    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    SHA512 = "SHA512"
    NTLM = "NTLM"


_HEX_RE = re.compile(r"^[a-fA-F0-9]+$")

_LENGTH_MAP: dict[int, HashType] = {
    32: HashType.MD5,
    40: HashType.SHA1,
    64: HashType.SHA256,
    128: HashType.SHA512,
}


def detect_hash_type(value: str) -> HashType | None:
    """Return the most likely HashType for *value*, or None if not a hash."""
    value = value.strip()
    if not value or not _HEX_RE.match(value):
        return None
    return _LENGTH_MAP.get(len(value))


def parse_hash_list(text: str) -> list[tuple[str, HashType]]:
    """Parse a newline-separated list of hashes and return typed pairs."""
    results: list[tuple[str, HashType]] = []
    for line in text.splitlines():
        line = line.strip()
        ht = detect_hash_type(line)
        if ht is not None:
            results.append((line, ht))
    return results
```

- [ ] **Step 12.6: Run both tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_smart_paste_nmap.py tests/tui/test_smart_paste_hash.py -v
```

Expected: all 6 + 5 = 11 tests pass.

- [ ] **Step 12.7: Commit**

```bash
git add src/bagley/tui/parsers/nmap.py src/bagley/tui/parsers/hashes.py tests/tui/test_smart_paste_nmap.py tests/tui/test_smart_paste_hash.py
git commit -m "feat(tui-p4): nmap text parser (Host/Port) + hash type detector"
```

---

## Task 13: Shodan JSON parser and smart paste dispatcher

**Files:**
- Create: `src/bagley/tui/parsers/shodan.py`
- Create: `src/bagley/tui/interactions/smart_paste.py`
- Create: `tests/tui/test_smart_paste_ip_list.py`
- Create: `tests/tui/test_smart_paste_cve_url.py`

- [ ] **Step 13.1: Write the IP-list and CVE/URL tests**

Create `tests/tui/test_smart_paste_ip_list.py`:

```python
"""Tests for smart paste — IP list detection and scope-add flow."""

from bagley.tui.interactions.smart_paste import SmartPasteDispatcher, PasteClassification


IP_LIST = "10.0.0.1\n10.0.0.2\n10.0.0.3\n192.168.1.100\n"
NOT_IP_LIST = "hello world\nthis is text\nnot ips\n"
MIXED = "10.0.0.1\nsome text\n10.0.0.2\n"  # not pure IP list


def test_classify_ip_list():
    d = SmartPasteDispatcher()
    cls = d.classify(IP_LIST)
    assert cls == PasteClassification.IP_LIST


def test_classify_non_ip_list():
    d = SmartPasteDispatcher()
    cls = d.classify(NOT_IP_LIST)
    assert cls == PasteClassification.PLAIN_TEXT


def test_classify_mixed_is_plain():
    d = SmartPasteDispatcher()
    cls = d.classify(MIXED)
    assert cls == PasteClassification.PLAIN_TEXT


def test_extract_ips():
    d = SmartPasteDispatcher()
    ips = d.extract_ips(IP_LIST)
    assert ips == ["10.0.0.1", "10.0.0.2", "10.0.0.3", "192.168.1.100"]
```

Create `tests/tui/test_smart_paste_cve_url.py`:

```python
"""Tests for smart paste — CVE ID and URL classification."""

from bagley.tui.interactions.smart_paste import SmartPasteDispatcher, PasteClassification


def test_classify_cve():
    d = SmartPasteDispatcher()
    assert d.classify("CVE-2021-41773") == PasteClassification.CVE
    assert d.classify("cve-2023-1234") == PasteClassification.CVE


def test_classify_url():
    d = SmartPasteDispatcher()
    assert d.classify("https://example.com/path?q=1") == PasteClassification.URL
    assert d.classify("http://10.0.0.1:8080/admin") == PasteClassification.URL


def test_classify_nmap_output():
    nmap_text = "Nmap scan report for 10.0.0.1\nPORT   STATE SERVICE\n22/tcp open  ssh\n"
    d = SmartPasteDispatcher()
    assert d.classify(nmap_text) == PasteClassification.NMAP


def test_classify_hash_list():
    hashes = "5d41402abc4b2a76b9719d911017c592\naaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d\n"
    d = SmartPasteDispatcher()
    assert d.classify(hashes) == PasteClassification.HASH_LIST


def test_classify_plain_fallback():
    d = SmartPasteDispatcher()
    assert d.classify("just some random text") == PasteClassification.PLAIN_TEXT
```

- [ ] **Step 13.2: Run both tests — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_smart_paste_ip_list.py tests/tui/test_smart_paste_cve_url.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 13.3: Implement `shodan.py`**

Create `src/bagley/tui/parsers/shodan.py`:

```python
"""Minimal Shodan JSON → list[Host] parser."""

from __future__ import annotations

import json
from typing import Any

from bagley.tui.parsers.nmap import Host, Port


def parse_shodan_json(text: str) -> list[Host]:
    """Parse Shodan host JSON (single host or list) into Host objects.

    Handles both a bare Shodan host object and a list of them.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    hosts: list[Host] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        ip = item.get("ip_str") or item.get("ip")
        if not ip:
            continue
        ports: list[Port] = []
        for port_entry in item.get("ports", []):
            if isinstance(port_entry, int):
                ports.append(Port(number=port_entry, protocol="tcp", state="open",
                                  service="", version=""))
        # Also parse the richer 'data' array if present
        for svc in item.get("data", []):
            if isinstance(svc, dict):
                num = svc.get("port")
                if num:
                    ports.append(Port(
                        number=int(num),
                        protocol=svc.get("transport", "tcp"),
                        state="open",
                        service=svc.get("_shodan", {}).get("module", ""),
                        version=svc.get("product", ""),
                    ))
        hosts.append(Host(ip=str(ip), ports=ports))
    return hosts
```

- [ ] **Step 13.4: Implement `smart_paste.py`**

Create `src/bagley/tui/interactions/smart_paste.py`:

```python
"""Smart paste dispatcher — classify and route pasted content."""

from __future__ import annotations

import enum
import re
from typing import Optional


class PasteClassification(str, enum.Enum):
    NMAP = "nmap"
    SHODAN = "shodan"
    HASH_LIST = "hash_list"
    CVE = "cve"
    URL = "url"
    IP_LIST = "ip_list"
    PLAIN_TEXT = "plain_text"


_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_CVE_RE = re.compile(r"^cve-\d{4}-\d{4,}$", re.IGNORECASE)
_URL_RE = re.compile(r"^https?://\S+", re.IGNORECASE)
_HEX32_RE = re.compile(r"^[a-fA-F0-9]{32,128}$")


class SmartPasteDispatcher:
    """Classify pasted content and provide extraction helpers."""

    def classify(self, text: str) -> PasteClassification:
        """Return the most specific PasteClassification for *text*."""
        stripped = text.strip()

        # Single-line patterns first
        if _CVE_RE.match(stripped):
            return PasteClassification.CVE
        if _URL_RE.match(stripped):
            return PasteClassification.URL

        # Multi-line content
        lines = [l.strip() for l in stripped.splitlines() if l.strip()]
        if not lines:
            return PasteClassification.PLAIN_TEXT

        # Nmap: look for "Nmap scan report for" marker
        if any("Nmap scan report for" in l or "PORT   STATE" in l or "PORT     STATE" in l
               for l in lines):
            return PasteClassification.NMAP

        # Shodan JSON: starts with { and contains "ip_str"
        if stripped.startswith("{") and "ip_str" in stripped:
            return PasteClassification.SHODAN

        # Hash list: every non-empty line is a valid hex hash
        if all(_HEX32_RE.match(l) for l in lines):
            return PasteClassification.HASH_LIST

        # IP list: every non-empty line is a bare IPv4
        if all(_IP_RE.match(l) for l in lines):
            return PasteClassification.IP_LIST

        return PasteClassification.PLAIN_TEXT

    def extract_ips(self, text: str) -> list[str]:
        """Extract all IPv4 addresses from an IP-list-classified text."""
        return [
            l.strip()
            for l in text.splitlines()
            if _IP_RE.match(l.strip())
        ]
```

- [ ] **Step 13.5: Run all smart paste tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_smart_paste_ip_list.py tests/tui/test_smart_paste_cve_url.py -v
```

Expected: all 4 + 5 = 9 tests pass.

- [ ] **Step 13.6: Commit**

```bash
git add src/bagley/tui/parsers/shodan.py src/bagley/tui/interactions/smart_paste.py tests/tui/test_smart_paste_ip_list.py tests/tui/test_smart_paste_cve_url.py
git commit -m "feat(tui-p4): Shodan parser + SmartPasteDispatcher (classify/extract)"
```

---

## Task 14: Wire Ctrl+Shift+V smart paste into `app.py` and `chat.py`

**Files:**
- Modify: `src/bagley/tui/app.py`
- Modify: `src/bagley/tui/panels/chat.py`

- [ ] **Step 14.1: Add Ctrl+Shift+V binding to `app.py`**

Open `src/bagley/tui/app.py`. In the `BINDINGS` list, append:

```python
Binding("ctrl+shift+v", "smart_paste", "Smart paste"),
```

Add the action method to `BagleyApp`:

```python
def action_smart_paste(self) -> None:
    """Invoke smart paste: reads clipboard and dispatches to ChatPanel."""
    try:
        import pyperclip
        text = pyperclip.paste()
    except Exception:
        self.notify("Could not read clipboard (pyperclip missing?)", severity="error")
        return
    try:
        chat = self.query_one("ChatPanel")
        chat.handle_smart_paste(text)
    except Exception:
        self.notify("No active chat panel for smart paste", severity="warning")
```

- [ ] **Step 14.2: Add `handle_smart_paste` to `ChatPanel`**

Open `src/bagley/tui/panels/chat.py`. Add imports:

```python
from bagley.tui.interactions.smart_paste import SmartPasteDispatcher, PasteClassification
from bagley.tui.parsers.nmap import parse_nmap_output
from bagley.tui.parsers.hashes import parse_hash_list
```

Add inside `ChatPanel`:

```python
def handle_smart_paste(self, text: str) -> None:
    """Classify pasted content and dispatch to the appropriate handler."""
    dispatcher = SmartPasteDispatcher()
    cls = dispatcher.classify(text)

    if cls == PasteClassification.NMAP:
        hosts = parse_nmap_output(text)
        summary = f"Parsed nmap output: {len(hosts)} host(s). Promoting to memory."
        for host in hosts:
            # Write to memory via auto-memory layer (Phase 3 API)
            try:
                from bagley.tui.memory import ingest_hosts  # Phase 3 API
                ingest_hosts(hosts)
            except ImportError:
                pass
        self._post_system_message(summary)

    elif cls == PasteClassification.HASH_LIST:
        pairs = parse_hash_list(text)
        summary = f"Detected {len(pairs)} hash(es): " + ", ".join(
            f"{h[:8]}… ({t.value})" for h, t in pairs[:3]
        )
        self._post_system_message(summary)

    elif cls == PasteClassification.CVE:
        cve = text.strip()
        self._post_system_message(f"CVE detected: {cve}. Opening inspector.")
        # Trigger inspector (Phase 2 API)
        self.app.post_message_to("InspectorPane", cve)

    elif cls == PasteClassification.URL:
        url = text.strip()
        self._post_system_message(f"URL pasted: {url}. Consider: fingerprint + dir-bust.")

    elif cls == PasteClassification.IP_LIST:
        ips = dispatcher.extract_ips(text)

        def _on_confirm(confirmed: bool) -> None:
            if confirmed:
                for ip in ips:
                    self.app.state.scope_hosts |= frozenset([ip])
                self._post_system_message(f"Added {len(ips)} IP(s) to scope.")
            else:
                self._post_system_message("Scope add cancelled.")

        # Textual constraint: push_screen with callback, NOT push_screen_wait
        from bagley.tui.screens.confirm import ConfirmScreen
        self.app.push_screen(
            ConfirmScreen(f"Add {len(ips)} IP(s) to scope?"),
            callback=_on_confirm,
        )

    else:
        # Fallback: send as-is to chat loop
        self._submit_to_loop(text)
```

- [ ] **Step 14.3: Run the full Phase 4 test suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short
```

Expected: all Phase 4 tests pass. Any Phase 1/2/3 tests that exist should remain unaffected.

- [ ] **Step 14.4: Commit**

```bash
git add src/bagley/tui/app.py src/bagley/tui/panels/chat.py
git commit -m "feat(tui-p4): wire Ctrl+Shift+V smart paste into app + ChatPanel"
```

---

## Self-review checklist

Before marking Phase 4 complete, verify each item:

**Architecture**
- [ ] All 12 new modules have corresponding tests that were written *before* their implementation (TDD order verified in git log).
- [ ] No Phase 4 code touches `src/bagley/agent/`, `src/bagley/inference/`, `src/bagley/memory/store.py` (read-only from parsers only).
- [ ] `push_screen(callback=...)` used everywhere outside workers — no `push_screen_wait` in non-worker contexts.
- [ ] PyYAML is the only new runtime dependency added.

**Plan mode**
- [ ] `StepStatus` enum covers: PENDING, RUNNING, DONE, SKIPPED, FAILED.
- [ ] `Plan.advance()` marks DONE, `Plan.skip()` marks SKIPPED; both increment `current_index`.
- [ ] `PlanOverlay` emits `Dismissed` on Esc, `ApproveStep` on Enter, `EditStep` on `e`.
- [ ] `ChatPanel.on_plan_overlay_dismissed` calls `save_plan()` before removing the overlay.
- [ ] Plans saved to `.bagley/plans/<tab>-<ts>.yml` with colons stripped from timestamp.

**Playbooks**
- [ ] `PlaybookValidationError` raised when `name` is missing.
- [ ] `scan_playbooks()` silently skips malformed files.
- [ ] `eval_condition` uses a whitelist regex before calling `eval`; returns `False` on any error.
- [ ] Palette "Run playbook …" action calls `push_screen(PlaybookSelectScreen(...), callback=...)`.

**Bang re-exec**
- [ ] `!` alone (bare bang) is passed through unchanged.
- [ ] Empty history raises `BangExpansionError` for `!!`.
- [ ] `!prefix` scans history in reverse (most-recent-first).
- [ ] Bang expansion runs before `@` mention substitution in `on_input_submitted`.

**@ mentions**
- [ ] Unrecognized `@token` is preserved in the message (not silently dropped).
- [ ] `build_mention_entries` includes: `@<ip>`, `@creds`, `@creds.<user>`, `@scan.last`, `@finding.<cve>`, `@playbook.<name>`.
- [ ] `fuzzy_filter` is exported for use by the popup widget (Phase 5 full widget deferred to UI polish pass).

**Smart paste**
- [ ] Classifier order: CVE → URL → Nmap → Shodan → hash list → IP list → plain text.
- [ ] IP-list handler uses `push_screen(ConfirmScreen(...), callback=...)` before mutating scope.
- [ ] Nmap parse calls Phase 3 `ingest_hosts` wrapped in `try/except ImportError` (graceful if Phase 3 incomplete).
- [ ] Shodan parser handles both single-object and list-of-objects JSON.

**Tests**
- [ ] `tests/tui/test_plan_generator.py` — 9 tests (6 dataclass + 3 generator).
- [ ] `tests/tui/test_plan_overlay.py` — 6 tests.
- [ ] `tests/tui/test_plan_persistence.py` — 4 tests.
- [ ] `tests/tui/test_playbook_loader.py` — 5 tests.
- [ ] `tests/tui/test_playbook_runner.py` — 6 tests.
- [ ] `tests/tui/test_bang_expansion.py` — 7 tests.
- [ ] `tests/tui/test_mentions_popup.py` — 10 tests.
- [ ] `tests/tui/test_smart_paste_nmap.py` — 6 tests.
- [ ] `tests/tui/test_smart_paste_hash.py` — 5 tests.
- [ ] `tests/tui/test_smart_paste_ip_list.py` — 4 tests.
- [ ] `tests/tui/test_smart_paste_cve_url.py` — 5 tests.
- [ ] Total: **63 Phase 4 tests**.

**Git hygiene**
- [ ] Every commit uses `git add <exact paths>` — no `git add .` or `-A`.
- [ ] One commit per task (14 commits total for Phase 4).
- [ ] Commit messages follow pattern: `feat(tui-p4): <description>`.
- [ ] No plan document committed (this file is NOT committed per task instructions).
