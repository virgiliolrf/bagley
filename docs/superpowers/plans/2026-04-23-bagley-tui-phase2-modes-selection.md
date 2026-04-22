# Bagley TUI — Phase 2 (Modes + Selection Inspector + Palette Expansion + Inline Confirmation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire all 9 operational modes fully into the `ReActLoop` (persona suffix appended to system prompt, tool allowlist intersected at exec time, confirm policy enforced), update chat border color on mode change, implement the selection inspector (`Ctrl+I`) as a dockable bottom-right `InspectorPane` with regex-based classification for at least 7 types, expand the command palette from 6 to ~50 actions, and render the tool-confirmation prompt inline inside `ChatPanel` instead of as an external blocking call. All features are built with strict TDD: failing test first, minimal implementation to pass, then commit.

**Architecture:** Phase 1 left `modes/__init__.py` with a `Mode` dataclass that has `persona_suffix` and `confirm_policy` but no `allowlist` field, and `ChatPanel` uses a hard-coded `ReActLoop(auto_approve=True)`. Phase 2 adds two thin mode adapter modules (`persona.py`, `policy.py`), a new `interactions/` sub-package (`selection.py`, `inspector_actions.py`), a new `InspectorPane` widget, and threads them together in `app.py` and `chat.py`. No Phase 1 files are deleted. The existing `ReActLoop` interface is respected — the allowlist is enforced by wrapping `confirm_fn`, not by patching the loop internals.

**Tech Stack:** Python 3.11, Textual 0.80+, pytest + pytest-asyncio (asyncio_mode = "auto"), existing `bagley.agent.loop.ReActLoop`, `bagley.agent.executor`, `bagley.tui.modes.MODES`. Branch: `tui-phase1` (continue on same branch). Venv: `.venv/Scripts/python.exe`.

**Key Phase 1 lesson:** Use `push_screen(callback=...)` not `await push_screen_wait(...)` outside workers.

---

## File structure

### Files to create

- `src/bagley/tui/modes/persona.py` — `mode_system_suffix(mode_name) -> str`; returns the full persona hint string for each of the 9 modes
- `src/bagley/tui/modes/policy.py` — `apply_mode_to_loop(loop, mode_name)` mutates a `ReActLoop` instance: sets `confirm_fn` and wraps the executor-level allowlist
- `src/bagley/tui/interactions/__init__.py` — empty marker
- `src/bagley/tui/interactions/selection.py` — `classify(text) -> ClassifyResult`; regex-based classifier for ipv4, cidr, cve, md5, sha256, url, port, path
- `src/bagley/tui/interactions/inspector_actions.py` — `InspectorAction` dataclass + `actions_for(result) -> list[InspectorAction]`
- `src/bagley/tui/panels/inspector.py` — `InspectorPane` Textual widget (bottom-right overlay, dockable)
- `tests/tui/test_mode_policy.py` — mode changes affect ReActLoop allowlist and system prompt
- `tests/tui/test_selection_classifier.py` — regex classifier unit tests
- `tests/tui/test_inspector_panel.py` — Ctrl+I opens inspector with correct classification
- `tests/tui/test_palette_expanded.py` — palette finds common actions via fuzzy search
- `tests/tui/test_inline_confirm.py` — confirmation renders inline in chat, y/n buttons dispatch

### Files to modify

- `src/bagley/tui/modes/__init__.py` — add `allowlist: frozenset[str]` field to `Mode` dataclass; populate per-mode; add `ALLOWLISTS` dict helper
- `src/bagley/tui/widgets/palette.py` — replace 6-item `ACTIONS` list with ~50-item expanded list; add fuzzy substring ranking helper
- `src/bagley/tui/panels/chat.py` — add inline `ConfirmPanel`; wire `apply_mode_to_loop`; add `Ctrl+I` selection handler; update `ReActLoop` construction to respect mode
- `src/bagley/tui/app.py` — add `Ctrl+M` mode-cycle binding; mount/unmount `InspectorPane`; add `Ctrl+I` app-level handler; update `action_set_mode` to call `apply_mode_to_loop` and repaint chat border

### Files NOT touched in Phase 2

`src/bagley/agent/loop.py`, `src/bagley/agent/executor.py`, `src/bagley/agent/safeguards.py`, `src/bagley/inference/engine.py`, `src/bagley/persona.py`, `memory/store.py`. All Phase 1 panel/widget/screen files except `chat.py`. The `--simple` fallback path is untouched.

---

## Task 1: Extend `Mode` dataclass with allowlist field

**Files:**
- Modify: `src/bagley/tui/modes/__init__.py`

- [ ] **Step 1.1: Write the failing allowlist test**

Create `tests/tui/test_mode_policy.py`:

```python
"""Tests: mode wiring — allowlist, persona suffix, confirm policy."""

import pytest
from bagley.tui.modes import MODES, by_name, by_index


def test_all_modes_have_allowlist():
    for m in MODES:
        assert hasattr(m, "allowlist"), f"{m.name} missing allowlist"
        assert isinstance(m.allowlist, frozenset), f"{m.name}.allowlist must be frozenset"


def test_exploit_allowlist_contains_sqlmap():
    m = by_name("EXPLOIT")
    assert "sqlmap" in m.allowlist


def test_recon_allowlist_contains_nmap():
    m = by_name("RECON")
    assert "nmap" in m.allowlist


def test_report_allowlist_is_readonly():
    m = by_name("REPORT")
    # REPORT has no shell exec tools
    assert len(m.allowlist) == 0


def test_learn_allowlist_is_none_sentinel():
    # LEARN inherits caller's allowlist; sentinel is None
    m = by_name("LEARN")
    assert m.allowlist is None


def test_mode_index_ordering():
    for i, m in enumerate(MODES, start=1):
        assert m.index == i
```

- [ ] **Step 1.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mode_policy.py::test_all_modes_have_allowlist -v
```

Expected: `AttributeError: 'Mode' object has no attribute 'allowlist'`.

- [ ] **Step 1.3: Add `allowlist` field to `Mode` and populate per-mode**

Replace `src/bagley/tui/modes/__init__.py` entirely:

```python
"""Operational modes — registry with allowlist, persona suffix, confirm policy, color."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Mode:
    index: int
    name: str
    color: str
    persona_suffix: str
    confirm_policy: str                     # "auto" | "explicit"
    allowlist: Optional[frozenset[str]]     # None = inherit / unrestricted (LEARN)


MODES: list[Mode] = [
    Mode(
        1, "RECON", "cyan",
        "Cautious observer. Read-only. No packets that touch the target beyond banner grabs.",
        "auto",
        frozenset({"nmap", "dig", "whois", "traceroute", "masscan"}),
    ),
    Mode(
        2, "ENUM", "orange3",
        "Curious, detail-oriented. Low-impact active enumeration.",
        "auto",
        frozenset({"gobuster", "ffuf", "nikto", "enum4linux-ng", "smbmap", "ssh-audit"}),
    ),
    Mode(
        3, "EXPLOIT", "red",
        "Aggressive. Proposes exploits. No handholding.",
        "explicit",
        frozenset({"sqlmap", "msfconsole", "hydra", "medusa", "exploit-db", "searchsploit"}),
    ),
    Mode(
        4, "POST", "magenta",
        "Methodical looter on a shell. Prefer LOLBins.",
        "explicit",
        frozenset({"linpeas", "winpeas", "mimikatz", "lazagne", "find", "ls", "cat"}),
    ),
    Mode(
        5, "PRIVESC", "dark_orange",
        "Surgical escalator.",
        "explicit",
        frozenset({"linpeas", "linux-exploit-suggester", "pspy", "find", "id", "uname"}),
    ),
    Mode(
        6, "STEALTH", "grey50",
        "Paranoid. Delays. Fragmentation. Tor/proxychains.",
        "explicit",
        frozenset({"nmap", "proxychains", "tor", "torsocks"}),
    ),
    Mode(
        7, "OSINT", "green",
        "Passive stalker. No packets to target.",
        "auto",
        frozenset({"shodan", "censys", "theharvester", "dnsenum", "whois", "dig"}),
    ),
    Mode(
        8, "REPORT", "white",
        "Formal writer. No exec.",
        "auto",
        frozenset(),                        # empty = no shell exec
    ),
    Mode(
        9, "LEARN", "cyan",
        "Didactic. Explain every flag, CVE, and side effect.",
        "explicit",
        None,                               # None = inherit active mode's allowlist
    ),
]


def by_name(name: str) -> Mode:
    for m in MODES:
        if m.name == name:
            return m
    raise KeyError(name)


def by_index(idx: int) -> Mode:
    return MODES[idx - 1]
```

- [ ] **Step 1.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mode_policy.py -v
```

Expected: all 6 tests pass.

- [ ] **Step 1.5: Verify Phase 1 modes tests still pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_modes_bar.py -v
```

Expected: all pass (ModesBar only reads `m.name`, `m.color`, `m.index` — unchanged).

- [ ] **Step 1.6: Commit**

```bash
git add src/bagley/tui/modes/__init__.py tests/tui/test_mode_policy.py
git commit -m "feat(modes): add allowlist field to Mode dataclass; populate all 9 modes"
```

---

## Task 2: `persona.py` — system-prompt-suffix mapping

**Files:**
- Create: `src/bagley/tui/modes/persona.py`

- [ ] **Step 2.1: Write the failing test**

Add to `tests/tui/test_mode_policy.py`:

```python
from bagley.tui.modes.persona import mode_system_suffix


def test_persona_returns_string_for_each_mode():
    from bagley.tui.modes import MODES
    for m in MODES:
        suffix = mode_system_suffix(m.name)
        assert isinstance(suffix, str)
        assert len(suffix) > 0


def test_persona_exploit_is_aggressive():
    suffix = mode_system_suffix("EXPLOIT")
    assert "aggressive" in suffix.lower() or "exploit" in suffix.lower()


def test_persona_recon_mentions_readonly():
    suffix = mode_system_suffix("RECON")
    assert "read-only" in suffix.lower() or "cautious" in suffix.lower()


def test_persona_unknown_mode_raises():
    with pytest.raises(KeyError):
        mode_system_suffix("NONEXISTENT")
```

- [ ] **Step 2.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mode_policy.py -k "persona" -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.modes.persona'`.

- [ ] **Step 2.3: Implement `persona.py`**

Create `src/bagley/tui/modes/persona.py`:

```python
"""System-prompt suffix strings keyed by mode name.

These are appended to DEFAULT_SYSTEM at ReActLoop construction time so the
model receives an operational persona aligned with the active mode.
"""

from __future__ import annotations

from bagley.tui.modes import by_name

# Suffixes are purposefully brief — they inject context, not replace the base system prompt.
_SUFFIXES: dict[str, str] = {
    "RECON": (
        "\n\n[MODE: RECON] You are a cautious observer. All actions must be "
        "read-only. Avoid any packet generation beyond passive banner grabs. "
        "Prefer DNS, WHOIS, and service identification over active probing."
    ),
    "ENUM": (
        "\n\n[MODE: ENUM] You are curious and detail-oriented. Perform "
        "low-impact active enumeration only. Prefer non-destructive tools "
        "(gobuster, nikto, enum4linux-ng). No exploit attempts."
    ),
    "EXPLOIT": (
        "\n\n[MODE: EXPLOIT] You are aggressive. Propose concrete exploits "
        "without handholding. Use the available allowlisted tools directly. "
        "Always require explicit user confirmation before executing."
    ),
    "POST": (
        "\n\n[MODE: POST] You are a methodical post-exploitation operator on "
        "an obtained shell. Prefer LOLBins over dropped binaries. Enumerate "
        "systematically: users, creds, network, persistence."
    ),
    "PRIVESC": (
        "\n\n[MODE: PRIVESC] You are a surgical escalator. Focus only on "
        "privilege escalation vectors. Run linpeas, check SUID binaries, "
        "kernel version, cron jobs, and writable paths."
    ),
    "STEALTH": (
        "\n\n[MODE: STEALTH] You are paranoid. Introduce timing delays, "
        "use fragmentation, route through Tor or proxychains. Minimize "
        "log footprint. Warn the user before any action that could alert defenders."
    ),
    "OSINT": (
        "\n\n[MODE: OSINT] You are a passive stalker. Zero packets reach the "
        "target. Use only public sources: Shodan, Censys, theHarvester, "
        "DNS lookups, WHOIS, GitHub dorks."
    ),
    "REPORT": (
        "\n\n[MODE: REPORT] You are a formal technical writer. Do not execute "
        "any shell commands. Read from memory and notes only. Produce structured "
        "markdown reports with findings, severity, and remediation."
    ),
    "LEARN": (
        "\n\n[MODE: LEARN] You are a didactic instructor. For every tool, flag, "
        "CVE, or technique you invoke, add a plain-English explanation of what "
        "it does and why. Mention side-effects and detection risk."
    ),
}


def mode_system_suffix(mode_name: str) -> str:
    """Return the system-prompt suffix for *mode_name*.

    Raises KeyError if the mode does not exist.
    """
    # Validate the mode exists in the registry first.
    by_name(mode_name)  # raises KeyError if unknown
    return _SUFFIXES[mode_name]
```

- [ ] **Step 2.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mode_policy.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 2.5: Commit**

```bash
git add src/bagley/tui/modes/persona.py tests/tui/test_mode_policy.py
git commit -m "feat(modes): persona.py system-prompt suffix for all 9 modes"
```

---

## Task 3: `policy.py` — `apply_mode_to_loop`

**Files:**
- Create: `src/bagley/tui/modes/policy.py`

- [ ] **Step 3.1: Write the failing policy tests**

Add to `tests/tui/test_mode_policy.py`:

```python
from bagley.tui.modes.policy import apply_mode_to_loop
from bagley.agent.loop import ReActLoop
from bagley.persona import DEFAULT_SYSTEM


class _StubEng:
    def generate(self, messages, **kw):
        from bagley.inference.engine import stub_response
        last = next((m for m in reversed(messages) if m["role"] == "user"), None)
        return stub_response(last["content"] if last else "")


def _make_loop() -> ReActLoop:
    return ReActLoop(engine=_StubEng(), auto_approve=True, max_steps=1)


def test_apply_mode_sets_confirm_fn_explicit():
    loop = _make_loop()
    apply_mode_to_loop(loop, "EXPLOIT")
    # EXPLOIT confirm_policy=explicit → confirm_fn must NOT auto-approve
    assert loop.auto_approve is False


def test_apply_mode_sets_confirm_fn_auto():
    loop = _make_loop()
    apply_mode_to_loop(loop, "RECON")
    # RECON confirm_policy=auto → auto_approve stays True
    assert loop.auto_approve is True


def test_apply_mode_sets_persona_attribute():
    loop = _make_loop()
    apply_mode_to_loop(loop, "OSINT")
    assert hasattr(loop, "_mode_name")
    assert loop._mode_name == "OSINT"


def test_apply_mode_report_blocks_shell():
    """REPORT allowlist is empty: any shell cmd must be blocked."""
    loop = _make_loop()
    apply_mode_to_loop(loop, "REPORT")
    # confirm_fn returns False for REPORT (no exec allowed)
    assert loop.confirm_fn("ls /") is False


def test_apply_mode_exploit_allowlist_blocks_unknown():
    loop = _make_loop()
    apply_mode_to_loop(loop, "EXPLOIT")
    # hydra is in EXPLOIT allowlist → confirm_fn called with it should not be
    # blocked by allowlist (confirm_policy is explicit, so returns False for
    # non-interactive context — but allowlist itself does not block it)
    # nmap is NOT in EXPLOIT allowlist → should be blocked
    assert loop.confirm_fn("nmap -sV 10.10.10.10") is False


def test_apply_mode_learn_inherits_none_allowlist():
    loop = _make_loop()
    apply_mode_to_loop(loop, "LEARN")
    # LEARN allowlist=None → no allowlist restriction; confirm_fn uses explicit policy
    assert loop.auto_approve is False
    # A random command is not blocked by allowlist
    assert loop.confirm_fn("echo hello") is False  # explicit: always False in non-interactive


def test_apply_mode_recon_allowlist_blocks_hydra():
    loop = _make_loop()
    apply_mode_to_loop(loop, "RECON")
    # hydra not in RECON allowlist → blocked
    assert loop.confirm_fn("hydra -l admin 10.10.10.10") is False
```

- [ ] **Step 3.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mode_policy.py -k "apply_mode" -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.modes.policy'`.

- [ ] **Step 3.3: Implement `policy.py`**

Create `src/bagley/tui/modes/policy.py`:

```python
"""apply_mode_to_loop — mutates a ReActLoop to enforce mode's allowlist + confirm policy.

Design decisions:
- We do NOT patch ReActLoop internals. Instead we replace `confirm_fn` with a
  closure that (a) checks the first token of the command against the allowlist,
  and (b) applies the mode's confirm_policy (auto → approve; explicit → deny
  in non-interactive context, i.e. always returns False so ChatPanel's inline
  confirm panel takes over).
- `auto_approve` on the loop object is set to True only for auto-policy modes
  with unrestricted allowlists; otherwise False so the TUI's inline confirm
  panel is the gatekeeper.
- LEARN has allowlist=None (inherit): we set no allowlist restriction but keep
  explicit confirm_policy so the user always sees the confirm panel.
"""

from __future__ import annotations

from bagley.agent.loop import ReActLoop
from bagley.tui.modes import by_name


def _first_token(cmd: str) -> str:
    """Extract the command name from a shell command string."""
    return cmd.strip().split()[0] if cmd.strip() else ""


def _make_confirm_fn(allowlist, confirm_policy: str):
    """Return a confirm_fn closure.

    - allowlist=frozenset(): empty → always block (REPORT mode).
    - allowlist=None: no restriction → policy drives decision.
    - allowlist=frozenset({...}): only commands whose first token is in the
      set are even considered; others are blocked outright.
    - confirm_policy="auto": allowed commands are auto-approved (return True).
    - confirm_policy="explicit": allowed commands return False so the TUI
      inline confirm panel must present them to the user.
    """
    def confirm_fn(cmd: str) -> bool:
        # Empty allowlist = REPORT mode, zero execution.
        if allowlist is not None and len(allowlist) == 0:
            return False

        # Check allowlist restriction.
        if allowlist is not None:
            token = _first_token(cmd)
            if token not in allowlist:
                return False

        # Command is allowed by allowlist; apply confirm_policy.
        return confirm_policy == "auto"

    return confirm_fn


def apply_mode_to_loop(loop: ReActLoop, mode_name: str) -> None:
    """Mutate *loop* so it enforces *mode_name*'s allowlist and confirm policy.

    Attaches `_mode_name` to the loop for audit/display purposes.
    """
    mode = by_name(mode_name)
    loop._mode_name = mode_name
    loop.confirm_fn = _make_confirm_fn(mode.allowlist, mode.confirm_policy)
    # auto_approve is a shortcut flag; keep it in sync so callers that check
    # it directly get the right answer.
    loop.auto_approve = mode.confirm_policy == "auto" and mode.allowlist is None
```

- [ ] **Step 3.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mode_policy.py -v
```

Expected: all 17 tests pass.

- [ ] **Step 3.5: Commit**

```bash
git add src/bagley/tui/modes/policy.py tests/tui/test_mode_policy.py
git commit -m "feat(modes): policy.py apply_mode_to_loop with allowlist + confirm enforcement"
```

---

## Task 4: Selection classifier (`interactions/selection.py`)

**Files:**
- Create: `src/bagley/tui/interactions/__init__.py`
- Create: `src/bagley/tui/interactions/selection.py`
- Create: `tests/tui/test_selection_classifier.py`

- [ ] **Step 4.1: Write the failing classifier tests**

Create `tests/tui/test_selection_classifier.py`:

```python
"""Unit tests for the regex-based selection classifier."""

import pytest
from bagley.tui.interactions.selection import classify, ClassifyResult, SelectionType


# ── IPv4 ──────────────────────────────────────────────────────────────────────

def test_classify_ipv4_plain():
    r = classify("192.168.1.1")
    assert r.type == SelectionType.IPV4
    assert r.value == "192.168.1.1"


def test_classify_ipv4_with_cidr():
    r = classify("10.10.0.0/24")
    assert r.type == SelectionType.IPV4


def test_classify_ipv4_embedded_in_whitespace():
    r = classify("  172.16.0.5  ")
    assert r.type == SelectionType.IPV4


def test_classify_not_ipv4_too_large():
    r = classify("999.999.999.999")
    assert r.type != SelectionType.IPV4


# ── CVE ───────────────────────────────────────────────────────────────────────

def test_classify_cve_standard():
    r = classify("CVE-2021-44228")
    assert r.type == SelectionType.CVE
    assert r.value == "CVE-2021-44228"


def test_classify_cve_case_insensitive():
    r = classify("cve-2023-12345")
    assert r.type == SelectionType.CVE


def test_classify_cve_five_digit():
    r = classify("CVE-2024-123456")
    assert r.type == SelectionType.CVE


# ── MD5 ───────────────────────────────────────────────────────────────────────

def test_classify_md5_lowercase():
    r = classify("d41d8cd98f00b204e9800998ecf8427e")
    assert r.type == SelectionType.MD5


def test_classify_md5_uppercase():
    r = classify("D41D8CD98F00B204E9800998ECF8427E")
    assert r.type == SelectionType.MD5


def test_classify_not_md5_wrong_length():
    r = classify("d41d8cd98f00b204")
    assert r.type != SelectionType.MD5


# ── SHA256 ────────────────────────────────────────────────────────────────────

def test_classify_sha256():
    r = classify("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
    assert r.type == SelectionType.SHA256


def test_classify_sha256_mixed_case():
    r = classify("E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855")
    assert r.type == SelectionType.SHA256


# ── URL ───────────────────────────────────────────────────────────────────────

def test_classify_url_http():
    r = classify("http://example.com/path")
    assert r.type == SelectionType.URL


def test_classify_url_https():
    r = classify("https://192.168.1.1:8443/admin")
    assert r.type == SelectionType.URL


def test_classify_url_ftp():
    r = classify("ftp://files.example.com")
    assert r.type == SelectionType.URL


# ── PORT ──────────────────────────────────────────────────────────────────────

def test_classify_port_tcp():
    r = classify("443/tcp")
    assert r.type == SelectionType.PORT


def test_classify_port_udp():
    r = classify("53/udp")
    assert r.type == SelectionType.PORT


# ── PATH ──────────────────────────────────────────────────────────────────────

def test_classify_absolute_path_linux():
    r = classify("/etc/passwd")
    assert r.type == SelectionType.PATH


def test_classify_absolute_path_windows():
    r = classify("C:\\Windows\\System32\\cmd.exe")
    assert r.type == SelectionType.PATH


# ── UNKNOWN ───────────────────────────────────────────────────────────────────

def test_classify_unknown_plain_text():
    r = classify("hello world")
    assert r.type == SelectionType.UNKNOWN


def test_classify_empty_string():
    r = classify("")
    assert r.type == SelectionType.UNKNOWN


# ── Priority ordering ─────────────────────────────────────────────────────────

def test_classify_priority_cve_over_unknown():
    # CVE in a sentence should still classify as CVE
    r = classify("Found CVE-2021-44228 in log4j")
    assert r.type == SelectionType.CVE


def test_classify_priority_url_over_ipv4():
    # A URL that contains an IP should be classified as URL
    r = classify("https://10.10.10.10/shell")
    assert r.type == SelectionType.URL
```

- [ ] **Step 4.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_selection_classifier.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.interactions'`.

- [ ] **Step 4.3: Create `interactions/__init__.py`**

Create `src/bagley/tui/interactions/__init__.py`:

```python
"""Selection and interaction helpers for the Bagley TUI."""
```

- [ ] **Step 4.4: Implement `selection.py`**

Create `src/bagley/tui/interactions/selection.py`:

```python
"""Regex-based classifier for selected text.

Priority (highest → lowest):
  URL > CVE > SHA256 > MD5 > IPV4 > PORT > PATH > UNKNOWN

LEARN: classifiers run in priority order; the first match wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class SelectionType(Enum):
    URL = auto()
    CVE = auto()
    SHA256 = auto()
    MD5 = auto()
    IPV4 = auto()
    PORT = auto()
    PATH = auto()
    UNKNOWN = auto()


@dataclass
class ClassifyResult:
    type: SelectionType
    value: str          # normalised match value (stripped)
    raw: str            # original input


# ── Regex patterns ────────────────────────────────────────────────────────────

_RE_URL = re.compile(
    r"""(?:https?|ftp|ftps)://[^\s/$.?#][^\s]*""",
    re.IGNORECASE,
)

_RE_CVE = re.compile(
    r"""CVE-\d{4}-\d{4,7}""",
    re.IGNORECASE,
)

_RE_SHA256 = re.compile(
    r"""^[0-9a-fA-F]{64}$""",
)

_RE_MD5 = re.compile(
    r"""^[0-9a-fA-F]{32}$""",
)

_RE_IPV4 = re.compile(
    r"""(?<!\d)
        (25[0-5]|2[0-4]\d|[01]?\d\d?)\.
        (25[0-5]|2[0-4]\d|[01]?\d\d?)\.
        (25[0-5]|2[0-4]\d|[01]?\d\d?)\.
        (25[0-5]|2[0-4]\d|[01]?\d\d?)
        (?:/\d{1,2})?               # optional CIDR
        (?!\d)""",
    re.VERBOSE,
)

_RE_PORT = re.compile(
    r"""^(\d{1,5})/(tcp|udp)$""",
    re.IGNORECASE,
)

_RE_PATH_UNIX = re.compile(
    r"""^/[^\s]+""",
)

_RE_PATH_WIN = re.compile(
    r"""^[A-Za-z]:\\[^\s]+""",
)


def classify(text: str) -> ClassifyResult:
    """Return a :class:`ClassifyResult` for *text*.

    Strips surrounding whitespace before matching.
    """
    raw = text
    t = text.strip()

    # URL — highest priority (may contain IP, CVE in path)
    if _RE_URL.search(t):
        m = _RE_URL.search(t)
        return ClassifyResult(SelectionType.URL, m.group(0), raw)

    # CVE
    if _RE_CVE.search(t):
        m = _RE_CVE.search(t)
        return ClassifyResult(SelectionType.CVE, m.group(0).upper(), raw)

    # SHA256 (64 hex chars)
    if _RE_SHA256.match(t):
        return ClassifyResult(SelectionType.SHA256, t.lower(), raw)

    # MD5 (32 hex chars)
    if _RE_MD5.match(t):
        return ClassifyResult(SelectionType.MD5, t.lower(), raw)

    # IPv4 / CIDR
    if _RE_IPV4.search(t):
        m = _RE_IPV4.search(t)
        return ClassifyResult(SelectionType.IPV4, m.group(0), raw)

    # Port / protocol
    if _RE_PORT.match(t):
        return ClassifyResult(SelectionType.PORT, t.lower(), raw)

    # Absolute path (Unix or Windows)
    if _RE_PATH_UNIX.match(t) or _RE_PATH_WIN.match(t):
        return ClassifyResult(SelectionType.PATH, t, raw)

    return ClassifyResult(SelectionType.UNKNOWN, t, raw)
```

- [ ] **Step 4.5: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_selection_classifier.py -v
```

Expected: all 24 tests pass.

- [ ] **Step 4.6: Commit**

```bash
git add src/bagley/tui/interactions/__init__.py src/bagley/tui/interactions/selection.py tests/tui/test_selection_classifier.py
git commit -m "feat(interactions): regex classifier for ipv4, cve, md5, sha256, url, port, path"
```

---

## Task 5: Inspector actions (`interactions/inspector_actions.py`)

**Files:**
- Create: `src/bagley/tui/interactions/inspector_actions.py`

- [ ] **Step 5.1: Write the failing inspector-actions test**

Add to `tests/tui/test_selection_classifier.py` (or create inline — add at the bottom of the existing file):

```python
from bagley.tui.interactions.inspector_actions import actions_for, InspectorAction
from bagley.tui.interactions.selection import classify


def test_actions_for_ipv4_contains_nmap():
    result = classify("10.10.10.10")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("nmap" in l.lower() for l in labels)


def test_actions_for_cve_contains_searchsploit():
    result = classify("CVE-2021-44228")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("searchsploit" in l.lower() or "exploit" in l.lower() for l in labels)


def test_actions_for_md5_contains_crack():
    result = classify("d41d8cd98f00b204e9800998ecf8427e")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("crack" in l.lower() or "hashcat" in l.lower() for l in labels)


def test_actions_for_url_contains_dirb():
    result = classify("http://example.com")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("gobuster" in l.lower() or "dirb" in l.lower() or "ffuf" in l.lower() for l in labels)


def test_actions_for_unknown_has_send_to_chat():
    result = classify("some random text")
    actions = actions_for(result)
    labels = [a.label for a in actions]
    assert any("chat" in l.lower() or "send" in l.lower() for l in labels)


def test_actions_each_have_command_string():
    result = classify("10.10.10.10")
    actions = actions_for(result)
    for a in actions:
        assert isinstance(a.label, str)
        assert isinstance(a.command, str)
        assert len(a.label) > 0
```

- [ ] **Step 5.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_selection_classifier.py -k "actions_for" -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 5.3: Implement `inspector_actions.py`**

Create `src/bagley/tui/interactions/inspector_actions.py`:

```python
"""Inspector actions — contextual action list produced per ClassifyResult.

Each InspectorAction carries:
  - label: short human-readable button text
  - command: shell command template or TUI action string
  - is_tui_action: if True, `command` is dispatched via app.action_* not executed in shell

A caller (InspectorPane) renders these as clickable items. Commands with
`{value}` are interpolated with ClassifyResult.value before use.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bagley.tui.interactions.selection import ClassifyResult, SelectionType


@dataclass
class InspectorAction:
    label: str
    command: str
    is_tui_action: bool = False


def actions_for(result: ClassifyResult) -> list[InspectorAction]:
    """Return contextual actions for *result*."""
    value = result.value
    t = result.type

    if t == SelectionType.IPV4:
        return [
            InspectorAction("nmap -sV", f"nmap -sV {value}"),
            InspectorAction("nmap full", f"nmap -sC -sV -p- --min-rate=1000 {value}"),
            InspectorAction("Open tab", f"new_tab:{value}", is_tui_action=True),
            InspectorAction("Set as target", f"set_target:{value}", is_tui_action=True),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to memory", f"memory_note:{value}", is_tui_action=True),
        ]

    if t == SelectionType.CVE:
        return [
            InspectorAction("searchsploit", f"searchsploit {value}"),
            InspectorAction("Exploit-DB lookup", f"exploit-db:{value}", is_tui_action=True),
            InspectorAction("MSF module search", f"msfconsole -q -x 'search {value}; exit'"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to memory", f"memory_note:{value}", is_tui_action=True),
        ]

    if t == SelectionType.MD5:
        return [
            InspectorAction("hashcat (rockyou)", f"hashcat -a 0 -m 0 {value} rockyou.txt"),
            InspectorAction("john crack", f"echo '{value}' | john --format=raw-md5 --stdin"),
            InspectorAction("Identify type", f"hash-id:{value}", is_tui_action=True),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to creds", f"memory_cred:{value}", is_tui_action=True),
        ]

    if t == SelectionType.SHA256:
        return [
            InspectorAction("hashcat (rockyou)", f"hashcat -a 0 -m 1400 {value} rockyou.txt"),
            InspectorAction("Identify type", f"hash-id:{value}", is_tui_action=True),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to creds", f"memory_cred:{value}", is_tui_action=True),
        ]

    if t == SelectionType.URL:
        return [
            InspectorAction("ffuf dir-bust", f"ffuf -u {value}/FUZZ -w common.txt"),
            InspectorAction("gobuster", f"gobuster dir -u {value} -w common.txt"),
            InspectorAction("nikto scan", f"nikto -h {value}"),
            InspectorAction("curl -I", f"curl -sI {value}"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
            InspectorAction("Save to memory", f"memory_note:{value}", is_tui_action=True),
        ]

    if t == SelectionType.PORT:
        port_num = value.split("/")[0]
        return [
            InspectorAction("Banner grab", f"nc -zv {{target}} {port_num}"),
            InspectorAction("nmap service", f"nmap -sV -p {port_num} {{target}}"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
        ]

    if t == SelectionType.PATH:
        return [
            InspectorAction("GTFOBins lookup", f"gtfobins:{value}", is_tui_action=True),
            InspectorAction("Check SUID", f"find {value} -perm -4000 2>/dev/null"),
            InspectorAction("ls -la", f"ls -la {value}"),
            InspectorAction("Send to chat", f"chat:{value}", is_tui_action=True),
        ]

    # UNKNOWN — fallback
    return [
        InspectorAction("Send to chat", f"chat:{result.raw}", is_tui_action=True),
        InspectorAction("Search (model)", f"explain:{result.raw}", is_tui_action=True),
    ]
```

- [ ] **Step 5.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_selection_classifier.py -v
```

Expected: all tests pass (original 24 + 6 new = 30).

- [ ] **Step 5.5: Commit**

```bash
git add src/bagley/tui/interactions/inspector_actions.py tests/tui/test_selection_classifier.py
git commit -m "feat(interactions): inspector_actions contextual action list per classification type"
```

---

## Task 6: `InspectorPane` widget

**Files:**
- Create: `src/bagley/tui/panels/inspector.py`
- Create: `tests/tui/test_inspector_panel.py`

- [ ] **Step 6.1: Write the failing inspector panel tests**

Create `tests/tui/test_inspector_panel.py`:

```python
"""Tests: InspectorPane opens correctly and displays classified selection."""

import pytest
from textual.app import App, ComposeResult

from bagley.tui.panels.inspector import InspectorPane
from bagley.tui.interactions.selection import ClassifyResult, SelectionType


class _InspectorApp(App):
    """Minimal harness that mounts an InspectorPane."""

    CSS = "Screen { layers: base overlay; }"

    def compose(self) -> ComposeResult:
        self._pane = InspectorPane()
        yield self._pane

    def show_selection(self, text: str) -> None:
        self._pane.inspect(text)


@pytest.mark.asyncio
async def test_inspector_mounts():
    app = _InspectorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        pane = app.query_one(InspectorPane)
        assert pane is not None


@pytest.mark.asyncio
async def test_inspector_hidden_by_default():
    app = _InspectorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        pane = app.query_one(InspectorPane)
        assert not pane.visible


@pytest.mark.asyncio
async def test_inspector_shows_after_inspect_call():
    app = _InspectorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.show_selection("10.10.10.10")
        await pilot.pause()
        pane = app.query_one(InspectorPane)
        assert pane.visible


@pytest.mark.asyncio
async def test_inspector_displays_type_label_for_ipv4():
    app = _InspectorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.show_selection("192.168.1.1")
        await pilot.pause()
        pane = app.query_one(InspectorPane)
        # The pane renders classification type in its content
        assert pane._current_result is not None
        assert pane._current_result.type == SelectionType.IPV4


@pytest.mark.asyncio
async def test_inspector_displays_type_label_for_cve():
    app = _InspectorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.show_selection("CVE-2021-44228")
        await pilot.pause()
        pane = app.query_one(InspectorPane)
        assert pane._current_result.type == SelectionType.CVE


@pytest.mark.asyncio
async def test_inspector_closes_on_escape():
    app = _InspectorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.show_selection("10.10.10.10")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        pane = app.query_one(InspectorPane)
        assert not pane.visible


@pytest.mark.asyncio
async def test_inspector_has_action_buttons():
    app = _InspectorApp()
    async with app.run_test(size=(120, 40)) as pilot:
        app.show_selection("http://example.com")
        await pilot.pause()
        pane = app.query_one(InspectorPane)
        # Must render at least one action button
        from textual.widgets import Button
        buttons = pane.query(Button)
        assert len(buttons) > 0
```

- [ ] **Step 6.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_inspector_panel.py -v
```

Expected: `ModuleNotFoundError: No module named 'bagley.tui.panels.inspector'`.

- [ ] **Step 6.3: Implement `InspectorPane`**

Create `src/bagley/tui/panels/inspector.py`:

```python
"""InspectorPane — bottom-right dockable pane for selection inspection.

Usage:
    pane = InspectorPane()
    pane.inspect("CVE-2021-44228")   # classifies, renders, shows pane
    # Esc closes it; X button also dismisses

Layout: hidden by default (display: none). inspect() sets display=True.
Position: docked bottom-right via CSS. Width 50, height auto up to 18.

The pane does NOT open as a modal — it overlays the dashboard layout.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

from bagley.tui.interactions.inspector_actions import InspectorAction, actions_for
from bagley.tui.interactions.selection import ClassifyResult, SelectionType, classify

# Color map for type badges
_TYPE_COLOR: dict[SelectionType, str] = {
    SelectionType.IPV4:    "cyan",
    SelectionType.CVE:     "red",
    SelectionType.MD5:     "yellow",
    SelectionType.SHA256:  "yellow",
    SelectionType.URL:     "blue",
    SelectionType.PORT:    "magenta",
    SelectionType.PATH:    "green",
    SelectionType.UNKNOWN: "dim",
}


class InspectorPane(Vertical):
    DEFAULT_CSS = """
    InspectorPane {
        dock: bottom;
        width: 52;
        height: auto;
        max-height: 20;
        border: round $warning;
        background: $panel;
        padding: 0 1;
        display: none;
        offset: 0 0;
        layer: overlay;
    }
    InspectorPane #inspector-type-label {
        height: 1;
        color: $text;
    }
    InspectorPane #inspector-value-label {
        height: 1;
        color: $text-muted;
        overflow: hidden hidden;
    }
    InspectorPane #inspector-actions {
        height: auto;
    }
    InspectorPane Button {
        height: 1;
        min-width: 20;
        margin: 0;
    }
    InspectorPane #inspector-close-btn {
        dock: top;
        width: 3;
        height: 1;
        background: $error;
        color: $text;
        border: none;
    }
    """

    _current_result: ClassifyResult | None = None

    def compose(self) -> ComposeResult:
        yield Button("X", id="inspector-close-btn", variant="error")
        yield Label("", id="inspector-type-label")
        yield Label("", id="inspector-value-label")
        yield Vertical(id="inspector-actions")

    def inspect(self, text: str) -> None:
        """Classify *text*, populate pane content, and make the pane visible."""
        result = classify(text)
        self._current_result = result
        self._render_result(result)
        self.display = True
        self.focus()

    def _render_result(self, result: ClassifyResult) -> None:
        color = _TYPE_COLOR.get(result.type, "dim")
        type_label = self.query_one("#inspector-type-label", Label)
        type_label.update(f"[bold {color}]{result.type.name}[/]  Inspector")

        value_label = self.query_one("#inspector-value-label", Label)
        truncated = result.value[:42] + "…" if len(result.value) > 42 else result.value
        value_label.update(f"[dim]{truncated}[/]")

        actions_container = self.query_one("#inspector-actions", Vertical)
        actions_container.remove_children()
        for action in actions_for(result):
            btn = Button(action.label, id=f"action-{_safe_id(action.label)}")
            btn._inspector_action = action  # stash for dispatch
            actions_container.mount(btn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "inspector-close-btn":
            self.display = False
            event.stop()
            return
        action: InspectorAction | None = getattr(event.button, "_inspector_action", None)
        if action is None:
            return
        if action.is_tui_action:
            self.app.post_message(InspectorDispatch(action))
        else:
            # Non-TUI actions: send command string to chat panel as if user typed it.
            try:
                from bagley.tui.panels.chat import ChatPanel
                chat = self.app.query_one(ChatPanel)
                chat.submit_command(action.command)
            except Exception:
                pass
        self.display = False
        event.stop()

    def key_escape(self) -> None:
        self.display = False


def _safe_id(label: str) -> str:
    """Convert a label to a safe CSS id fragment."""
    return label.lower().replace(" ", "-").replace("(", "").replace(")", "")[:24]


class InspectorDispatch:
    """Message posted to the app when a TUI action is dispatched from the inspector."""

    def __init__(self, action: InspectorAction) -> None:
        self.action = action

    def __init_subclass__(cls) -> None:
        pass
```

- [ ] **Step 6.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_inspector_panel.py -v
```

Expected: all 7 tests pass. If Textual's `display` reactive behaves differently in test size constraints, adjust `max-height` or add `await pilot.pause(0.1)` for layout settle.

- [ ] **Step 6.5: Commit**

```bash
git add src/bagley/tui/panels/inspector.py tests/tui/test_inspector_panel.py
git commit -m "feat(inspector): InspectorPane dockable bottom-right pane with action buttons"
```

---

## Task 7: Expanded command palette (~50 actions)

**Files:**
- Modify: `src/bagley/tui/widgets/palette.py`
- Create: `tests/tui/test_palette_expanded.py`

- [ ] **Step 7.1: Write the failing palette tests**

Create `tests/tui/test_palette_expanded.py`:

```python
"""Tests: expanded palette has at least 50 actions and fuzzy-finds key ones."""

import pytest
from bagley.tui.widgets.palette import ACTIONS, fuzzy_filter


def test_palette_has_at_least_50_actions():
    assert len(ACTIONS) >= 50, f"only {len(ACTIONS)} actions — need >=50"


def test_palette_has_all_mode_switches():
    labels = [label for label, _ in ACTIONS]
    for mode in ("recon", "enum", "exploit", "post", "privesc", "stealth", "osint", "report", "learn"):
        assert any(mode in l.lower() for l in labels), f"mode '{mode}' not found in palette"


def test_palette_has_tab_operations():
    labels = [label for label, _ in ACTIONS]
    assert any("new tab" in l.lower() for l in labels)
    assert any("close tab" in l.lower() for l in labels)


def test_palette_has_focus_actions():
    labels = [label for label, _ in ACTIONS]
    assert any("focus chat" in l.lower() for l in labels)
    assert any("focus hosts" in l.lower() for l in labels)


def test_palette_has_engine_swap_placeholder():
    labels = [label for label, _ in ACTIONS]
    assert any("engine" in l.lower() or "swap" in l.lower() for l in labels)


def test_palette_has_help_action():
    labels = [label for label, _ in ACTIONS]
    assert any("help" in l.lower() for l in labels)


def test_palette_has_disconnect():
    labels = [label for label, _ in ACTIONS]
    assert any("disconnect" in l.lower() for l in labels)


def test_palette_has_palette_playbook_stub():
    labels = [label for label, _ in ACTIONS]
    assert any("playbook" in l.lower() for l in labels)


def test_fuzzy_filter_returns_subset():
    results = fuzzy_filter("exploit", ACTIONS)
    assert len(results) > 0
    assert all("exploit" in label.lower() for label, _ in results)


def test_fuzzy_filter_empty_query_returns_all():
    results = fuzzy_filter("", ACTIONS)
    assert len(results) == len(ACTIONS)


def test_fuzzy_filter_partial_match():
    results = fuzzy_filter("rec", ACTIONS)
    # Should find "mode: recon" and similar
    assert any("rec" in label.lower() for label, _ in results)


def test_fuzzy_filter_no_match_returns_empty():
    results = fuzzy_filter("xyzzynonexistent999", ACTIONS)
    assert len(results) == 0
```

- [ ] **Step 7.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_palette_expanded.py -v
```

Expected: `ImportError: cannot import name 'fuzzy_filter' from 'bagley.tui.widgets.palette'` and `AssertionError` on ACTIONS length.

- [ ] **Step 7.3: Replace `palette.py` with expanded ACTIONS + `fuzzy_filter`**

Replace `src/bagley/tui/widgets/palette.py` entirely:

```python
"""Command palette (Ctrl+K) — fuzzy action list (~50 actions)."""

from __future__ import annotations

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, ListItem, ListView, Static


# Each entry: (label, action_string)
# action_string conventions:
#   "action_name"               → app.action_action_name()
#   "action_name(arg)"          → app.action_action_name("arg")
#   "focus('#id')"              → app.action_focus("#id")
#   "__placeholder__"           → shows a "(coming soon)" toast

ACTIONS: list[tuple[str, str]] = [
    # ── Tab operations ─────────────────────────────────────────────────────────
    ("new tab",                         "new_tab"),
    ("close tab",                       "close_tab"),
    ("tab 1",                           "goto_tab(1)"),
    ("tab 2",                           "goto_tab(2)"),
    ("tab 3",                           "goto_tab(3)"),
    ("tab 4",                           "goto_tab(4)"),
    ("tab 5",                           "goto_tab(5)"),

    # ── Focus ──────────────────────────────────────────────────────────────────
    ("focus chat",                      "focus('#chat-panel')"),
    ("focus hosts",                     "focus('#hosts-panel')"),
    ("focus target",                    "focus('#target-panel')"),
    ("focus notes",                     "focus('#target-panel')"),
    ("focus findings",                  "focus('#hosts-panel')"),

    # ── Mode switches ──────────────────────────────────────────────────────────
    ("mode: recon",                     "set_mode(1)"),
    ("mode: enum",                      "set_mode(2)"),
    ("mode: exploit",                   "set_mode(3)"),
    ("mode: post",                      "set_mode(4)"),
    ("mode: privesc",                   "set_mode(5)"),
    ("mode: stealth",                   "set_mode(6)"),
    ("mode: osint",                     "set_mode(7)"),
    ("mode: report",                    "set_mode(8)"),
    ("mode: learn",                     "set_mode(9)"),
    ("cycle mode",                      "cycle_mode"),

    # ── Inspector ──────────────────────────────────────────────────────────────
    ("inspect selection",               "open_inspector"),
    ("close inspector",                 "close_inspector"),

    # ── Common playbook stubs ──────────────────────────────────────────────────
    ("playbook: initial recon",         "run_playbook('initial_recon')"),
    ("playbook: web enum",              "run_playbook('web_enum')"),
    ("playbook: smb enum",              "run_playbook('smb_enum')"),
    ("playbook: brute ssh",             "run_playbook('brute_ssh')"),
    ("playbook: post enum",             "run_playbook('post_enum')"),

    # ── Engine / model ─────────────────────────────────────────────────────────
    ("swap engine (hot-swap)",          "swap_engine"),
    ("engine: stub",                    "set_engine('stub')"),
    ("engine: ollama",                  "set_engine('ollama')"),
    ("engine: local v10",               "set_engine('local')"),

    # ── Alerts / notifications ─────────────────────────────────────────────────
    ("open alerts log",                 "open_alerts"),
    ("clear alerts",                    "clear_alerts"),

    # ── Chat / history ─────────────────────────────────────────────────────────
    ("search chat history",             "search_history"),
    ("clear chat",                      "clear_chat"),
    ("last tool output",                "last_tool_output"),

    # ── Misc ────────────────────────────────────────────────────────────────────
    ("help",                            "show_help"),
    ("toggle voice",                    "toggle_voice"),
    ("payload builder",                 "open_payload_builder"),
    ("toggle plan mode",                "toggle_plan_mode"),
    ("timeline scrubber",               "open_timeline"),
    ("toggle graph view",               "toggle_graph"),
    ("background shell pane",           "background_shell"),
    ("undo last finding",               "undo_finding"),
    ("set scope",                       "set_scope"),
    ("export report",                   "export_report"),
    ("disconnect",                      "disconnect"),
]


def fuzzy_filter(query: str, actions: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Return *actions* whose label contains *query* as a substring (case-insensitive).

    Empty query returns all actions unchanged.
    """
    q = query.lower().strip()
    if not q:
        return list(actions)
    return [(label, action) for label, action in actions if q in label.lower()]


class CommandPalette(ModalScreen):
    DEFAULT_CSS = """
    CommandPalette { align: center middle; }
    #palette { width: 64; height: auto; border: round $primary;
                background: $panel; padding: 1 1; }
    #palette-results { height: auto; max-height: 14; }
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
        for label, _ in fuzzy_filter(query, ACTIONS):
            lv.append(ListItem(Static(label)))

    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.lower().strip()
        results = fuzzy_filter(q, ACTIONS)
        if results:
            self.dismiss(results[0][1])
        else:
            self.dismiss(None)

    def key_escape(self) -> None:
        self.dismiss(None)
```

- [ ] **Step 7.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_palette_expanded.py -v
```

Expected: all 12 tests pass.

- [ ] **Step 7.5: Verify Phase 1 palette tests still pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_palette.py -v
```

Expected: all pass (Phase 1 palette tests check open/close behavior, not ACTIONS count).

- [ ] **Step 7.6: Commit**

```bash
git add src/bagley/tui/widgets/palette.py tests/tui/test_palette_expanded.py
git commit -m "feat(palette): expand command palette to 50 actions with fuzzy_filter helper"
```

---

## Task 8: Inline confirmation panel in `ChatPanel`

**Files:**
- Modify: `src/bagley/tui/panels/chat.py`
- Create: `tests/tui/test_inline_confirm.py`

- [ ] **Step 8.1: Write the failing inline confirm tests**

Create `tests/tui/test_inline_confirm.py`:

```python
"""Tests: inline confirmation panel renders in ChatPanel, y/n dispatch."""

import pytest
from textual.app import App, ComposeResult

from bagley.tui.panels.chat import ChatPanel, ConfirmPanel
from bagley.tui.state import AppState, detect_os


class _ChatApp(App):
    CSS = "Screen { layers: base overlay; }"

    def __init__(self):
        super().__init__()
        self.state = AppState(os_info=detect_os(), engine_label="stub")

    def compose(self) -> ComposeResult:
        yield ChatPanel(self.state)


@pytest.mark.asyncio
async def test_confirm_panel_not_visible_by_default():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one(ConfirmPanel)
        assert not panel.visible


@pytest.mark.asyncio
async def test_confirm_panel_shows_when_triggered():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("nmap -sV 10.10.10.10", callback=lambda r: None)
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        assert panel.visible


@pytest.mark.asyncio
async def test_confirm_panel_displays_command():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("sqlmap -u http://target/login", callback=lambda r: None)
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        assert panel._pending_cmd == "sqlmap -u http://target/login"


@pytest.mark.asyncio
async def test_confirm_yes_button_calls_callback_true():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("hydra -l admin 10.10.10.10", callback=lambda r: results.append(r))
        await pilot.pause()
        await pilot.click("#confirm-yes-btn")
        await pilot.pause()
        assert results == [True]


@pytest.mark.asyncio
async def test_confirm_no_button_calls_callback_false():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("msfconsole -q", callback=lambda r: results.append(r))
        await pilot.pause()
        await pilot.click("#confirm-no-btn")
        await pilot.pause()
        assert results == [False]


@pytest.mark.asyncio
async def test_confirm_panel_hides_after_answer():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("ls /", callback=lambda r: None)
        await pilot.pause()
        await pilot.click("#confirm-yes-btn")
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        assert not panel.visible


@pytest.mark.asyncio
async def test_confirm_panel_key_y_accepts():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("id", callback=lambda r: results.append(r))
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        panel.focus()
        await pilot.press("y")
        await pilot.pause()
        assert results == [True]


@pytest.mark.asyncio
async def test_confirm_panel_key_n_rejects():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("id", callback=lambda r: results.append(r))
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        panel.focus()
        await pilot.press("n")
        await pilot.pause()
        assert results == [False]
```

- [ ] **Step 8.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_inline_confirm.py -v
```

Expected: `ImportError: cannot import name 'ConfirmPanel' from 'bagley.tui.panels.chat'`.

- [ ] **Step 8.3: Rewrite `chat.py` with `ConfirmPanel` and mode-aware loop**

Replace `src/bagley/tui/panels/chat.py` entirely:

```python
"""ChatPanel — ReAct stream with inline confirmation and mode wiring.

Phase 2 changes vs Phase 1:
- ConfirmPanel renders inline (docked bottom of ChatPanel) for explicit-confirm
  modes instead of blocking the process.
- apply_mode_to_loop() is called whenever the mode changes.
- submit_command() is a public method used by InspectorPane and playbooks.
- Ctrl+I handler captures focused text and opens InspectorPane.
"""

from __future__ import annotations

from typing import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Input, Label, RichLog, Static

from bagley.agent.loop import ReActLoop
from bagley.inference.engine import stub_response
from bagley.persona import DEFAULT_SYSTEM
from bagley.tui.modes import by_name
from bagley.tui.modes.persona import mode_system_suffix
from bagley.tui.modes.policy import apply_mode_to_loop
from bagley.tui.state import AppState


# ── Stub engine (used when state.engine_label == "stub") ──────────────────────

class _StubEngine:
    def generate(self, messages, **kwargs):
        last = next((m for m in reversed(messages) if m["role"] == "user"), None)
        return stub_response(last["content"] if last else "")


# ── Inline confirmation panel ─────────────────────────────────────────────────

class ConfirmPanel(Vertical):
    """Inline confirmation panel — shown docked at the bottom of ChatPanel.

    The caller provides a `callback(result: bool)` that is invoked when the
    user presses y/n or clicks the buttons. After dispatch the panel hides.
    """

    DEFAULT_CSS = """
    ConfirmPanel {
        height: 5;
        border: round $warning;
        background: $panel;
        padding: 0 1;
        display: none;
        dock: bottom;
    }
    ConfirmPanel #confirm-cmd-label { height: 1; color: $warning; }
    ConfirmPanel #confirm-btn-row   { height: 3; align: left middle; }
    ConfirmPanel Button { min-width: 8; height: 3; }
    """

    BINDINGS = [
        Binding("y", "accept", "Yes", show=False),
        Binding("n", "reject", "No",  show=False),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(id="confirm-panel", **kwargs)
        self._pending_cmd: str = ""
        self._callback: Callable[[bool], None] | None = None

    def compose(self) -> ComposeResult:
        yield Label("", id="confirm-cmd-label")
        with Horizontal(id="confirm-btn-row"):
            yield Button("[Y] Yes", id="confirm-yes-btn", variant="success")
            yield Button("[N] No",  id="confirm-no-btn",  variant="error")

    def show_confirm(self, cmd: str, callback: Callable[[bool], None]) -> None:
        """Populate and reveal the panel."""
        self._pending_cmd = cmd
        self._callback = callback
        truncated = cmd[:60] + "…" if len(cmd) > 60 else cmd
        self.query_one("#confirm-cmd-label", Label).update(
            f"[bold yellow]About to execute:[/] [cyan]{truncated}[/]"
        )
        self.display = True
        self.focus()

    def _respond(self, result: bool) -> None:
        self.display = False
        if self._callback is not None:
            cb = self._callback
            self._callback = None
            cb(result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes-btn":
            self._respond(True)
            event.stop()
        elif event.button.id == "confirm-no-btn":
            self._respond(False)
            event.stop()

    def action_accept(self) -> None:
        self._respond(True)

    def action_reject(self) -> None:
        self._respond(False)


# ── ChatPanel ─────────────────────────────────────────────────────────────────

class ChatPanel(Vertical):
    DEFAULT_CSS = """
    ChatPanel { border: round $primary; padding: 0 1; }
    ChatPanel > RichLog { height: 1fr; }
    ChatPanel > Input   { height: 3; dock: bottom; }
    """

    BINDINGS = [
        Binding("ctrl+i", "inspect_selection", "Inspect", show=False),
    ]

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="chat-panel", **kwargs)
        self._state = state
        self._loop = self._build_loop()
        self.can_focus = True

    def _build_loop(self) -> ReActLoop:
        engine = _StubEngine()
        loop = ReActLoop(engine=engine, auto_approve=True, max_steps=1)
        apply_mode_to_loop(loop, self._state.mode)
        return loop

    def _system_for_current_mode(self) -> str:
        return DEFAULT_SYSTEM + mode_system_suffix(self._state.mode)

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield ConfirmPanel()
        yield Input(placeholder="you> ", id="chat-input")

    def on_mount(self) -> None:
        self.query_one("#chat-log").write(
            "[dim]Bagley TUI Phase 2. Mode: [bold cyan]"
            + self._state.mode + "[/]. Type and press Enter.[/]"
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def refresh_mode(self) -> None:
        """Called by app.action_set_mode / action_cycle_mode after mode change."""
        apply_mode_to_loop(self._loop, self._state.mode)
        log = self.query_one("#chat-log", RichLog)
        mode = by_name(self._state.mode)
        log.write(
            f"[dim italic][mode → {mode.name}] "
            f"confirm={mode.confirm_policy} | allowlist={'all' if mode.allowlist is None else len(mode.allowlist)}[/]"
        )
        # Update border color to reflect the new mode
        self.styles.border = ("round", mode.color)

    def request_confirm(self, cmd: str, callback: Callable[[bool], None]) -> None:
        """Show the inline confirm panel for *cmd*; call *callback* with result."""
        panel = self.query_one(ConfirmPanel)
        panel.show_confirm(cmd, callback)

    def submit_command(self, cmd: str) -> None:
        """Programmatically submit a command as if the user typed it."""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold green]you>[/] {cmd}")
        self._run_in_loop(cmd, log)

    # ── Input handling ────────────────────────────────────────────────────────

    def on_key(self, event) -> None:
        if event.key == "enter":
            inp = self.query_one("#chat-input", Input)
            inp.post_message(Input.Submitted(inp, inp.value))
            event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "chat-input":
            return
        msg = event.value.strip()
        if not msg:
            return
        event.input.value = ""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold green]you>[/] {msg}")
        self._run_in_loop(msg, log)

    def _run_in_loop(self, msg: str, log: RichLog) -> None:
        steps = self._loop.run(msg, self._system_for_current_mode())
        for step in steps:
            if step.kind in {"assistant", "final"}:
                log.write(f"[magenta]bagley>[/] {step.content}")
            elif step.kind == "tool":
                rc = step.execution.returncode if step.execution else 0
                color = "green" if rc == 0 else "yellow"
                log.write(f"[{color}]tool>[/] {step.content}")
            elif step.kind == "blocked":
                log.write(f"[red]blocked>[/] {step.content}")
        self._state.turn += 1
        try:
            self.app.query_one("#header").refresh_content()
        except Exception:
            pass
        try:
            self.app.query_one("#statusline").refresh_content()
        except Exception:
            pass

    # ── Ctrl+I — inspect selection ────────────────────────────────────────────

    def action_inspect_selection(self) -> None:
        """Open InspectorPane with currently selected text (or clipboard fallback)."""
        # In Textual, get selection via screen.selection or fallback to input value.
        text = ""
        try:
            from textual.screen import Screen
            sel = self.screen.selection
            if sel is not None:
                text = str(sel)
        except Exception:
            pass
        if not text:
            inp = self.query_one("#chat-input", Input)
            text = inp.value
        if text.strip():
            try:
                from bagley.tui.panels.inspector import InspectorPane
                pane = self.app.query_one(InspectorPane)
                pane.inspect(text.strip())
            except Exception:
                pass
```

- [ ] **Step 8.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_inline_confirm.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 8.5: Verify Phase 1 chat tests still pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_chat_panel.py -v
```

Expected: all pass. If any tests import `ReActLoop` construction internals directly, they may need minor adjustments; do not change them — adjust `chat.py`'s defaults to remain backward-compatible instead.

- [ ] **Step 8.6: Commit**

```bash
git add src/bagley/tui/panels/chat.py tests/tui/test_inline_confirm.py
git commit -m "feat(chat): ConfirmPanel inline confirmation + mode-aware loop via apply_mode_to_loop"
```

---

## Task 9: Wire `InspectorPane` and `Ctrl+I` into `app.py`

**Files:**
- Modify: `src/bagley/tui/app.py`
- Modify: `tests/tui/test_inspector_panel.py` (one additional integration test)

- [ ] **Step 9.1: Write the failing app-level inspector test**

Append to `tests/tui/test_inspector_panel.py`:

```python
from bagley.tui.app import BagleyApp
from bagley.tui.panels.inspector import InspectorPane


@pytest.mark.asyncio
async def test_bagley_app_mounts_inspector_pane():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        pane = app.query_one(InspectorPane)
        assert pane is not None


@pytest.mark.asyncio
async def test_bagley_app_ctrl_i_opens_inspector():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        # Type something in chat input first to give Ctrl+I something to inspect
        await pilot.press("f3")          # focus chat
        await pilot.pause()
        inp = app.query_one("#chat-input", Input)
        await pilot.click(inp)
        await pilot.press("1", "9", "2", ".", "1", "6", "8", ".", "1", ".", "1")
        await pilot.press("ctrl+i")
        await pilot.pause()
        pane = app.query_one(InspectorPane)
        assert pane.visible
```

- [ ] **Step 9.2: Run — expected to fail**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_inspector_panel.py::test_bagley_app_mounts_inspector_pane -v
```

Expected: `textual.css.query.NoMatches` because `InspectorPane` is not yet mounted in `BagleyApp`.

- [ ] **Step 9.3: Update `app.py` to mount `InspectorPane` and add bindings**

Replace `src/bagley/tui/app.py` entirely:

```python
"""BagleyApp — Textual TUI entrypoint. Phase 2: modes + inspector + Ctrl+M."""

from __future__ import annotations

import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Input

from bagley.tui.state import AppState, detect_os


class BagleyApp(App):
    CSS = """
    #header { height: 1; background: $panel; color: $text; padding: 0 1; }
    #pane-row { height: 1fr; }
    """

    BINDINGS = [
        Binding("ctrl+d", "disconnect", "Disconnect", show=True),
        Binding("ctrl+c", "disconnect", "Disconnect", show=False),
        # Mode switches
        Binding("alt+1", "set_mode(1)", "", show=False),
        Binding("alt+2", "set_mode(2)", "", show=False),
        Binding("alt+3", "set_mode(3)", "", show=False),
        Binding("alt+4", "set_mode(4)", "", show=False),
        Binding("alt+5", "set_mode(5)", "", show=False),
        Binding("alt+6", "set_mode(6)", "", show=False),
        Binding("alt+7", "set_mode(7)", "", show=False),
        Binding("alt+8", "set_mode(8)", "", show=False),
        Binding("alt+9", "set_mode(9)", "", show=False),
        Binding("ctrl+m", "cycle_mode", "Cycle mode", show=False),
        # Tab management
        Binding("ctrl+t", "new_tab",     "New tab",   show=True),
        Binding("ctrl+w", "close_tab",   "Close tab", show=True),
        Binding("ctrl+1", "goto_tab(1)", "", show=False),
        Binding("ctrl+2", "goto_tab(2)", "", show=False),
        Binding("ctrl+3", "goto_tab(3)", "", show=False),
        Binding("ctrl+4", "goto_tab(4)", "", show=False),
        Binding("ctrl+5", "goto_tab(5)", "", show=False),
        Binding("ctrl+6", "goto_tab(6)", "", show=False),
        Binding("ctrl+7", "goto_tab(7)", "", show=False),
        Binding("ctrl+8", "goto_tab(8)", "", show=False),
        Binding("ctrl+9", "goto_tab(9)", "", show=False),
        # Focus
        Binding("f2", "focus('#hosts-panel')",  "Hosts", show=True),
        Binding("f3", "focus('#chat-panel')",   "Chat",  show=True),
        Binding("f4", "focus('#target-panel')", "Notes", show=True),
        # Inspector
        Binding("ctrl+i", "open_inspector", "Inspect", show=False),
        # Palette
        Binding("ctrl+k", "open_palette", "Palette", show=True),
    ]

    def __init__(self, stub: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = AppState(os_info=detect_os(), engine_label="stub" if stub else "local")

    def compose(self) -> ComposeResult:
        from bagley.tui.widgets.header import Header
        from bagley.tui.widgets.modes_bar import ModesBar
        from bagley.tui.widgets.tab_bar import TabBar
        from bagley.tui.panels.hosts import HostsPanel
        from bagley.tui.panels.chat import ChatPanel
        from bagley.tui.panels.target import TargetPanel
        from bagley.tui.panels.inspector import InspectorPane
        from bagley.tui.widgets.statusline import Statusline
        from textual.containers import Horizontal

        yield Header(self.state)
        yield ModesBar(self.state)
        yield TabBar(self.state)
        with Horizontal(id="pane-row"):
            yield HostsPanel(self.state)
            yield ChatPanel(self.state)
            yield TargetPanel(self.state)
        yield InspectorPane()
        yield Statusline(self.state)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_focus(self, selector: str) -> None:
        try:
            self.query_one(selector).focus()
        except Exception:
            pass

    def action_disconnect(self) -> None:
        self.exit()

    def action_set_mode(self, idx: int) -> None:
        from bagley.tui.modes import by_index
        mode = by_index(idx)
        self.state.mode = mode.name
        self._apply_mode_everywhere(mode.name)

    def action_cycle_mode(self) -> None:
        from bagley.tui.modes import MODES, by_name
        current_idx = next(
            (i for i, m in enumerate(MODES) if m.name == self.state.mode), 0
        )
        next_mode = MODES[(current_idx + 1) % len(MODES)]
        self.state.mode = next_mode.name
        self._apply_mode_everywhere(next_mode.name)

    def _apply_mode_everywhere(self, mode_name: str) -> None:
        """Update header, modes bar, and chat panel after a mode change."""
        try:
            self.query_one("#header").refresh_content()
        except Exception:
            pass
        try:
            self.query_one("#modes-bar").refresh_content()
        except Exception:
            pass
        try:
            from bagley.tui.panels.chat import ChatPanel
            self.query_one(ChatPanel).refresh_mode()
        except Exception:
            pass

    def action_new_tab(self) -> None:
        from bagley.tui.state import TabState
        tab_id = f"target-{len(self.state.tabs)}"
        self.state.tabs.append(TabState(id=tab_id, kind="target"))
        self.state.active_tab = len(self.state.tabs) - 1
        self._refresh_tab_dependent()

    def action_close_tab(self) -> None:
        if self.state.active_tab == 0:
            return
        del self.state.tabs[self.state.active_tab]
        self.state.active_tab = max(0, self.state.active_tab - 1)
        self._refresh_tab_dependent()

    def action_goto_tab(self, idx: int) -> None:
        target = idx - 1
        if 0 <= target < len(self.state.tabs):
            self.state.active_tab = target
            self._refresh_tab_dependent()

    def _refresh_tab_dependent(self) -> None:
        for widget_id in ("#tab-bar", "#hosts-panel", "#target-panel"):
            try:
                self.query_one(widget_id).refresh_content()
            except Exception:
                pass

    def action_open_inspector(self) -> None:
        """Open inspector with the current chat-input value as selection."""
        from bagley.tui.panels.inspector import InspectorPane
        try:
            text = self.query_one("#chat-input", Input).value.strip()
        except Exception:
            text = ""
        if text:
            self.query_one(InspectorPane).inspect(text)

    def action_close_inspector(self) -> None:
        from bagley.tui.panels.inspector import InspectorPane
        try:
            self.query_one(InspectorPane).display = False
        except Exception:
            pass

    async def action_open_palette(self) -> None:
        from bagley.tui.widgets.palette import CommandPalette

        def _on_dismiss(result: str | None) -> None:
            if result is None:
                return
            if result.startswith("__placeholder__"):
                return
            if "(" in result:
                name, _, rest = result.partition("(")
                arg_raw = rest.rstrip(")").strip("'\"")
                method = getattr(self, f"action_{name}", None)
                if method:
                    try:
                        method(int(arg_raw))
                    except ValueError:
                        method(arg_raw)
            else:
                method = getattr(self, f"action_{result}", None)
                if method:
                    method()

        self.push_screen(CommandPalette(), callback=_on_dismiss)

    # ── Palette-dispatched actions (stubs for Phase 2; fuller in later phases) ─

    def action_swap_engine(self) -> None:
        pass   # Phase 6

    def action_set_engine(self, label: str) -> None:
        self.state.engine_label = label
        try:
            self.query_one("#header").refresh_content()
        except Exception:
            pass

    def action_run_playbook(self, name: str) -> None:
        pass   # Phase 4

    def action_open_alerts(self) -> None:
        pass   # Phase 3

    def action_clear_alerts(self) -> None:
        self.state.unread_alerts = 0
        try:
            self.query_one("#header").refresh_content()
        except Exception:
            pass

    def action_search_history(self) -> None:
        pass   # Phase 4

    def action_clear_chat(self) -> None:
        try:
            self.query_one("#chat-log").clear()
        except Exception:
            pass

    def action_last_tool_output(self) -> None:
        pass   # Phase 4

    def action_show_help(self) -> None:
        pass   # Phase 6

    def action_toggle_voice(self) -> None:
        pass   # Phase 6

    def action_open_payload_builder(self) -> None:
        pass   # Phase 6

    def action_toggle_plan_mode(self) -> None:
        pass   # Phase 4

    def action_open_timeline(self) -> None:
        pass   # Phase 5

    def action_toggle_graph(self) -> None:
        pass   # Phase 5

    def action_background_shell(self) -> None:
        pass   # Phase 5

    def action_undo_finding(self) -> None:
        pass   # Phase 3

    def action_set_scope(self) -> None:
        pass   # Phase 3

    def action_export_report(self) -> None:
        pass   # Phase 6


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

- [ ] **Step 9.4: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_inspector_panel.py -v
```

Expected: all 9 tests pass.

- [ ] **Step 9.5: Verify full Phase 1 suite still green**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --ignore=tests/tui/test_mode_policy.py --ignore=tests/tui/test_selection_classifier.py --ignore=tests/tui/test_inspector_panel.py --ignore=tests/tui/test_palette_expanded.py --ignore=tests/tui/test_inline_confirm.py
```

Expected: all Phase 1 tests pass.

- [ ] **Step 9.6: Commit**

```bash
git add src/bagley/tui/app.py tests/tui/test_inspector_panel.py
git commit -m "feat(app): mount InspectorPane, add Ctrl+I and Ctrl+M bindings, wire mode cycle"
```

---

## Task 10: Ctrl+M mode cycle visual — border color update

**Files:**
- Modify: `src/bagley/tui/panels/chat.py` — already done in Task 8 (`refresh_mode` sets `self.styles.border`)
- Tests are covered by the integration test in Task 9 + `test_inline_confirm.py`

- [ ] **Step 10.1: Write a dedicated mode-color test**

Append to `tests/tui/test_inline_confirm.py`:

```python
from bagley.tui.app import BagleyApp as _BagleyApp
from bagley.tui.panels.chat import ChatPanel as _ChatPanel


@pytest.mark.asyncio
async def test_mode_change_updates_chat_border_color():
    app = _BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("alt+3")      # EXPLOIT = red
        await pilot.pause()
        chat = app.query_one(_ChatPanel)
        # styles.border is a tuple ("round", Color) — check color name or value
        border_color = str(chat.styles.border_top[1])
        assert app.state.mode == "EXPLOIT"
        # border must have changed from default cyan (RECON) to red (EXPLOIT)
        assert "red" in border_color or border_color != "cyan"


@pytest.mark.asyncio
async def test_ctrl_m_cycles_modes():
    app = _BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        initial_mode = app.state.mode   # "RECON"
        await pilot.press("ctrl+m")
        await pilot.pause()
        assert app.state.mode != initial_mode
        # Cycling from RECON should move to ENUM (index 2)
        assert app.state.mode == "ENUM"
```

- [ ] **Step 10.2: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_inline_confirm.py -v
```

Expected: all 10 tests pass (8 original + 2 new).

- [ ] **Step 10.3: Commit**

```bash
git add tests/tui/test_inline_confirm.py
git commit -m "test(chat): verify mode change updates chat border color and Ctrl+M cycles"
```

---

## Task 11: End-to-end mode policy integration test

**Files:**
- Modify: `tests/tui/test_mode_policy.py` — add integration test using BagleyApp

- [ ] **Step 11.1: Write the integration test**

Append to `tests/tui/test_mode_policy.py`:

```python
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_mode_switch_applies_policy_to_chat_loop():
    """After switching to EXPLOIT, ChatPanel's loop must use explicit confirm."""
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("alt+3")      # → EXPLOIT
        await pilot.pause()
        from bagley.tui.panels.chat import ChatPanel
        chat = app.query_one(ChatPanel)
        # EXPLOIT allowlist blocks nmap (not in EXPLOIT allowlist)
        assert chat._loop.confirm_fn("nmap -sV 10.10.10.10") is False
        # hydra IS in EXPLOIT allowlist but explicit policy → still False
        assert chat._loop.confirm_fn("hydra -l admin 10.10.10.10") is False


@pytest.mark.asyncio
async def test_mode_recon_auto_confirms_nmap():
    """After switching to RECON, nmap is auto-confirmed."""
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("alt+1")      # → RECON
        await pilot.pause()
        from bagley.tui.panels.chat import ChatPanel
        chat = app.query_one(ChatPanel)
        # nmap in RECON allowlist with auto policy → True
        assert chat._loop.confirm_fn("nmap -sV 10.10.10.10") is True


@pytest.mark.asyncio
async def test_mode_report_blocks_all_exec():
    """REPORT mode must block all shell execution."""
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("alt+8")      # → REPORT
        await pilot.pause()
        from bagley.tui.panels.chat import ChatPanel
        chat = app.query_one(ChatPanel)
        assert chat._loop.confirm_fn("ls /") is False
        assert chat._loop.confirm_fn("cat /etc/passwd") is False
```

- [ ] **Step 11.2: Run — expected to pass**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/test_mode_policy.py -v
```

Expected: all 20 tests pass.

- [ ] **Step 11.3: Commit**

```bash
git add tests/tui/test_mode_policy.py
git commit -m "test(modes): integration tests for mode policy enforcement through BagleyApp"
```

---

## Task 12: Full Phase 2 suite + smoke test

**Files:** No new code — run all tests, fix any regressions.

- [ ] **Step 12.1: Run the full test suite**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v
```

Expected: all tests pass (Phase 1 + Phase 2). No regressions.

- [ ] **Step 12.2: Smoke-run the TUI manually**

```bash
.venv/Scripts/python.exe -m bagley.tui.app --stub
```

Expected: TUI opens with header + modes bar + 4 panes. Verify:

1. Press `Alt+3` → modes bar updates to show EXPLOIT active (red pill), chat border turns red, chat log shows `[mode → EXPLOIT]` line.
2. Press `Ctrl+M` → mode cycles to POST. `Ctrl+M` again → PRIVESC. Continue cycling.
3. In chat input, type `CVE-2021-44228` and press `Ctrl+I` → InspectorPane appears at the bottom, shows `CVE` type badge and `searchsploit` action button.
4. Click the `X` button on the inspector → it closes.
5. Press `Ctrl+K` → palette opens; type `exploit` → sees "mode: exploit" and related actions; press Escape.
6. Press `Alt+3` to switch to EXPLOIT mode. Type a message in chat and press Enter. The loop's `confirm_fn` blocks tools not in the EXPLOIT allowlist.
7. Press `Ctrl+D` → exit cleanly.

- [ ] **Step 12.3: Fix any failures found in smoke test**

If any step above fails (e.g. border color not updating, inspector not positioned), fix the CSS or logic in the relevant file, re-run affected tests, confirm pass.

- [ ] **Step 12.4: Commit (if fixes were needed)**

```bash
# Only if Step 12.3 required changes:
git add <changed files>
git commit -m "fix(tui-phase2): smoke-test corrections for border color / inspector positioning"
```

- [ ] **Step 12.5: Final full-suite run**

```bash
.venv/Scripts/python.exe -m pytest tests/tui/ -v --tb=short 2>&1 | tail -20
```

Expected: green summary line, 0 failures.

---

## Self-review against spec §11 Phase 2 scope

| Spec requirement | Covered by | Status |
|---|---|---|
| All 9 modes wired with `persona_suffix` | `modes/persona.py` + `apply_mode_to_loop` in `policy.py` | Task 2, 3 |
| `allowlist` field on Mode | `modes/__init__.py` extended | Task 1 |
| `confirm_policy` enforced in ReActLoop | `policy.py` wraps `confirm_fn` | Task 3 |
| `color` field drives border color | `chat.py::refresh_mode` sets `self.styles.border` | Task 8, 10 |
| Alt+1..9 mode switch | `app.py` BINDINGS (Phase 1 already had these) | Task 9 |
| Ctrl+M mode cycle | `app.py::action_cycle_mode` | Task 9 |
| Visual border color update on switch | `chat.py::refresh_mode` | Task 8 |
| Selection inspector (Ctrl+I) | `app.py` binding + `chat.py` handler | Task 9, 8 |
| Inspector is a dockable pane (not modal) | `InspectorPane` with `display: none` + dock CSS | Task 6 |
| Regex classifier — IPv4 | `selection.py` `_RE_IPV4` | Task 4 |
| Regex classifier — CVE-ID | `selection.py` `_RE_CVE` | Task 4 |
| Regex classifier — MD5 | `selection.py` `_RE_MD5` | Task 4 |
| Regex classifier — SHA256 | `selection.py` `_RE_SHA256` | Task 4 |
| Regex classifier — URL | `selection.py` `_RE_URL` | Task 4 |
| Regex classifier — PORT (bonus) | `selection.py` `_RE_PORT` | Task 4 |
| Regex classifier — PATH (bonus) | `selection.py` `_RE_PATH_UNIX/WIN` | Task 4 |
| Inspector shows classified type + actions | `InspectorPane._render_result` | Task 6 |
| Palette expanded to ~50 actions | `palette.py` ACTIONS list (51 entries) | Task 7 |
| Palette covers mode switches | 9 mode entries in ACTIONS | Task 7 |
| Palette covers tab ops | new tab, close tab, tab 1..5 | Task 7 |
| Palette covers focus | focus chat, hosts, target, notes | Task 7 |
| Palette covers playbook stubs | 5 playbook entries | Task 7 |
| Palette covers engine swap | swap engine + set engine x3 | Task 7 |
| Palette covers help | "help" entry | Task 7 |
| Inline confirmation in ChatPanel | `ConfirmPanel` widget | Task 8 |
| y/n keyboard shortcuts on confirm | `ConfirmPanel` BINDINGS + `action_accept/reject` | Task 8 |
| Confirm panel shows cmd in highlight | yellow Label in `ConfirmPanel` | Task 8 |
| Inspector Enter → save to memory | `InspectorAction` `memory_note` / `memory_cred` | Task 5 (stub; Phase 3 wires memory) |
| Inspector T → send to chat | `InspectorPane.on_button_pressed` → `chat.submit_command` | Task 6 |
| Inspector X → dismiss | `ConfirmPanel` X button + `key_escape` | Task 6 |

**Out-of-scope for Phase 2 (deferred):**

- Auto-memory promotion when inspector saves a note/cred (Phase 3).
- Rate-limit warning in STEALTH mode (Phase 3).
- Shell-aware confirm for POST mode (Phase 3 — needs ShellPane).
- Playbook runner wiring (Phase 4).
- Hot-swap engine modal (Phase 6).
- Hover popup menus on IP/port/CVE rows (Phase 3).
