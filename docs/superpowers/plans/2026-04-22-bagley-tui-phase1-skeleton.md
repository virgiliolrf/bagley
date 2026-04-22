# Bagley TUI — Phase 1 (Skeleton) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current Rich REPL (`src/bagley/agent/cli.py`) with a Textual-based TUI skeleton that boots, shows header + modes bar + tab bar + 4-pane dashboard (hosts, chat, target), wires existing `ReActLoop` into the chat panel, and supports basic keyboard navigation (tabs, focus, palette, disconnect). Ship a usable-but-minimal terminal UI that is tested with Textual's `Pilot` headless harness.

**Architecture:** New package `src/bagley/tui/` sits alongside existing `src/bagley/agent/cli.py`. `pyproject.toml` entry point routes `bagley` → `bagley.tui.app:run`; `bagley --simple` still reaches the old Rich REPL. In-memory `AppState` and `TabState` dataclasses hold the session; the existing `memory/store.py` SQLite layer is read from but not yet written to (auto-memory is Phase 3). Phase 1 implements only the RECON mode; other modes render in the bar but do nothing when pressed.

**Tech Stack:** Python 3.11, Textual 0.80+, pytest + pytest-asyncio (for `Pilot`), existing rich/typer/prompt_toolkit/transformers/peft stack.

---

## File structure

### Files to create

- `src/bagley/tui/__init__.py` — empty marker
- `src/bagley/tui/app.py` — `BagleyApp` class, `run()` entrypoint, argument parsing
- `src/bagley/tui/state.py` — `AppState`, `TabState`, `OsInfo` dataclasses + `detect_os()`
- `src/bagley/tui/widgets/header.py` — top-row header widget (OS, scope, mode, voice, alerts badge)
- `src/bagley/tui/widgets/modes_bar.py` — 9-pill modes bar (static render in Phase 1)
- `src/bagley/tui/widgets/tab_bar.py` — tab strip with "recon" tab + per-host tabs + `+` button
- `src/bagley/tui/widgets/statusline.py` — footer statusline (turn, model, hints)
- `src/bagley/tui/widgets/palette.py` — `CommandPalette` modal (Ctrl+K)
- `src/bagley/tui/panels/hosts.py` — `HostsPanel` (reads memory/store.py for hosts+ports+findings)
- `src/bagley/tui/panels/chat.py` — `ChatPanel` wrapping `ReActLoop` + inline confirmation
- `src/bagley/tui/panels/target.py` — `TargetPanel` (target info + kill-chain + creds + notes)
- `src/bagley/tui/screens/dashboard.py` — `DashboardScreen` (4-pane layout for a tab)
- `src/bagley/tui/screens/recon.py` — `ReconScreen` (tab 0 scope overview — same skeleton, different data binding)
- `src/bagley/tui/modes/__init__.py` — `Mode` dataclass + `RECON` instance (other modes stubbed with same defaults)
- `tests/tui/__init__.py` — empty marker
- `tests/tui/conftest.py` — Pilot fixtures
- `tests/tui/test_app_boot.py` — boot tests
- `tests/tui/test_header.py` — header content tests
- `tests/tui/test_modes_bar.py` — modes bar renders 9 pills
- `tests/tui/test_tab_bar.py` — tab bar tests
- `tests/tui/test_dashboard.py` — dashboard layout + navigation
- `tests/tui/test_hosts_panel.py` — HostsPanel data binding
- `tests/tui/test_chat_panel.py` — ChatPanel stream tests (stub engine)
- `tests/tui/test_target_panel.py` — TargetPanel sections
- `tests/tui/test_palette.py` — palette open/close
- `tests/tui/test_entrypoint.py` — `--simple` fallback
- `docs/superpowers/plans/2026-04-22-bagley-tui-phase1-skeleton.md` — this file

### Files to modify

- `pyproject.toml` — add deps (textual, pytest-asyncio), swap `[project.scripts].bagley` to new entrypoint, keep old entry accessible.

### Files NOT touched in Phase 1

`src/bagley/agent/cli.py` stays as-is — invoked via `bagley --simple`. `src/bagley/agent/loop.py`, `executor.py`, `inference/engine.py`, `memory/store.py`, `persona.py` are read-only in Phase 1.

---

## Task 1: Add dependencies and project scripts

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1.1: Add Textual + pytest-asyncio to dependencies**

Open `pyproject.toml`. In the `[project].dependencies` list, add:

```toml
    "textual>=0.80.0",
```

In `[project.optional-dependencies].dev`, replace the line with:

```toml
dev = ["pytest>=8.3.0", "pytest-asyncio>=0.24.0", "ruff>=0.7.0"]
```

- [ ] **Step 1.2: Swap the `bagley` entry point to the TUI**

Replace the `[project.scripts]` block:

```toml
[project.scripts]
bagley = "bagley.tui.app:run"
bagley-simple = "bagley.agent.cli:app"
```

This adds a second console script `bagley-simple` for the old Rich REPL while the new `bagley` points to the TUI. A `--simple` flag inside the TUI entrypoint (Task 11) also forwards to the old app.

- [ ] **Step 1.3: Install new deps in the existing venv**

Run:

```bash
.venv/Scripts/python.exe -m pip install "textual>=0.80.0" "pytest-asyncio>=0.24.0"
```

Expected: both packages install without error. Verify:

```bash
.venv/Scripts/python.exe -c "import textual, pytest_asyncio; print(textual.__version__, pytest_asyncio.__version__)"
```

Expected output: a Textual 0.80+ version string and a pytest-asyncio version string.

- [ ] **Step 1.4: Commit**

```bash
git add pyproject.toml
git commit -m "deps(tui): add textual and pytest-asyncio for Phase 1 TUI"
```

---

## Task 2: Package scaffolding and `AppState`

**Files:**
- Create: `src/bagley/tui/__init__.py`
- Create: `src/bagley/tui/state.py`
- Create: `tests/tui/__init__.py`
- Create: `tests/tui/conftest.py`
- Create: `tests/tui/test_state.py`

- [ ] **Step 2.1: Write the failing state test**

Create `tests/tui/test_state.py`:

```python
from bagley.tui.state import AppState, TabState, OsInfo, detect_os


def test_detect_os_returns_fields():
    info = detect_os()
    assert info.system in {"Windows", "Linux", "Darwin"}
    assert isinstance(info.release, str)
    assert isinstance(info.distro, str)           # "" when not Linux
    assert info.eof in {"Ctrl+D", "Ctrl+Z, Enter"}
    assert isinstance(info.pty_stream, bool)


def test_tabstate_defaults():
    t = TabState(id="recon", kind="recon")
    assert t.chat == []
    assert t.react_history == []
    assert t.cmd_history == []
    assert t.killchain_stage == 0
    assert t.creds == []
    assert t.notes_md == ""


def test_appstate_starts_with_recon_tab():
    os_info = detect_os()
    st = AppState(os_info=os_info)
    assert len(st.tabs) == 1
    assert st.tabs[0].id == "recon"
    assert st.tabs[0].kind == "recon"
    assert st.active_tab == 0
```

- [ ] **Step 2.2: Run the test — expected to fail (imports missing)**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_state.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui'`.

- [ ] **Step 2.3: Create empty package markers**

Create `src/bagley/tui/__init__.py` with content:

```python
"""Bagley Textual TUI package."""
```

Create `tests/tui/__init__.py` with content: empty file (literally zero bytes).

Create `tests/tui/conftest.py` with content:

```python
"""Shared Textual Pilot fixtures."""
```

- [ ] **Step 2.4: Implement `state.py`**

Create `src/bagley/tui/state.py`:

```python
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
    voice_state: str = "off"          # off | listen | active
    unread_alerts: int = 0
    turn: int = 0
```

- [ ] **Step 2.5: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_state.py -v
```

Expected: 3 tests pass.

- [ ] **Step 2.6: Commit**

```bash
git add src/bagley/tui/__init__.py src/bagley/tui/state.py tests/tui/__init__.py tests/tui/conftest.py tests/tui/test_state.py
git commit -m "feat(tui): AppState/TabState/OsInfo dataclasses with detect_os"
```

---

## Task 3: App boot + Pilot harness

**Files:**
- Create: `src/bagley/tui/app.py`
- Modify: `tests/tui/conftest.py`
- Create: `tests/tui/test_app_boot.py`

- [ ] **Step 3.1: Write the failing boot test**

Create `tests/tui/test_app_boot.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_app_boots_and_mounts_header():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(120, 40)) as pilot:
        assert app.state.mode == "RECON"
        header = app.query_one("#header")
        assert header is not None


@pytest.mark.asyncio
async def test_app_quits_on_ctrl_d():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+d")
        await pilot.pause()
    assert app._exit is True
```

- [ ] **Step 3.2: Register pytest-asyncio mode in `pyproject.toml`**

Append to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 3.3: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_app_boot.py -v
```

Expected: `ImportError` or `AttributeError` — `BagleyApp` does not exist.

- [ ] **Step 3.4: Implement the minimal app**

Create `src/bagley/tui/app.py`:

```python
"""BagleyApp — Textual TUI entrypoint."""

from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static

from bagley.tui.state import AppState, detect_os


class BagleyApp(App):
    CSS = """
    #header { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    BINDINGS = [
        Binding("ctrl+d", "disconnect", "Disconnect", show=True),
        Binding("ctrl+c", "disconnect", "Disconnect", show=False),
    ]

    def __init__(self, stub: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")

    def compose(self) -> ComposeResult:
        yield Static(self._header_text(), id="header")

    def _header_text(self) -> str:
        st = self.state
        return (
            f"Bagley · os={st.os_info.system} · scope=<none> · "
            f"mode={st.mode} · voice={st.voice_state} · turn={st.turn}"
        )

    def action_disconnect(self) -> None:
        self.exit()


def run() -> None:
    simple = "--simple" in sys.argv
    if simple:
        from bagley.agent.cli import app as simple_app
        sys.argv = [a for a in sys.argv if a != "--simple"]
        simple_app()
        return
    BagleyApp().run()
```

- [ ] **Step 3.5: Run the tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_app_boot.py -v
```

Expected: both tests pass.

- [ ] **Step 3.6: Smoke-run the TUI manually**

```bash
.venv/Scripts/python.exe -m bagley.tui.app
```

Expected: the terminal switches to the alt screen and shows a one-line header reading `Bagley · os=Windows · scope=<none> · mode=RECON · voice=off · turn=0`. Press Ctrl+D to exit cleanly.

- [ ] **Step 3.7: Commit**

```bash
git add src/bagley/tui/app.py tests/tui/test_app_boot.py pyproject.toml
git commit -m "feat(tui): BagleyApp boot with header and ctrl-d disconnect"
```

---

## Task 4: Header widget with live OS + scope + mode

**Files:**
- Create: `src/bagley/tui/widgets/__init__.py`
- Create: `src/bagley/tui/widgets/header.py`
- Create: `tests/tui/test_header.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 4.1: Write the failing header test**

Create `tests/tui/test_header.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_header_shows_os_and_mode():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        header = app.query_one("#header")
        rendered = header.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "Bagley" in text
        assert app.state.os_info.system in text
        assert "RECON" in text


@pytest.mark.asyncio
async def test_header_updates_when_mode_changes():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        app.state.mode = "EXPLOIT"
        header = app.query_one("#header")
        header.refresh_content()
        rendered = header.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "EXPLOIT" in text
```

- [ ] **Step 4.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_header.py -v
```

Expected: the second test fails with `AttributeError: refresh_content`.

- [ ] **Step 4.3: Implement the Header widget**

Create `src/bagley/tui/widgets/__init__.py`: empty file.

Create `src/bagley/tui/widgets/header.py`:

```python
"""Header widget — OS, scope, mode, voice, alerts badge."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.state import AppState


class Header(Static):
    DEFAULT_CSS = """
    Header { height: 1; background: $panel; color: $text; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="header", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        s = self._state
        scope = ",".join(s.scope_cidrs) or "<none>"
        self.update(
            f"[b]Bagley[/] · os={s.os_info.system} · scope={scope} · "
            f"[b]mode={s.mode}[/] · voice={s.voice_state} · "
            f"🔔 {s.unread_alerts} · turn={s.turn}"
        )
```

- [ ] **Step 4.4: Wire the Header into `app.py`**

Replace the `compose` method and drop the inline Static:

```python
    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        yield Header(self.state)
```

Remove the `_header_text` method — it's unused now.

- [ ] **Step 4.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_app_boot.py tests/tui/test_header.py -v
```

Expected: all four tests pass.

- [ ] **Step 4.6: Commit**

```bash
git add src/bagley/tui/widgets/__init__.py src/bagley/tui/widgets/header.py src/bagley/tui/app.py tests/tui/test_header.py
git commit -m "feat(tui): Header widget with live mode/scope/voice"
```

---

## Task 5: Modes bar with 9 pills

**Files:**
- Create: `src/bagley/tui/modes/__init__.py`
- Create: `src/bagley/tui/widgets/modes_bar.py`
- Create: `tests/tui/test_modes_bar.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 5.1: Write the failing modes-bar test**

Create `tests/tui/test_modes_bar.py`:

```python
import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.modes import MODES


def test_modes_registry_has_nine_entries():
    names = [m.name for m in MODES]
    assert names == [
        "RECON", "ENUM", "EXPLOIT", "POST",
        "PRIVESC", "STEALTH", "OSINT", "REPORT", "LEARN",
    ]


@pytest.mark.asyncio
async def test_modes_bar_renders_all_nine():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        bar = app.query_one("#modes-bar")
        rendered = bar.render().plain if hasattr(bar.render(), "plain") else str(bar.render())
        for name in ["RECON", "ENUM", "EXPLOIT", "POST", "PRIVESC",
                      "STEALTH", "OSINT", "REPORT", "LEARN"]:
            assert name in rendered


@pytest.mark.asyncio
async def test_alt_digit_switches_mode():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+3")   # EXPLOIT is #3
        await pilot.pause()
    assert app.state.mode == "EXPLOIT"
```

- [ ] **Step 5.2: Run — expected to fail (MODES undefined)**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_modes_bar.py -v
```

Expected: `ImportError: cannot import name 'MODES'`.

- [ ] **Step 5.3: Implement the modes registry**

Create `src/bagley/tui/modes/__init__.py`:

```python
"""Operational modes. Phase 1 registers all nine with identical RECON-level defaults."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    index: int
    name: str
    color: str
    persona_suffix: str
    confirm_policy: str = "explicit"          # "auto" | "explicit"


MODES: list[Mode] = [
    Mode(1, "RECON",    "cyan",       "Cautious observer. Read-only.",                  "auto"),
    Mode(2, "ENUM",     "orange3",    "Curious. Low-impact active enum.",               "auto"),
    Mode(3, "EXPLOIT",  "red",        "Aggressive. Proposes exploits.",                 "explicit"),
    Mode(4, "POST",     "magenta",    "Methodical looter on a shell.",                  "explicit"),
    Mode(5, "PRIVESC",  "dark_orange","Surgical escalator.",                            "explicit"),
    Mode(6, "STEALTH",  "grey50",     "Paranoid. Delays. Fragmentation.",               "explicit"),
    Mode(7, "OSINT",    "green",      "Passive stalker. No packets to target.",         "auto"),
    Mode(8, "REPORT",   "white",      "Formal writer. No exec.",                        "auto"),
    Mode(9, "LEARN",    "cyan",       "Didactic. Explain every flag and CVE.",          "explicit"),
]


def by_name(name: str) -> Mode:
    for m in MODES:
        if m.name == name:
            return m
    raise KeyError(name)


def by_index(idx: int) -> Mode:
    return MODES[idx - 1]
```

- [ ] **Step 5.4: Implement the modes bar widget**

Create `src/bagley/tui/widgets/modes_bar.py`:

```python
"""Modes bar — 9 pills, active one highlighted by state.mode."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.modes import MODES
from bagley.tui.state import AppState


class ModesBar(Static):
    DEFAULT_CSS = """
    ModesBar { height: 1; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="modes-bar", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        active = self._state.mode
        pills = []
        for m in MODES:
            marker = "◉" if m.name == active else "○"
            style = f"bold {m.color}" if m.name == active else f"dim {m.color}"
            pills.append(f"[{style}]{marker} {m.index}.{m.name}[/]")
        self.update(" ".join(pills))
```

- [ ] **Step 5.5: Add Alt+1..9 bindings and compose order in `app.py`**

Edit `src/bagley/tui/app.py`. Replace the BINDINGS list and compose:

```python
    BINDINGS = [
        Binding("ctrl+d", "disconnect", "Disconnect", show=True),
        Binding("ctrl+c", "disconnect", "Disconnect", show=False),
        Binding("alt+1", "set_mode(1)", "", show=False),
        Binding("alt+2", "set_mode(2)", "", show=False),
        Binding("alt+3", "set_mode(3)", "", show=False),
        Binding("alt+4", "set_mode(4)", "", show=False),
        Binding("alt+5", "set_mode(5)", "", show=False),
        Binding("alt+6", "set_mode(6)", "", show=False),
        Binding("alt+7", "set_mode(7)", "", show=False),
        Binding("alt+8", "set_mode(8)", "", show=False),
        Binding("alt+9", "set_mode(9)", "", show=False),
    ]

    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        from bagley.tui.widgets.modes_bar import ModesBar
        yield Header(self.state)
        yield ModesBar(self.state)

    def action_set_mode(self, idx: int) -> None:
        from bagley.tui.modes import by_index
        self.state.mode = by_index(idx).name
        self.query_one("#header").refresh_content()
        self.query_one("#modes-bar").refresh_content()
```

- [ ] **Step 5.6: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_modes_bar.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5.7: Commit**

```bash
git add src/bagley/tui/modes/__init__.py src/bagley/tui/widgets/modes_bar.py src/bagley/tui/app.py tests/tui/test_modes_bar.py
git commit -m "feat(tui): modes registry and bar with alt+digit switching"
```

---

## Task 6: Tab bar + tab switching

**Files:**
- Create: `src/bagley/tui/widgets/tab_bar.py`
- Create: `tests/tui/test_tab_bar.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 6.1: Write the failing tab-bar test**

Create `tests/tui/test_tab_bar.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_tab_bar_initial_has_recon_and_plus():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        bar = app.query_one("#tab-bar")
        rendered = bar.render().plain if hasattr(bar.render(), "plain") else str(bar.render())
        assert "recon" in rendered
        assert "+" in rendered


@pytest.mark.asyncio
async def test_ctrl_t_opens_new_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+t")
        await pilot.pause()
    assert len(app.state.tabs) == 2
    assert app.state.tabs[1].kind == "target"
    assert app.state.active_tab == 1


@pytest.mark.asyncio
async def test_ctrl_w_closes_non_recon_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert len(app.state.tabs) == 2
        await pilot.press("ctrl+w")
        await pilot.pause()
    assert len(app.state.tabs) == 1
    assert app.state.active_tab == 0


@pytest.mark.asyncio
async def test_ctrl_w_does_not_close_recon_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+w")
        await pilot.pause()
    assert len(app.state.tabs) == 1


@pytest.mark.asyncio
async def test_ctrl_digit_switches_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+t")
        await pilot.press("ctrl+t")
        await pilot.press("ctrl+1")
        await pilot.pause()
    assert app.state.active_tab == 0
```

- [ ] **Step 6.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_tab_bar.py -v
```

Expected: `AttributeError` or missing widget.

- [ ] **Step 6.3: Implement the tab bar**

Create `src/bagley/tui/widgets/tab_bar.py`:

```python
"""Tab bar with recon + per-target tabs and a + indicator."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.state import AppState


class TabBar(Static):
    DEFAULT_CSS = """
    TabBar { height: 1; padding: 0 1; background: $panel-lighten-1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="tab-bar", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        parts = []
        for i, tab in enumerate(self._state.tabs):
            label = tab.id
            if i == self._state.active_tab:
                parts.append(f"[reverse][b]{label}[/][/]")
            else:
                parts.append(f"[dim]{label}[/]")
        parts.append("[dim]+[/]")
        self.update(" │ ".join(parts))
```

- [ ] **Step 6.4: Add tab bindings + actions to `app.py`**

Append to the `BINDINGS` list:

```python
        Binding("ctrl+t", "new_tab", "New tab", show=True),
        Binding("ctrl+w", "close_tab", "Close tab", show=True),
        Binding("ctrl+1", "goto_tab(1)", "", show=False),
        Binding("ctrl+2", "goto_tab(2)", "", show=False),
        Binding("ctrl+3", "goto_tab(3)", "", show=False),
        Binding("ctrl+4", "goto_tab(4)", "", show=False),
        Binding("ctrl+5", "goto_tab(5)", "", show=False),
        Binding("ctrl+6", "goto_tab(6)", "", show=False),
        Binding("ctrl+7", "goto_tab(7)", "", show=False),
        Binding("ctrl+8", "goto_tab(8)", "", show=False),
        Binding("ctrl+9", "goto_tab(9)", "", show=False),
```

Append to compose (after `ModesBar`):

```python
        from bagley.tui.widgets.tab_bar import TabBar
        yield TabBar(self.state)
```

Add these action methods to `BagleyApp`:

```python
    def action_new_tab(self) -> None:
        from bagley.tui.state import TabState
        tab_id = f"target-{len(self.state.tabs)}"
        self.state.tabs.append(TabState(id=tab_id, kind="target"))
        self.state.active_tab = len(self.state.tabs) - 1
        self.query_one("#tab-bar").refresh_content()

    def action_close_tab(self) -> None:
        if self.state.active_tab == 0:
            return                                # recon tab is pinned
        del self.state.tabs[self.state.active_tab]
        self.state.active_tab = max(0, self.state.active_tab - 1)
        self.query_one("#tab-bar").refresh_content()

    def action_goto_tab(self, idx: int) -> None:
        target = idx - 1
        if 0 <= target < len(self.state.tabs):
            self.state.active_tab = target
            self.query_one("#tab-bar").refresh_content()
```

- [ ] **Step 6.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_tab_bar.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6.6: Commit**

```bash
git add src/bagley/tui/widgets/tab_bar.py src/bagley/tui/app.py tests/tui/test_tab_bar.py
git commit -m "feat(tui): tab bar with new/close/switch bindings"
```

---

## Task 7: 4-pane dashboard skeleton

**Files:**
- Create: `src/bagley/tui/panels/__init__.py`
- Create: `src/bagley/tui/panels/hosts.py` (minimal)
- Create: `src/bagley/tui/panels/chat.py` (minimal)
- Create: `src/bagley/tui/panels/target.py` (minimal)
- Create: `src/bagley/tui/screens/__init__.py`
- Create: `src/bagley/tui/screens/dashboard.py`
- Create: `tests/tui/test_dashboard.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 7.1: Write the failing dashboard test**

Create `tests/tui/test_dashboard.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_dashboard_has_three_panes():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        assert app.query_one("#hosts-panel") is not None
        assert app.query_one("#chat-panel") is not None
        assert app.query_one("#target-panel") is not None


@pytest.mark.asyncio
async def test_f2_focuses_hosts():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == "hosts-panel"


@pytest.mark.asyncio
async def test_f3_focuses_chat():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("f3")
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == "chat-panel"
```

- [ ] **Step 7.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_dashboard.py -v
```

Expected: widgets missing.

- [ ] **Step 7.3: Implement the three panel stubs**

Create `src/bagley/tui/panels/__init__.py`: empty file.

Create `src/bagley/tui/panels/hosts.py`:

```python
"""HostsPanel — left column: hosts, ports, findings. Phase 1 stub."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState


class HostsPanel(Vertical):
    DEFAULT_CSS = """
    HostsPanel { width: 28; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="hosts-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("[b orange3]◆ HOSTS[/]\n[dim](Phase 1 stub)[/]", id="hosts-section")
        yield Static("[b orange3]◆ PORTS[/]\n[dim](Phase 1 stub)[/]", id="ports-section")
        yield Static("[b orange3]◆ FINDINGS[/]\n[dim](Phase 1 stub)[/]", id="findings-section")
```

Create `src/bagley/tui/panels/chat.py`:

```python
"""ChatPanel — center column: ReAct stream. Phase 1 stub."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog, Input

from bagley.tui.state import AppState


class ChatPanel(Vertical):
    DEFAULT_CSS = """
    ChatPanel { border: round $primary; padding: 0 1; }
    ChatPanel > RichLog { height: 1fr; }
    ChatPanel > Input { height: 3; dock: bottom; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="chat-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        log = RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield log
        yield Input(placeholder="you> ", id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-log").write("[dim]Phase 1 — chat skeleton. ReActLoop wiring comes in Task 8.[/]")
```

Create `src/bagley/tui/panels/target.py`:

```python
"""TargetPanel — right column: target, kill-chain, creds, notes. Phase 1 stub."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState


class TargetPanel(Vertical):
    DEFAULT_CSS = """
    TargetPanel { width: 32; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="target-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("[b orange3]◆ TARGET[/]\n[dim](no target)[/]", id="target-info")
        yield Static("[b orange3]◆ KILL-CHAIN[/]\n"
                      "[dim]· recon · enum · exploit · postex · privesc · persist · cleanup[/]",
                      id="killchain")
        yield Static("[b orange3]◆ CREDS[/]\n[dim](none yet)[/]", id="creds-section")
        yield Static("[b orange3]◆ NOTES[/]\n[dim](empty)[/]", id="notes-section")
```

Create `src/bagley/tui/screens/__init__.py`: empty file.

Create `src/bagley/tui/screens/dashboard.py`:

```python
"""DashboardScreen — 4-pane layout for a tab."""

from __future__ import annotations

from textual.containers import Horizontal
from textual.screen import Screen

from bagley.tui.panels.chat import ChatPanel
from bagley.tui.panels.hosts import HostsPanel
from bagley.tui.panels.target import TargetPanel
from bagley.tui.state import AppState


class DashboardScreen(Screen):
    DEFAULT_CSS = """
    DashboardScreen { layout: vertical; }
    #pane-row { height: 1fr; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(**kwargs)
        self._state = state

    def compose(self):
        with Horizontal(id="pane-row"):
            yield HostsPanel(self._state)
            yield ChatPanel(self._state)
            yield TargetPanel(self._state)
```

- [ ] **Step 7.4: Wire the dashboard into `app.py`**

Replace `app.py`'s compose with a split layout. Change compose to:

```python
    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        from bagley.tui.widgets.modes_bar import ModesBar
        from bagley.tui.widgets.tab_bar import TabBar
        from bagley.tui.panels.hosts import HostsPanel
        from bagley.tui.panels.chat import ChatPanel
        from bagley.tui.panels.target import TargetPanel
        from textual.containers import Horizontal
        yield Header(self.state)
        yield ModesBar(self.state)
        yield TabBar(self.state)
        with Horizontal(id="pane-row"):
            yield HostsPanel(self.state)
            yield ChatPanel(self.state)
            yield TargetPanel(self.state)
```

Add to `BagleyApp.CSS`:

```css
    #pane-row { height: 1fr; }
```

Add focus bindings to `BINDINGS`:

```python
        Binding("f2", "focus('#hosts-panel')", "Hosts", show=True),
        Binding("f3", "focus('#chat-panel')", "Chat", show=True),
        Binding("f4", "focus('#target-panel')", "Notes", show=True),
```

Add the action:

```python
    def action_focus(self, selector: str) -> None:
        try:
            widget = self.query_one(selector)
        except Exception:
            return
        widget.focus()
```

- [ ] **Step 7.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_dashboard.py -v
```

Expected: 3 tests pass.

- [ ] **Step 7.6: Smoke-run the TUI**

```bash
.venv/Scripts/python.exe -m bagley.tui.app
```

Expected: header, modes bar, tab bar, three bordered panels in a horizontal row, labels `HOSTS / PORTS / FINDINGS`, `chat-log`, and `TARGET / KILL-CHAIN / CREDS / NOTES`. F2/F3/F4 cycle focus. Ctrl+D exits.

- [ ] **Step 7.7: Commit**

```bash
git add src/bagley/tui/panels/ src/bagley/tui/screens/ src/bagley/tui/app.py tests/tui/test_dashboard.py
git commit -m "feat(tui): 4-pane dashboard skeleton with focus bindings"
```

---

## Task 8: Wire `ReActLoop` into `ChatPanel`

**Files:**
- Modify: `src/bagley/tui/panels/chat.py`
- Create: `tests/tui/test_chat_panel.py`

- [ ] **Step 8.1: Write the failing chat test**

Create `tests/tui/test_chat_panel.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_chat_submit_updates_log_via_stub_engine():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        inp = app.query_one("#chat-input")
        inp.value = "hello"
        await pilot.press("f3")            # focus chat pane
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        log = app.query_one("#chat-log")
        text = "\n".join(str(line) for line in log.lines)
        assert "hello" in text
        assert "bagley" in text.lower()
        assert app.state.turn == 1
```

- [ ] **Step 8.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_chat_panel.py -v
```

Expected: state.turn stays 0 — submit doesn't call engine.

- [ ] **Step 8.3: Implement ChatPanel engine wiring**

Replace `src/bagley/tui/panels/chat.py`:

```python
"""ChatPanel — ReAct stream (Phase 1: plain exchange, no tool use UI yet)."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import RichLog, Input

from bagley.agent.loop import ReActLoop
from bagley.inference.engine import stub_response
from bagley.persona import DEFAULT_SYSTEM
from bagley.tui.state import AppState


class _StubEngine:
    def generate(self, messages, **kwargs):
        last = next((m for m in reversed(messages) if m["role"] == "user"), None)
        return stub_response(last["content"] if last else "")


class ChatPanel(Vertical):
    DEFAULT_CSS = """
    ChatPanel { border: round $primary; padding: 0 1; }
    ChatPanel > RichLog { height: 1fr; }
    ChatPanel > Input { height: 3; dock: bottom; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="chat-panel", **kwargs)
        self._state = state
        self._loop = ReActLoop(engine=_StubEngine(), auto_approve=True, max_steps=1)
        self.can_focus = True

    def compose(self):
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield Input(placeholder="you> ", id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-log").write(
            "[dim]Phase 1 chat (stub engine). Type and press Enter.[/]"
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input":
            return
        msg = event.value.strip()
        if not msg:
            return
        event.input.value = ""
        log = self.query_one("#chat-log")
        log.write(f"[bold green]you>[/] {msg}")
        steps = self._loop.run(msg, DEFAULT_SYSTEM)
        for step in steps:
            prefix = "[magenta]bagley>[/]" if step.kind in {"assistant", "final"} else "[yellow]tool>[/]"
            log.write(f"{prefix} {step.content}")
        self._state.turn += 1
        self.app.query_one("#header").refresh_content()
```

- [ ] **Step 8.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_chat_panel.py -v
```

Expected: test passes.

- [ ] **Step 8.5: Manual smoke-run**

```bash
.venv/Scripts/python.exe -m bagley.tui.app
```

Expected: type `oi` in the bottom input, press Enter. The log shows `you> oi` in green and `bagley> Stub mode...` in magenta. The header's turn counter advances.

- [ ] **Step 8.6: Commit**

```bash
git add src/bagley/tui/panels/chat.py tests/tui/test_chat_panel.py
git commit -m "feat(tui): ChatPanel wraps ReActLoop with stub engine"
```

---

## Task 9: `HostsPanel` reads `memory/store.py`

**Files:**
- Modify: `src/bagley/tui/panels/hosts.py`
- Create: `tests/tui/test_hosts_panel.py`

- [ ] **Step 9.1: Write the failing hosts-panel test**

Create `tests/tui/test_hosts_panel.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_hosts_panel_renders_store_content(tmp_path, monkeypatch):
    monkeypatch.setenv("BAGLEY_MEMORY_DB", str(tmp_path / "mem.db"))
    from bagley.memory.store import MemoryStore
    store = MemoryStore(str(tmp_path / "mem.db"))
    store.upsert_host("10.10.14.23", state="up")
    store.add_port("10.10.14.23", 22, "tcp", "ssh", "OpenSSH 8.9")
    store.add_finding("10.10.14.23", "HIGH", "web", "weak SSH kex", cve="CVE-2023-X")
    store.close()

    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        hosts = app.query_one("#hosts-section")
        ports = app.query_one("#ports-section")
        findings = app.query_one("#findings-section")
        h_text = str(hosts.render())
        p_text = str(ports.render())
        f_text = str(findings.render())
        assert "10.10.14.23" in h_text
        assert "22" in p_text and "ssh" in p_text
        assert "CVE-2023-X" in f_text or "weak SSH kex" in f_text
```

- [ ] **Step 9.2: Confirm `memory/store.py` supports `BAGLEY_MEMORY_DB`**

Read `src/bagley/memory/store.py`. If `MemoryStore` is constructed with a path, use that. If it hard-codes a path, add an override in the constructor or an env var fallback. This is in the existing codebase — do not change semantics beyond pulling the path.

If the constructor already accepts a path: good. If not, modify `MemoryStore.__init__` to respect `os.getenv("BAGLEY_MEMORY_DB", default=...)`.

- [ ] **Step 9.3: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_hosts_panel.py -v
```

Expected: sections still say "Phase 1 stub".

- [ ] **Step 9.4: Implement HostsPanel data binding**

Replace `src/bagley/tui/panels/hosts.py`:

```python
"""HostsPanel — reads memory/store.py for hosts + ports + findings."""

from __future__ import annotations

import os

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState


def _memory_path() -> str:
    return os.getenv("BAGLEY_MEMORY_DB", ".bagley/memory.db")


class HostsPanel(Vertical):
    DEFAULT_CSS = """
    HostsPanel { width: 28; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="hosts-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("", id="hosts-section")
        yield Static("", id="ports-section")
        yield Static("", id="findings-section")

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        from bagley.memory.store import MemoryStore
        try:
            store = MemoryStore(_memory_path())
        except Exception:
            self.query_one("#hosts-section").update("[b orange3]◆ HOSTS[/]\n[dim](memory unavailable)[/]")
            return
        try:
            hosts = store.list_hosts() if hasattr(store, "list_hosts") else []
            host_lines = ["[b orange3]◆ HOSTS[/]"]
            for h in hosts or []:
                ip = h.get("ip") if isinstance(h, dict) else h["ip"]
                state = h.get("state", "?") if isinstance(h, dict) else h["state"]
                dot = "●" if state == "up" else "○"
                host_lines.append(f"{ip} [green]{dot}[/]")
            if len(host_lines) == 1:
                host_lines.append("[dim](none)[/]")

            active = self._state.tabs[self._state.active_tab]
            target_ip = active.id if active.kind == "target" else None

            ports = []
            findings = []
            if target_ip and hasattr(store, "host_detail"):
                detail = store.host_detail(target_ip) or {}
                for p in detail.get("ports", []):
                    ports.append(f"{p['port']}/{p['proto']} [green]{p.get('service','?')}[/]")
                for f in detail.get("findings", []):
                    sev = f.get("severity", "?")
                    summary = f.get("summary", "")
                    cve = f.get("cve", "")
                    findings.append(f"[red]▸[/] {cve or summary} [dim]({sev})[/]")

            port_lines = ["[b orange3]◆ PORTS[/]"] + (ports or ["[dim](none)[/]"])
            finding_lines = ["[b orange3]◆ FINDINGS[/]"] + (findings or ["[dim](none)[/]"])

            self.query_one("#hosts-section").update("\n".join(host_lines))
            self.query_one("#ports-section").update("\n".join(port_lines))
            self.query_one("#findings-section").update("\n".join(finding_lines))
        finally:
            try:
                store.close()
            except Exception:
                pass
```

- [ ] **Step 9.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_hosts_panel.py -v
```

Expected: test passes. If `memory/store.py` lacks `list_hosts` or `host_detail`, the assertions for ports/findings fail — in that case, add thin wrappers in `store.py` that wrap existing SQL, then rerun.

- [ ] **Step 9.6: Commit**

```bash
git add src/bagley/tui/panels/hosts.py tests/tui/test_hosts_panel.py
git commit -m "feat(tui): HostsPanel reads from memory/store.py"
```

---

## Task 10: TargetPanel sections

**Files:**
- Modify: `src/bagley/tui/panels/target.py`
- Create: `tests/tui/test_target_panel.py`

- [ ] **Step 10.1: Write the failing target-panel test**

Create `tests/tui/test_target_panel.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_target_panel_shows_no_target_on_recon_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        info = app.query_one("#target-info")
        text = str(info.render())
        assert "no target" in text.lower()


@pytest.mark.asyncio
async def test_target_panel_killchain_shows_all_seven_stages():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        kc = app.query_one("#killchain")
        text = str(kc.render())
        for stage in ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]:
            assert stage in text.lower()


@pytest.mark.asyncio
async def test_target_panel_reflects_killchain_stage_marker():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        app.state.tabs[0].killchain_stage = 2
        app.query_one("#target-panel").refresh_content()
        kc = app.query_one("#killchain")
        text = str(kc.render())
        assert "▸" in text
```

- [ ] **Step 10.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_target_panel.py -v
```

Expected: static stub text, no marker logic.

- [ ] **Step 10.3: Implement the TargetPanel**

Replace `src/bagley/tui/panels/target.py`:

```python
"""TargetPanel — target info, kill-chain, creds, notes."""

from __future__ import annotations

from textual.containers import Vertical
from textual.widgets import Static

from bagley.tui.state import AppState

_STAGES = ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]


class TargetPanel(Vertical):
    DEFAULT_CSS = """
    TargetPanel { width: 32; border: round $accent; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="target-panel", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self):
        yield Static("", id="target-info")
        yield Static("", id="killchain")
        yield Static("", id="creds-section")
        yield Static("", id="notes-section")

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        tab = self._state.tabs[self._state.active_tab]
        if tab.kind == "recon":
            info = "[b orange3]◆ TARGET[/]\n[dim](no target — recon tab)[/]"
        else:
            info = f"[b orange3]◆ TARGET[/]\n[orange3]{tab.id}[/]"

        kc_lines = ["[b orange3]◆ KILL-CHAIN[/]"]
        for i, stage in enumerate(_STAGES):
            if i < tab.killchain_stage:
                kc_lines.append(f"[green]✓[/] {stage}")
            elif i == tab.killchain_stage:
                kc_lines.append(f"[orange3]▸[/] [b]{stage}[/]")
            else:
                kc_lines.append(f"[dim]·[/] [dim]{stage}[/]")

        creds = "[b orange3]◆ CREDS[/]\n"
        creds += "[dim](none yet)[/]" if not tab.creds else "\n".join(
            f"{c.get('user','?')}:{c.get('secret','?')}" for c in tab.creds
        )

        notes = "[b orange3]◆ NOTES[/]\n"
        notes += tab.notes_md or "[dim](empty)[/]"

        self.query_one("#target-info").update(info)
        self.query_one("#killchain").update("\n".join(kc_lines))
        self.query_one("#creds-section").update(creds)
        self.query_one("#notes-section").update(notes)
```

- [ ] **Step 10.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_target_panel.py -v
```

Expected: 3 tests pass.

- [ ] **Step 10.5: Wire panel refresh on tab change**

Modify `src/bagley/tui/app.py`. Update `action_new_tab`, `action_close_tab`, `action_goto_tab` to call `self.query_one("#hosts-panel").refresh_content()` and `self.query_one("#target-panel").refresh_content()` in addition to the tab-bar refresh.

Example for `action_goto_tab`:

```python
    def action_goto_tab(self, idx: int) -> None:
        target = idx - 1
        if 0 <= target < len(self.state.tabs):
            self.state.active_tab = target
            self.query_one("#tab-bar").refresh_content()
            self.query_one("#hosts-panel").refresh_content()
            self.query_one("#target-panel").refresh_content()
```

Apply the same pattern to `action_new_tab` and `action_close_tab`.

- [ ] **Step 10.6: Commit**

```bash
git add src/bagley/tui/panels/target.py src/bagley/tui/app.py tests/tui/test_target_panel.py
git commit -m "feat(tui): TargetPanel with kill-chain stage markers"
```

---

## Task 11: Command palette (Ctrl+K) minimal

**Files:**
- Create: `src/bagley/tui/widgets/palette.py`
- Create: `tests/tui/test_palette.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 11.1: Write the failing palette test**

Create `tests/tui/test_palette.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_ctrl_k_opens_palette():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+k")
        await pilot.pause()
        assert app.query_one("#palette", None) is not None


@pytest.mark.asyncio
async def test_palette_selects_new_tab_action():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+k")
        await pilot.pause()
        inp = app.query_one("#palette-input")
        inp.value = "new tab"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert len(app.state.tabs) == 2
```

- [ ] **Step 11.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_palette.py -v
```

Expected: `Ctrl+K` not bound.

- [ ] **Step 11.3: Implement the palette**

Create `src/bagley/tui/widgets/palette.py`:

```python
"""Command palette (Ctrl+K) — fuzzy action list."""

from __future__ import annotations

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static


ACTIONS: list[tuple[str, str]] = [
    ("new tab", "new_tab"),
    ("close tab", "close_tab"),
    ("focus hosts", "focus('#hosts-panel')"),
    ("focus chat", "focus('#chat-panel')"),
    ("focus target", "focus('#target-panel')"),
    ("disconnect", "disconnect"),
]


class CommandPalette(ModalScreen):
    DEFAULT_CSS = """
    CommandPalette { align: center middle; }
    #palette { width: 60; height: auto; border: round $primary;
                background: $panel; padding: 1 1; }
    #palette-results { height: auto; max-height: 10; }
    """

    def compose(self):
        with Vertical(id="palette"):
            yield Input(placeholder="type action…", id="palette-input")
            yield ListView(id="palette-results")

    def on_mount(self) -> None:
        self._refresh("")
        self.query_one("#palette-input").focus()

    def _refresh(self, query: str) -> None:
        lv = self.query_one("#palette-results", ListView)
        lv.clear()
        q = query.lower().strip()
        for label, _ in ACTIONS:
            if q in label:
                lv.append(ListItem(Static(label)))

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.lower().strip()
        for label, action in ACTIONS:
            if q in label:
                self.dismiss(action)
                return
        self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
```

- [ ] **Step 11.4: Bind Ctrl+K in `app.py`**

Append to `BINDINGS`:

```python
        Binding("ctrl+k", "open_palette", "Palette", show=True),
```

Add the handler:

```python
    async def action_open_palette(self) -> None:
        from bagley.tui.widgets.palette import CommandPalette
        result = await self.push_screen_wait(CommandPalette())
        if result is None:
            return
        if "(" in result:
            name, _, rest = result.partition("(")
            arg = rest.rstrip(")").strip("'\"")
            method = getattr(self, f"action_{name}", None)
            if method:
                method(arg)
        else:
            method = getattr(self, f"action_{result}", None)
            if method:
                method()
```

- [ ] **Step 11.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_palette.py -v
```

Expected: 2 tests pass.

- [ ] **Step 11.6: Commit**

```bash
git add src/bagley/tui/widgets/palette.py src/bagley/tui/app.py tests/tui/test_palette.py
git commit -m "feat(tui): Ctrl+K command palette with minimal action set"
```

---

## Task 12: `--simple` fallback + entrypoint wiring

**Files:**
- Modify: `src/bagley/tui/app.py`
- Create: `tests/tui/test_entrypoint.py`

- [ ] **Step 12.1: Write the failing entrypoint test**

Create `tests/tui/test_entrypoint.py`:

```python
import sys

import pytest


def test_run_routes_simple_flag_to_old_cli(monkeypatch):
    calls = {"simple": 0, "tui": 0}

    def fake_simple():
        calls["simple"] += 1

    class FakeApp:
        def run(self):
            calls["tui"] += 1

    from bagley.tui import app as app_mod
    monkeypatch.setattr(app_mod, "BagleyApp", lambda *a, **kw: FakeApp())
    monkeypatch.setattr("bagley.agent.cli.app", fake_simple)
    monkeypatch.setattr(sys, "argv", ["bagley", "--simple"])
    app_mod.run()
    assert calls == {"simple": 1, "tui": 0}


def test_run_routes_default_to_tui(monkeypatch):
    calls = {"simple": 0, "tui": 0}

    class FakeApp:
        def run(self):
            calls["tui"] += 1

    from bagley.tui import app as app_mod
    monkeypatch.setattr(app_mod, "BagleyApp", lambda *a, **kw: FakeApp())
    monkeypatch.setattr("bagley.agent.cli.app", lambda: calls.update(simple=calls["simple"] + 1))
    monkeypatch.setattr(sys, "argv", ["bagley"])
    app_mod.run()
    assert calls == {"simple": 0, "tui": 1}
```

- [ ] **Step 12.2: Run — expected to pass or fail depending on current `run()`**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_entrypoint.py -v
```

If the `run()` from Task 3.4 still has the `--simple` branch intact, both tests pass. If it was modified, restore it per 3.4.

- [ ] **Step 12.3: Ensure entrypoint accepts CLI flags for engine**

Extend `run()` in `src/bagley/tui/app.py` so that engine flags are parsed and forwarded to `BagleyApp` (the `--simple` branch short-circuits to old CLI):

```python
def run() -> None:
    if "--simple" in sys.argv:
        from bagley.agent.cli import app as simple_app
        sys.argv = [a for a in sys.argv if a != "--simple"]
        simple_app()
        return

    import argparse
    parser = argparse.ArgumentParser(prog="bagley", add_help=False)
    parser.add_argument("--stub", action="store_true")
    parser.add_argument("--adapter", default=None)
    parser.add_argument("--base", default="./models/foundation-sec-8b")
    parser.add_argument("--ollama", action="store_true")
    parser.add_argument("--ollama-model", default="bagley")
    parser.add_argument("-h", "--help", action="store_true")
    args, _ = parser.parse_known_args()

    if args.help:
        print("bagley [--stub] [--adapter PATH] [--base PATH] [--ollama] [--simple]")
        return

    BagleyApp(stub=args.stub).run()
```

(Full engine-flag wiring beyond `--stub` comes in Phase 2. Phase 1 only honors `--stub` because chat is still stub-engine; other flags are parsed for forward-compat but ignored.)

- [ ] **Step 12.4: Run full TUI test suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v
```

Expected: all tests pass. If any fail, fix before continuing.

- [ ] **Step 12.5: Smoke-test the installed `bagley` entrypoint**

```bash
.venv/Scripts/python.exe -m pip install -e .
bagley --simple --stub
```

Expected: the old Rich REPL opens. Type `/exit`.

```bash
bagley --stub
```

Expected: the new TUI opens with header + modes bar + tab bar + 4-pane dashboard. Type `hello` in chat, press Enter, see stub response. Press Ctrl+K, type `new`, press Enter, see a new tab appear. Press Ctrl+W to close. Press Ctrl+D to exit.

- [ ] **Step 12.6: Commit**

```bash
git add src/bagley/tui/app.py tests/tui/test_entrypoint.py
git commit -m "feat(tui): entrypoint routes --simple to old REPL, TUI is default"
```

---

## Task 13: Statusline footer

**Files:**
- Create: `src/bagley/tui/widgets/statusline.py`
- Create: `tests/tui/test_statusline.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 13.1: Write the failing statusline test**

Create `tests/tui/test_statusline.py`:

```python
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_statusline_shows_turn_and_engine():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        footer = app.query_one("#statusline")
        text = str(footer.render())
        assert "turn=0" in text
        assert "engine=stub" in text
        assert "F1" in text or "palette" in text
```

- [ ] **Step 13.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_statusline.py -v
```

Expected: no `#statusline`.

- [ ] **Step 13.3: Implement the statusline**

Create `src/bagley/tui/widgets/statusline.py`:

```python
"""Statusline footer — turn, engine, hints."""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.state import AppState


class Statusline(Static):
    DEFAULT_CSS = """
    Statusline { height: 1; dock: bottom; background: $panel; color: $text-muted; padding: 0 1; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="statusline", **kwargs)
        self._state = state

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        s = self._state
        self.update(
            f"turn={s.turn} · engine={s.engine_label} · "
            f"[b]F1[/] help · [b]Ctrl+K[/] palette · [b]Ctrl+D[/] disconnect"
        )
```

- [ ] **Step 13.4: Mount the statusline in `app.py`**

In `compose`, yield `Statusline(self.state)` as the last child (Textual docks it via CSS).

```python
        from bagley.tui.widgets.statusline import Statusline
        yield Statusline(self.state)
```

In `ChatPanel.on_input_submitted` (and anywhere state.turn changes), also refresh the statusline:

```python
        self.app.query_one("#statusline").refresh_content()
```

- [ ] **Step 13.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_statusline.py -v
```

Expected: passes.

- [ ] **Step 13.6: Commit**

```bash
git add src/bagley/tui/widgets/statusline.py src/bagley/tui/app.py src/bagley/tui/panels/chat.py tests/tui/test_statusline.py
git commit -m "feat(tui): statusline footer with turn/engine/key-hints"
```

---

## Task 14: Phase 1 acceptance checklist

- [ ] **Step 14.1: Run the full suite one last time**

```bash
.venv/Scripts/python.exe -m pytest -v
```

Expected: every test in `tests/tui/` and every pre-existing test in `tests/` pass. If a pre-existing test breaks, diagnose and fix before moving on.

- [ ] **Step 14.2: Manual walkthrough**

```bash
.venv/Scripts/python.exe -m bagley.tui.app --stub
```

Tick each off as you verify it on screen:
- Header shows OS, scope=`<none>`, mode=RECON, voice=off, alerts badge.
- Modes bar shows nine pills; RECON is highlighted.
- Tab bar shows `recon` selected and a `+` indicator.
- Three bordered panels are visible: HOSTS/PORTS/FINDINGS · chat-log+input · TARGET/KILL-CHAIN/CREDS/NOTES.
- Statusline at the bottom shows turn=0, engine=stub, key hints.
- Typing `hello` in chat + Enter writes two lines to the log; turn advances to 1.
- `Alt+3` switches mode to EXPLOIT (header and modes bar update colors).
- `Ctrl+T` opens `target-1` tab; `Ctrl+1` returns to recon; `Ctrl+W` closes `target-1`.
- `Ctrl+K` opens palette; typing `new` + Enter creates a tab.
- `F2`/`F3`/`F4` focus the three panes.
- `Ctrl+D` disconnects cleanly.

- [ ] **Step 14.3: Tag the Phase 1 milestone**

```bash
git tag -a tui-phase1 -m "TUI Phase 1 skeleton complete"
```

- [ ] **Step 14.4: Write a one-line migration note in `README.md`**

Modify `README.md`. Add a short section:

```markdown
## CLI

- `bagley` — Textual TUI (default).
- `bagley --simple` — legacy Rich REPL.
- `bagley --stub` — skip engine load for UI-only testing.
```

Commit:

```bash
git add README.md
git commit -m "docs: TUI replaces Rich REPL as default"
```

---

## Self-review

**Spec coverage for Phase 1** (spec §11 Phase 1 lists: Textual app boots with header, modes bar, tab bar, 4-pane dashboard; Recon + single target tab; ChatPanel shows ReAct stream with existing ReActLoop; HostsPanel/TargetPanel read from memory/store.py; keymap Ctrl+T/W/1..9, F1..F6, Ctrl+D, Esc, Ctrl+K palette minimal; modes bar visible but only RECON implemented; smoke-testable on Linux + Windows):

- Textual app boots → Task 3
- Header / modes bar / tab bar / 4-pane dashboard → Tasks 4/5/6/7
- Recon + single target tab → Task 6 (recon is tab 0, targets spawn via Ctrl+T)
- ChatPanel wraps ReActLoop → Task 8
- HostsPanel reads store → Task 9
- TargetPanel sections → Task 10
- Keymap: Ctrl+T/W (Task 6), Ctrl+1..9 (Task 6), F2/F3/F4 (Task 7, F5/F6 deferred since no raw-terminal pane yet), Ctrl+D (Task 3), Esc (palette Task 11), Ctrl+K (Task 11)
- Modes bar, only RECON wired → Task 5 + modes registry
- Smoke-testable cross-platform → Task 12.5, Task 14.2

**Deferred to Phase 2+ (documented in spec):** F5 findings focus (needs separate widget), F6 raw terminal pane, mode-specific persona injection into ReActLoop (Phase 2), real engine load beyond stub (Phase 2), voice toggle, alerts, auto-memory, plan mode, inspector, shell panes, playbooks, timeline, graph, payload, hot-swap, report, tour.

**Placeholder scan:** no TBD, no "implement later", every code step contains runnable code, every test step has a concrete assertion.

**Type consistency:** `AppState` / `TabState` field names match across tasks (scope_cidrs, scope_hosts, active_tab, killchain_stage, engine_label, turn). `refresh_content` is the conventional method name on every state-reading widget. `Mode.name` and `Mode.index` stable across 5/11.

**Dependencies lock-in:** Textual 0.80+, pytest-asyncio 0.24+; both installed in Task 1.
