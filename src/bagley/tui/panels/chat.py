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
from bagley.tui.interactions.bang import BangExpander, BangExpansionError
from bagley.tui.interactions.mentions import MentionSubstitutor, build_mention_entries
from bagley.tui.interactions.smart_paste import SmartPasteDispatcher, PasteClassification
from bagley.tui.parsers.nmap import parse_nmap_output
from bagley.tui.parsers.hashes import parse_hash_list
from bagley.tui.modes import by_name
from bagley.tui.modes.persona import mode_system_suffix
from bagley.tui.modes.policy import apply_mode_to_loop
from bagley.tui.plan_mode.generator import PlanGenerator
from bagley.tui.plan_mode.overlay import PlanOverlay
from bagley.tui.plan_mode.persistence import save_plan
from bagley.tui.services.memory_promoter import MemoryPromoter
from bagley.tui.services.alerts import bus as _alert_bus, Alert, Severity
from bagley.tui.services.reporter import Reporter, ReportConfig
from bagley.tui.state import AppState


def _promoter_event_to_alert(kind: str, detail: str) -> "Alert":
    """Map a MemoryPromoter event kind to an Alert with correct severity and title."""
    _MAP: dict[str, tuple[Severity, str, str]] = {
        "new_host":        (Severity.INFO, "◯ saved to memory",  "#hosts-panel"),
        "new_port":        (Severity.INFO, "◯ saved to memory",  "#hosts-panel"),
        "cve_match":       (Severity.CRIT, "CRITICAL FINDING",        "#hosts-panel"),
        "new_cred":        (Severity.WARN, "NEW CRED",                "#target-panel"),
        "exploit_attempt": (Severity.WARN, "EXPLOIT ATTEMPT",         "#chat-panel"),
        "shell_obtained":  (Severity.CRIT, "SHELL OBTAINED",          "#chat-panel"),
    }
    sev, title, selector = _MAP.get(kind, (Severity.INFO, "◯ saved to memory", ""))
    return Alert(severity=sev, title=title, body=detail, source="promoter",
                 pane_selector=selector)


# -- Stub engine (used when state.engine_label == "stub") --

class _StubEngine:
    def generate(self, messages, **kwargs):
        last = next((m for m in reversed(messages) if m["role"] == "user"), None)
        return stub_response(last["content"] if last else "")


# -- Inline confirmation panel --

class ConfirmPanel(Vertical):
    """Inline confirmation panel - shown docked at the bottom of ChatPanel.

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
        visibility: hidden;
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
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Label("", id="confirm-cmd-label")
        with Horizontal(id="confirm-btn-row"):
            yield Button("[Y] Yes", id="confirm-yes-btn", variant="success")
            yield Button("[N] No",  id="confirm-no-btn",  variant="error")

    def show_confirm(self, cmd: str, callback: Callable[[bool], None]) -> None:
        """Populate and reveal the panel."""
        self._pending_cmd = cmd
        self._callback = callback
        truncated = cmd[:60] + "..." if len(cmd) > 60 else cmd
        self.query_one("#confirm-cmd-label", Label).update(
            f"[bold yellow]About to execute:[/] [cyan]{truncated}[/]"
        )
        self.display = True
        self.visible = True
        self.focus()

    def _respond(self, result: bool) -> None:
        self.display = False
        self.visible = False
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


# -- ChatPanel --

class ChatPanel(Vertical):
    DEFAULT_CSS = """
    ChatPanel { border: round $primary; padding: 0 1; }
    ChatPanel > RichLog { height: 1fr; }
    ChatPanel > Input   { height: 3; dock: bottom; }
    """

    BINDINGS = [
        Binding("ctrl+i", "inspect_selection", "Inspect", show=False),
    ]

    _plan_overlay: PlanOverlay | None = None

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="chat-panel", **kwargs)
        self._state = state
        self._loop = self._build_loop()
        self.can_focus = True
        # Phase 3: MemoryPromoter + optional MemoryStore
        self._promoter = MemoryPromoter()
        self._store = None
        try:
            from bagley.memory.store import MemoryStore
            from pathlib import Path
            db_path = Path(".bagley") / "memory.db"
            self._store = MemoryStore(db_path)
        except Exception:
            pass

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

    # -- Public API --

    def refresh_mode(self) -> None:
        """Called by app.action_set_mode / action_cycle_mode after mode change."""
        apply_mode_to_loop(self._loop, self._state.mode)
        try:
            log = self.query_one("#chat-log", RichLog)
            mode = by_name(self._state.mode)
            log.write(
                f"[dim italic][mode -> {mode.name}] "
                f"confirm={mode.confirm_policy} | allowlist={'all' if mode.allowlist is None else len(mode.allowlist)}[/]"
            )
            # Update border color to reflect the new mode
            self.styles.border = ("round", mode.color)
        except Exception:
            pass

    def request_confirm(self, cmd: str, callback: Callable[[bool], None]) -> None:
        """Show the inline confirm panel for *cmd*; call *callback* with result."""
        panel = self.query_one(ConfirmPanel)
        panel.show_confirm(cmd, callback)

    def submit_command(self, cmd: str) -> None:
        """Programmatically submit a command as if the user typed it."""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold green]you>[/] {cmd}")
        self._run_in_loop(cmd, log)

    def post_assistant_message(self, text: str) -> None:
        """Append an assistant message to the chat log and speak it if voice is active."""
        try:
            log = self.query_one("#chat-log", RichLog)
            log.write(f"[magenta]bagley>[/] {text}")
        except Exception:
            pass
        # TTS hook: speak assistant messages (not tool output).
        try:
            self.app.voice.speak(text, role="assistant")
        except AttributeError:
            pass   # voice not wired in test environments without BagleyApp
        except Exception:
            pass

    def _handle_report_mode(self, prompt: str) -> None:
        """In REPORT mode: compile notes + memory into a markdown report."""
        import datetime
        from pathlib import Path

        notes = {
            tab.id: tab.notes_md
            for tab in self._state.tabs
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
            self._post_system_message(
                f"[b]Report compiled[/b] -> `{saved}`\n\n"
                + md[:500] + ("..." if len(md) > 500 else "")
            )
        except Exception as exc:
            self._post_system_message(f"[red]Report error:[/red] {exc}")

    # -- Input handling --

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

        # Bang expansion (!!, !N, !prefix) before anything else
        try:
            if self._state.tabs:
                tab = self._state.tabs[self._state.active_tab]
                expander = BangExpander(cmd_history=tab.cmd_history)
                msg = expander.expand(msg)
        except BangExpansionError as exc:
            self._post_system_message(f"[bang error] {exc}")
            return

        # @ mention substitution
        try:
            if self._state.tabs:
                tab = self._state.tabs[self._state.active_tab]
                last_scan = ""
                if tab.react_history:
                    last_scan = tab.react_history[-1].get("output", "") if isinstance(
                        tab.react_history[-1], dict) else ""
                context = {
                    "hosts": list(self._state.scope_hosts),
                    "creds": {
                        c.get("user", ""): f"{c.get('user','')}:{c.get('pass','')}"
                        for c in tab.creds
                    },
                    "scan_last": last_scan,
                    "findings": {},
                    "playbooks": [],
                }
                substitutor = MentionSubstitutor(context=context)
                msg = substitutor.substitute(msg)
        except Exception:
            pass

        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold green]you>[/] {msg}")
        if self._handle_slash_command(msg):
            return
        # Record in history for future bang expansion
        try:
            if self._state.tabs:
                self._state.tabs[self._state.active_tab].cmd_history.append(msg)
        except Exception:
            pass
        # Phase 6: REPORT mode intercept - compile report instead of executing tools.
        if self._state.mode == "REPORT":
            self._handle_report_mode(msg)
            return
        self._respond(msg)

    def _respond(self, msg: str) -> None:
        """Default engine dispatch. Monkeypatched in tests to simulate responses."""
        log = self.query_one("#chat-log", RichLog)
        self._run_in_loop(msg, log)

    def _handle_slash_command(self, text: str) -> bool:
        """Return True if the text was a slash command (handled here)."""
        cmd = text.strip().lower()
        if cmd == "/memory" or cmd.startswith("/memory "):
            self._show_memory_browse()
            return True
        return False

    def _show_memory_browse(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("[b cyan]◆ MEMORY BROWSE[/]")
        if self._store is None:
            log.write("[dim](no memory store active)[/]")
            return
        try:
            for sev in ("critical", "high", "medium", "low"):
                findings = self._store.list_findings_by_severity(sev)
                if findings:
                    log.write(f"[b]{sev.upper()}[/] ({len(findings)})")
                    for f in findings[:5]:    # cap display at 5 per severity
                        log.write(f"  · [{f['host']}] {f['summary']}")
            total = len(self._store.list_findings())
            if total == 0:
                log.write("[dim](no findings in memory yet)[/]")
        except Exception as e:
            log.write(f"[red](memory error: {e})[/]")

    def _run_in_loop(self, msg: str, log: RichLog) -> None:
        steps = self._loop.run(msg, self._system_for_current_mode())
        response_text_parts: list[str] = []
        for step in steps:
            if step.kind in {"assistant", "final"}:
                log.write(f"[magenta]bagley>[/] {step.content}")
                response_text_parts.append(step.content or "")
            elif step.kind == "tool":
                rc = step.execution.returncode if step.execution else 0
                color = "green" if rc == 0 else "yellow"
                log.write(f"[{color}]tool>[/] {step.content}")
                response_text_parts.append(step.content or "")
            elif step.kind == "blocked":
                log.write(f"[red]blocked>[/] {step.content}")
        self._state.turn += 1
        # Phase 3: auto-memory promotion hook
        response_text = "\n".join(response_text_parts)
        self._run_promoter(response_text)
        try:
            self.app.query_one("#header").refresh_content()
        except Exception:
            pass
        try:
            self.app.query_one("#statusline").refresh_content()
        except Exception:
            pass

    def _run_promoter(self, response_text: str) -> None:
        """Scan assistant response for auto-memory events and publish toasts."""
        if self._store is None or not response_text.strip():
            return
        try:
            tab = (self._state.tabs[self._state.active_tab]
                   if self._state.tabs else None)
            host = tab.id if (tab and tab.kind == "target") else None
            events = self._promoter.scan(response_text, self._store,
                                         current_host=host)
            for kind, detail in events:
                _alert_bus.publish(_promoter_event_to_alert(kind, detail))
        except Exception:
            pass

    # -- Ctrl+I - inspect selection --

    def action_inspect_selection(self) -> None:
        """Open InspectorPane with currently selected text (or chat-input fallback)."""
        text = ""
        try:
            sel = self.screen.selection
            if sel is not None:
                text = str(sel)
        except Exception:
            pass
        if not text:
            try:
                inp = self.query_one("#chat-input", Input)
                text = inp.value
            except Exception:
                pass
        if text.strip():
            try:
                from bagley.tui.panels.inspector import InspectorPane
                pane = self.app.query_one(InspectorPane)
                pane.inspect(text.strip())
            except Exception:
                pass

    # -- Plan mode --

    def _submit_to_loop(self, cmd: str) -> None:
        """Submit a command text to the ReAct loop (used by plan mode, smart paste)."""
        try:
            log = self.query_one("#chat-log", RichLog)
            log.write(f"[bold green]you>[/] {cmd}")
            self._run_in_loop(cmd, log)
        except Exception:
            pass

    def _post_system_message(self, text: str) -> None:
        """Post a dimmed system-style message into the chat log."""
        try:
            log = self.query_one("#chat-log", RichLog)
            log.write(f"[dim]{text}[/]")
        except Exception:
            pass

    def toggle_plan_mode(self) -> None:
        """Show plan overlay if hidden; remove it if already shown."""
        if self._plan_overlay is not None:
            try:
                self._plan_overlay.remove()
            except Exception:
                pass
            self._plan_overlay = None
            self.styles.opacity = "1"
            return

        # Use last user message as goal, fallback to generic text
        goal = "recon current target"
        try:
            if self._state.tabs:
                tab = self._state.tabs[self._state.active_tab]
                if getattr(tab, "chat", None):
                    last_user = next(
                        (m["content"] for m in reversed(tab.chat) if m.get("role") == "user"),
                        goal,
                    )
                    goal = last_user
        except Exception:
            pass

        # Use stub/real engine from app state or fall back to local stub
        engine = getattr(self.app, "engine", None)
        if engine is None:
            engine = _StubEngine()

        gen = PlanGenerator(engine=engine)
        try:
            tab_id = self._state.tabs[self._state.active_tab].id if self._state.tabs else "recon"
            plan = gen.generate(goal=goal, tab_id=tab_id)
        except ValueError as exc:
            try:
                self.app.notify(str(exc), severity="error")
            except Exception:
                pass
            return

        overlay = PlanOverlay(plan, id="plan-overlay")
        self._plan_overlay = overlay
        self.styles.opacity = "0.4"
        self.mount(overlay)

    def load_plan(self, plan) -> None:
        """Mount a pre-built Plan as overlay (used by PlaybookRunner flow)."""
        if self._plan_overlay is not None:
            try:
                self._plan_overlay.remove()
            except Exception:
                pass
            self._plan_overlay = None
        overlay = PlanOverlay(plan, id="plan-overlay")
        self._plan_overlay = overlay
        self.styles.opacity = "0.4"
        self.mount(overlay)

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
            try:
                self._plan_overlay.remove()
            except Exception:
                pass
            self._plan_overlay = None
            self.styles.opacity = "1"

    # -- Smart paste --

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
                    from bagley.tui.memory import ingest_hosts  # type: ignore[attr-defined]
                    ingest_hosts(hosts)
                except ImportError:
                    pass
                except Exception:
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
            try:
                from bagley.tui.panels.inspector import InspectorPane
                pane = self.app.query_one(InspectorPane)
                pane.inspect(cve)
            except Exception:
                pass

        elif cls == PasteClassification.URL:
            url = text.strip()
            self._post_system_message(
                f"URL pasted: {url}. Consider: fingerprint + dir-bust."
            )

        elif cls == PasteClassification.IP_LIST:
            ips = dispatcher.extract_ips(text)

            def _on_confirm(confirmed: bool) -> None:
                if confirmed:
                    for ip in ips:
                        self._state.scope_hosts = frozenset(
                            self._state.scope_hosts | {ip}
                        )
                    self._post_system_message(f"Added {len(ips)} IP(s) to scope.")
                else:
                    self._post_system_message("Scope add cancelled.")

            # Textual constraint: use inline ConfirmPanel (project convention)
            # instead of pushing a modal screen. Falls back to auto-confirm
            # outside a mounted app.
            try:
                self.request_confirm(
                    f"Add {len(ips)} IP(s) to scope?", _on_confirm,
                )
            except Exception:
                # If confirm panel not available (e.g., panel not mounted yet),
                # default to doing the add without interactive prompt.
                _on_confirm(True)

        else:
            # Fallback: send as-is to chat loop
            self._submit_to_loop(text)
