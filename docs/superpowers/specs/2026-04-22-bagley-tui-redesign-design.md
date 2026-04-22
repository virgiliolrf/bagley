# Bagley TUI Redesign — Design Spec

**Date:** 2026-04-22
**Status:** Draft, pending user review
**Author:** brainstorm session (Virgilio + Bagley)
**Target deploy:** Kali Linux (primary), macOS/Windows (dev fallback)

---

## 1. Goal

Replace the current Rich-based single-pane REPL (`src/bagley/agent/cli.py`) with a full Textual TUI that integrates Bagley deeply into the ethical-hacker workflow — multi-target tabs, operational modes, selection-to-analyze inspector, plan mode, persistent shell sessions, smart paste, playbooks, timeline scrubber, voice hooks, auto-memory, and a network graph view.

The new interface should feel closer to a dedicated hacking cockpit than a chatbot. The model stays the same (Foundation-Sec-8B + QLoRA adapter via `LocalEngine`/`OllamaEngine`); the change is purely host-side UX.

## 2. Non-goals

- No web UI, no mobile. Terminal only, runs over SSH.
- No change to training, inference, or tool execution layer (`executor.py`, `loop.py`, engines).
- No multi-user collaboration. Single-operator.
- No new model features — existing `ReActLoop` is the backbone.
- No proprietary plugin system. Playbooks are plain YAML, nothing more.

## 3. Architecture

```
┌── Textual App (bagley.tui.app.BagleyApp) ──────────────────────────────┐
│                                                                         │
│  Header (OS · scope · mode badge · voice · alerts-counter)              │
│  Modes bar (RECON/ENUM/EXPLOIT/POST/PRIVESC/STEALTH/OSINT/REPORT/LEARN) │
│  Tab bar (recon · <host1> · <host2> · + )                               │
│                                                                         │
│  ┌─ Active Tab (Dashboard or ReconOverview) ────────────────────────┐   │
│  │  ┌─ HostsPanel ──┐ ┌─ ChatPanel ──────────┐ ┌─ TargetPanel ──┐   │   │
│  │  │ hosts/ports/  │ │ ReAct stream         │ │ target info,  │   │   │
│  │  │ findings      │ │ plan mode overlay    │ │ kill-chain,   │   │   │
│  │  │               │ │ confirmation inline  │ │ creds, notes  │   │   │
│  │  └───────────────┘ └──────────────────────┘ └───────────────┘   │   │
│  │  Optional: ShellPane (live), InspectorPane (right-bottom),       │   │
│  │            PayloadPane (Alt+Y), GraphPane (F7)                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Footer (keybinds hint · turn counter · model indicator)                │
│  Toast overlay (slide-in bottom-right)                                  │
│  Command palette (Ctrl+K modal)                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**New package layout:**

```
src/bagley/tui/
    __init__.py
    app.py              # BagleyApp — root Textual app
    state.py            # AppState, TabState (in-memory + SQLite sync)
    panels/
        hosts.py        # HostsPanel
        chat.py         # ChatPanel (ReAct stream + plan mode overlay)
        target.py       # TargetPanel (info + kill-chain + creds + notes)
        shell.py        # ShellPane (persistent PTY wrapper)
        inspector.py    # InspectorPane (selection-to-analyze)
        graph.py        # GraphPane (F7 network map)
        payload.py      # PayloadPane (Alt+Y builder)
    widgets/
        modes_bar.py
        tab_bar.py
        statusline.py
        toast.py
        palette.py
        timeline.py
        rings.py        # progress rings, minimap, severity bars
    interactions/
        selection.py    # drag-select detect, regex classify
        mentions.py     # @ autocomplete
        bang.py         # !! !N !prefix history
        smart_paste.py  # paste parser (nmap/shodan/pcap/hash/cve/url/ip)
    modes/
        __init__.py     # Mode registry
        recon.py        # per-mode: allowlist, confirm policy, prompt suffix, color
        enum.py
        exploit.py
        post.py
        privesc.py
        stealth.py
        osint.py
        report.py
        learn.py
    playbooks/
        loader.py       # parse .playbooks/*.yml
        runner.py       # execute step sequence with ReAct gaps
    observe/
        attach.py       # /observe pid N — consume external terminal
    report/
        generator.py    # mode=REPORT: notes + memory → markdown/PDF
```

The existing `src/bagley/agent/cli.py` stays as a fallback REPL (`bagley --simple`); the new TUI becomes the default `bagley` entrypoint.

## 4. Layout spec

### 4.1 Tab model

- **Recon tab (tab 0)** — global overview of the full scope. Lists every host known, with per-host one-line summary (IP, state, open ports count, findings count). Hover/click a host opens a target tab (reuses existing one if already open).
- **Target tabs** — one per active target IP. Each owns isolated state: chat history, ReAct context, creds, notes, kill-chain progression.
- **Max open tabs:** 10. Closing a tab archives its state to SQLite (not deleted); reopen via palette.
- **Keyboard:** Ctrl+T new, Ctrl+W close, Ctrl+1..9 jump, Ctrl+Tab cycle.

### 4.2 Dashboard (target tab) — 4-pane

**Left column (170 cols):**
- `HostsPanel` sections stacked: **Hosts** (scope), **Ports** (this target), **Findings** (severity-sorted).
- Each row is hoverable; hover shows a popup menu (see §6.1).

**Center (flex):**
- `ChatPanel` — ReAct stream.
- Assistant messages in magenta, tool calls in blue-bordered panel with `Syntax` highlight, tool output in green (ok) or yellow (non-zero exit) or red (blocked).
- Confirmation prompt renders inline yellow panel "about to execute" — user types `y`/`n` or clicks buttons.
- Plan mode (Alt+P) overlays chat with the plan tree; chat is dimmed until plan resolved.

**Right column (180 cols):**
- `TargetPanel` sections stacked: **Target** (IP, OS, uptime), **Kill-chain** (recon → enum → exploit → postex → privesc → persist → cleanup with current-step marker), **Creds** (list), **Notes** (markdown editable).

**Optional overlay panes:**
- `InspectorPane` — opens bottom-right when user inspects a selection (§6.2). 240 cols wide. Esc closes.
- `ShellPane` — opens full-height right-side or bottom when a persistent shell is spawned (§6.3). Ctrl+B backgrounds.
- `GraphPane` — F7 toggles full-screen graph view (§6.15).
- `PayloadPane` — Alt+Y modal, 60x20, quick payload builder.

### 4.3 Recon tab layout

Same 4-pane skeleton but ChatPanel is scope-wide (not tied to a single host), and TargetPanel right shows scope summary: total hosts up/down, heatmap minimap of the subnet, aggregate findings count per severity.

### 4.4 Header / footer

- **Header:** `▎Bagley · <os> · scope=<cidrs> · ◉ <MODE> · 🎤 voice=<off|listen|active> · 🔔 <N>`
- **Modes bar:** 9 pills, active mode colored, others dim. Alt+1..9 to switch, Ctrl+M to cycle.
- **Tab bar:** below modes bar.
- **Footer:** `turn N/max · model=<v10-modal|ollama|stub> · F1 help · Ctrl+K palette · Ctrl+D disconnect`.

## 5. Modes

| # | Mode | Persona hint (prompt suffix) | Tool allowlist | Confirm | Color |
|---|---|---|---|---|---|
| 1 | RECON | "Cautious observer. Read-only. No packets that touch the target beyond banner grabs." | nmap -sS/-sV, dig, whois, traceroute, masscan | auto-confirm | cyan |
| 2 | ENUM | "Curious, detail-oriented. Low-impact active enumeration." | gobuster, ffuf, nikto, enum4linux-ng, smbmap, ssh-audit | auto-confirm | orange |
| 3 | EXPLOIT | "Aggressive. Proposes exploits. No handholding." | sqlmap, msfconsole, hydra, medusa, exploit-db | **explicit [y/N] always** | red |
| 4 | POST | "Methodical looter on a shell. Prefer LOLBins." | linpeas, winpeas, mimikatz, lazagne, file/dir enum | explicit + shell-aware | magenta |
| 5 | PRIVESC | "Surgical escalator." | linpeas, kernel-exploit-suggester, pspy, GTFOBins lookups | explicit | orange-red |
| 6 | STEALTH | "Paranoid. Delays. Fragmentation. Tor/proxychains." | nmap -T0 -f, proxychains, tor | explicit + rate-limit warning | dim gray |
| 7 | OSINT | "Passive stalker. No packets to target." | shodan, censys, hibp, github-dorks, theHarvester, dnsenum | auto-confirm (zero impact) | green |
| 8 | REPORT | "Formal writer. No exec." | no shell exec; SQLite read-only + markdown generation | auto-confirm read-only | white |
| 9 | LEARN | "Didactic. Explain every flag, CVE, and side effect." | any (inherits active mode's allowlist) + explanatory prose | explicit + explanation | soft-cyan |

**How modes take effect:**

- Each mode module exports `system_suffix: str`, `allowlist: set[str]`, `confirm_policy: str`, `color: str`, `safeguard_overrides: dict`.
- `ReActLoop` constructor accepts `mode: Mode` and appends `mode.system_suffix` to the system prompt, intersects tool allowlist with `executor` pre-flight.
- Mode change does **not** clear chat history; it injects a transition line (`[mode → EXPLOIT]`) into history and updates the allowlist for subsequent turns.
- Border color of chat panel header tracks `mode.color`.
- Audit log tags every exec with the active mode.
- Mode suggestions come from Bagley itself (see §7.12 nudges).

## 6. Interactions

### 6.1 Hover popup menus

- Mouse hover (Textual's built-in mouse support) over any visible IP, port, CVE, or finding row.
- Hover delay 350ms → popup appears at cursor.
- Popup options are contextual:
  - IP: `[open tab] [nmap sV] [set target] [mark OOS]`
  - Port: `[exploit-db for <service> <version>] [banner grab] [brute :port]`
  - CVE: `[exploit-db] [msf module] [searchsploit]`
  - Finding: `[detail] [dismiss] [add note]`
- Click option or press number `1..9` to invoke.

### 6.2 Selection inspector (Ctrl+I)

Drag-select any text in any panel (Textual supports mouse selection). `Ctrl+I` (or Enter after select) opens `InspectorPane` bottom-right.

Classification via local regex first, then model only when needed:

| Pattern | Classifier | Inspector shows |
|---|---|---|
| IPv4/CIDR | regex | host known? scope? [open tab] [nmap] |
| `CVE-\d{4}-\d+` | regex | severity, exploit-db count, msf module |
| `[a-f0-9]{32}` | hash regex | MD5 → type; rockyou lookup; crack cmd |
| `[a-f0-9]{64}` | hash regex | SHA256 etc |
| URL | regex | status code, fingerprint, dir-bust hint |
| `\d+/tcp\|udp` | port regex | service defaults, known exploits |
| Absolute path | regex | SUID? GTFOBins? linpeas cross-ref |
| Shell command | heuristic | explain flags, risks, safer alt |
| fallback | model | "explain this" short query |

Inspector actions: `[Enter]` save to memory (as cred/note/finding), `[T]` send selection to chat as-is, `[X]` dismiss.

### 6.3 Persistent shell sessions

- When a tool launches an interactive shell (reverse-tcp listener, `ssh`, `meterpreter`), `executor.py` hands the PTY to `ShellPane` instead of capturing + returning stdout.
- `ShellPane` is a live Textual `RichLog` + `Input`; user types directly; Bagley still sees output and can comment in chat.
- Ctrl+B backgrounds the pane (stays alive, rejoinable via palette).
- Closing the pane sends SIGTERM.
- `memory/store.py::sessions` records each shell (user, method, uptime).

### 6.4 @ mentions

- Typing `@` in chat input opens a fuzzy-filtered popup over input.
- Entries come from current state: `@<ip>`, `@creds`, `@creds.<user>`, `@scan.last`, `@finding.<id>`, `@playbook.<name>`, `@file <path>`, `@url <link>`.
- Tab confirms. Enter sends. Shift-Tab cycles backward.
- On submit, `@mention` tokens are substituted in the message body sent to the model with concrete context: `@creds.admin` → `admin:password` inline.

### 6.5 Bang re-exec

- `!!` in chat input = last executed cmd of current tab.
- `!<N>` = nth command in tab history.
- `!<prefix>` = last command starting with prefix.
- Expansion happens on submit, resolved before sending to Bagley.

### 6.6 Smart paste

`ChatPanel` intercepts paste (Ctrl+Shift+V). Paste content goes through a classifier chain:

1. Nmap `<?xml` or table output → `parsers/nmap.py` → hosts, ports, services → promote to memory → inline summary.
2. Shodan/Censys JSON → `parsers/shodan.py` → ingest.
3. Hash-list (one hash per line) → creds pane (type detected per line).
4. `.pcap` path → tshark summary.
5. URL → fingerprint + dir-bust hint.
6. Screenshot path (if `.png`/`.jpg`) → if vision engine enabled, describe; else note path.
7. `CVE-…` ID → inspector opens.
8. Plain IP list (one per line) → add to scope after confirm.
9. Fallback → send as-is to chat.

Each path ends with a chat entry summarizing what was ingested and what actions Bagley suggests next.

### 6.7 Plan mode (Alt+P)

- Alt+P toggles plan mode. Chat dims; plan overlay appears.
- Bagley generates a `Plan` (list of `Step(kind, cmd, description)`).
- User navigates with ↑↓, approves with Enter (runs next), skips with `s`, edits with `e`, approves-all with `A`, exits with Esc.
- Approved steps move to "✓ done", current step is "▶", future steps are "·".
- Plan is persisted in `.bagley/plans/<tab>-<timestamp>.yml` for audit and replay.

### 6.8 Command palette (Ctrl+K)

- Modal over entire app.
- Fuzzy search over ~200 actions: modes, tabs, playbooks, slash commands, common tools, settings.
- Each action has label, description, key-binding hint, icon.
- Enter runs; Esc closes.

### 6.9 Playbooks

- `.playbooks/*.yml` in project root.
- Schema:
  ```yaml
  name: HTB initial recon
  description: Fast first pass on a new target
  target: "{target}"          # var substitution
  steps:
    - run: "nmap -sC -sV -p- --min-rate=1000 {target}"
    - if: "80 in ports or 443 in ports"
      run: "gobuster dir -u http://{target} -w common.txt"
    - if: "445 in ports"
      run: "enum4linux-ng {target}"
    - prompt: "summarize attack surface"
  ```
- Palette "Run playbook …" prompts for `target` and executes.
- Bagley watches for repeated sequences and offers "save this as playbook" nudge (§6.12).

### 6.10 Timeline scrubber (Ctrl+T — different from tab-new? see §11)

**Conflict note:** Ctrl+T is taken by tab-new. Timeline moves to **Ctrl+Shift+T**.

- Opens horizontal scrubber across bottom: events positioned along time axis (scan, port, finding, cred, shell).
- Scrubbing ← / → highlights the event; left pane dims to show state-as-of that moment; diff vs current shown in small panel.
- Ctrl+Shift+Z undoes the latest finding/ingest (for false positives).

### 6.11 Visualizations

- **Progress rings** — kill-chain stages rendered as `●●●○○` bars with % for current target. Lives in `TargetPanel`.
- **Subnet minimap** — for scope `10.10.0.0/24`, 254 cells shown as colored dots (green=up, red=down, gray=unscanned, yellow=scanning). Lives in recon tab.
- **Severity bars** — horizontal bars (`▓▓▓▓░`) for CRIT/HIGH/MED/LOW counts in `HostsPanel::findings`.

### 6.12 Nudges

- Background task evaluates heuristics every 30s:
  - Idle 15min → "want a suggested next step?"
  - ≥3 HIGH findings untouched → "open tab <host> to address?"
  - Same 3-step sequence run 3+ times → "save as playbook?"
  - (If online) new Metasploit module for a known CVE → "re-check <cve>?"
- Rendered as toasts (§6.14) with low-priority styling.

### 6.13 Tour on first launch

- Flag `.bagley/.toured`.
- Overlay highlights each pane in turn with one sentence: "hosts here · chat here · target/killchain here · modes bar · palette".
- Esc skips; never shown again.

### 6.14 Alerts / toasts

- Bottom-right stack, max 4 visible.
- Four severities: info (cyan), ok (green), warn (orange), crit (red).
- Triggers: SCAN COMPLETE, CRITICAL FINDING, NEW CRED, MODE SUGGESTED, SHELL OBTAINED, PLAYBOOK SAVED, AUTO-MEMORY (discrete).
- Click `Enter` opens the relevant pane; `X` or 3s auto-dismiss (crit requires explicit dismiss).
- `Ctrl+N` opens full alerts log.

### 6.15 Graph view (F7)

- Toggle full-screen; nodes = hosts, edges = relationships (scanned, routed-via, pivoted, shell-obtained).
- Current target starred (★).
- Click node = focus target tab.
- Rendering via Textual `Widget` + custom character drawing (box characters and arrows) or falling back to a networkx spring layout rasterized to unicode grid.

### 6.16 Payload builder (Alt+Y)

- Modal 60×20.
- Fields: type (bash/python/nc/php/ps1), LHOST, LPORT, encode (none/base64/url).
- Live preview of payload.
- `C` copy to clipboard (via `pyperclip`), `I` inject into chat, `L` start listener in a new ShellPane.

### 6.17 Screen observe (`/observe pid <N>`)

- Uses existing `src/bagley/observe/` (terminal tap).
- Attaches to an external terminal, streams stdout into a read-only pane, runs it through the smart-paste classifier, feeds results into memory, and lets Bagley narrate in chat.
- Detach with `/observe stop`.

### 6.18 Hot-swap engine (Ctrl+Shift+M)

- Modal listing available engines: local v9, local v10, Ollama (enumerated from HTTP API), stub.
- On selection, instantiates new engine; subsequent turns tagged `[engine=v10-modal]` in chat.
- Old engine GC'd; sessions share chat history.

### 6.19 Voice toggle (Ctrl+V)

- Off → Listen (wake-word "bagley") → Active (always streaming STT).
- TTS speaks only chat assistant messages and critical alerts; never raw tool output.
- States visible in header.

## 7. Keymap

| Key | Action |
|---|---|
| Ctrl+T | new tab (pick host from scope popup) |
| Ctrl+W | close tab |
| Ctrl+1..9 | jump to tab N |
| Ctrl+Tab | cycle tabs |
| F1 | help overlay |
| F2 | focus hosts panel |
| F3 | focus chat |
| F4 | focus notes |
| F5 | focus findings |
| F6 | focus raw tool output |
| F7 | toggle graph view |
| Alt+1..9 | switch to mode N |
| Ctrl+M | cycle mode |
| Alt+P | toggle plan mode |
| Alt+Y | payload builder modal |
| Ctrl+I | inspect selection |
| Ctrl+L | /last full tool output |
| Ctrl+K | command palette |
| Ctrl+N | alerts panel |
| Ctrl+V | toggle voice state |
| Ctrl+B | background current shell pane |
| Ctrl+Shift+T | timeline scrubber |
| Ctrl+Shift+Z | undo last finding/ingest |
| Ctrl+Shift+M | hot-swap engine |
| Ctrl+R | search chat history |
| Esc | close modal / exit plan mode / break |
| Ctrl+D | disconnect (Linux) |
| Ctrl+C | interrupt / disconnect (Windows) |

## 8. Data model

### 8.1 In-memory `AppState`

```python
@dataclass
class AppState:
    scope: Scope | None
    os_info: OsInfo
    mode: Mode
    engine: Engine
    tabs: list[TabState]
    active_tab: int
    voice: VoiceState
    alerts: list[Alert]
    tour_done: bool
    palette_history: list[str]
    nudge_ticks: dict[str, int]

@dataclass
class TabState:
    id: str                           # "recon" or "10.10.14.23"
    kind: str                         # "recon" | "target"
    chat: list[Message]
    react_history: list[dict]
    cmd_history: list[str]            # for bang re-exec
    killchain_stage: int              # 0..6
    creds: list[Cred]
    notes_md: str
    shell_panes: list[ShellPane]
    plan: Plan | None
    timeline: list[TimelineEvent]
```

### 8.2 SQLite (`memory/store.py` reuse)

Existing schema covers `hosts`, `ports`, `findings`, `creds`, `attempts`, `sessions`. New: add `tabs_archived` table for closed-tab state blobs. Add `playbook_runs` table for replay.

### 8.3 File persistence

- `.bagley/repl_history` — prompt_toolkit chat history (already exists).
- `.bagley/audit.log` — exec log (already exists).
- `.bagley/plans/<tab>-<ts>.yml` — new, per plan run.
- `.bagley/sessions/<id>.log` — shell pane transcripts.
- `.bagley/.toured` — flag.
- `.playbooks/*.yml` — user-authored playbooks.

## 9. OS/platform

- `platform.system()` drives display: banner, EOF key hint, statusline `os=` field.
- Linux (primary): full PTY streaming, full recon-tools check on boot.
- Darwin: same as Linux minus some tools (warn on missing).
- Windows (dev): yellow panel warns that recon tools won't run; PTY falls back to `subprocess.run`; persistent shells degrade to non-interactive subprocesses (no reverse-shell listener spawn locally).

## 10. Migration from current CLI

- `bagley` command (entry in `pyproject.toml`) routes to `bagley.tui.app:run`.
- `bagley --simple` keeps the old Rich REPL as fallback.
- All current flags are preserved: `--adapter`, `--base`, `--ollama`, `--stub`, `--scope`, `--auto`, `--allow-rfc1918`, `--disable-runtime-safeguard`, `--max-steps`.
- Audit log + scope behavior unchanged.

## 11. Implementation phases

Built incrementally so each phase produces a working TUI.

**Phase 1 — skeleton (1 week)**
- Textual app boots with header, modes bar, tab bar, 4-pane dashboard.
- Recon tab + single target tab.
- ChatPanel shows ReAct stream with existing `ReActLoop`.
- HostsPanel/TargetPanel read from `memory/store.py`.
- Keymap: Ctrl+T/W/1..9, F1..F6, Ctrl+D, Esc, Ctrl+K palette (minimal, just actions).
- Modes bar visible but only RECON implemented.
- Smoke-testable on Linux + Windows.

**Phase 2 — modes + selection + palette (1 week)**
- All 9 modes wired (system suffix + allowlist + confirm policy + color).
- Alt+1..9 / Ctrl+M.
- Selection inspector (Ctrl+I) with regex classifier and 3–4 inspector types (IP, CVE, hash, URL).
- Palette expanded to ~50 actions.
- Confirmation inline panel in ChatPanel.

**Phase 3 — auto-memory + alerts + visualizations (1 week)**
- Auto-memory promotion (hosts, ports, findings, creds, sessions).
- Toasts with four severities.
- Progress rings, severity bars, subnet minimap.
- Nudges (idle, findings-untouched) — first two only.
- Notes markdown editor in TargetPanel.

**Phase 4 — plan mode + playbooks + bang + @ mentions (1 week)**
- Alt+P plan mode overlay.
- Playbook loader/runner, `.playbooks/` dir.
- Bang re-exec.
- @ mentions popup.
- Smart paste (nmap, hash list, CVE, URL, IP list first — pcap/shodan later).

**Phase 5 — persistent shells + screen observe + graph view (1 week)**
- `ShellPane` with live PTY.
- `/observe pid N`.
- F7 graph view.
- Timeline scrubber (Ctrl+Shift+T).
- Undo (Ctrl+Shift+Z).

**Phase 6 — voice + payload builder + hot-swap + report (1 week)**
- Voice integration in header.
- Alt+Y payload builder.
- Ctrl+Shift+M hot-swap.
- REPORT mode pipeline: notes + memory → markdown.
- First-launch tour.

**Total:** ~6 calendar weeks for feature-complete v1. Each phase ships a usable increment.

### 11.1 New dependencies

Beyond what's already in `pyproject.toml`:

- `textual>=0.80` — TUI framework
- `pyperclip>=1.9` — clipboard integration (payload builder, inspector copy)
- `networkx>=3.3` — graph layout for §6.15
- `pyyaml>=6.0` — playbooks

Existing `rich`, `typer`, `prompt_toolkit` stay.

## 12. Out of scope for v1

- Vision model on pasted screenshots.
- Cloud sync / multi-device.
- Plugin system beyond YAML playbooks.
- Web companion.
- Collaborative multi-operator mode.

## 13. Open questions (for next pass, not blocking spec approval)

1. Should the `recon` tab be killable, or pinned as tab 0 always? (Recommend pinned.)
2. Plan mode: should Bagley propose the plan proactively on mode-switch, or only when user asks?
3. Hot-swap engine: warn on history compatibility (v9 and v10 use same chat template, but future adapters may not)?
4. Graph view: sufficient with networkx spring layout in unicode, or is force-atlas better? (Start with spring; revisit.)
5. Smart paste: auto-ingest or ask first? (Recommend ask for anything that modifies scope; auto for read-only ingest like hashes/ports.)

---

**End of spec.**
