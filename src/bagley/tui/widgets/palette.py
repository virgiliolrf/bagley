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
    ("run playbook …",                  "run_playbook_picker"),
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
    ("reload config",                   "reload_config"),
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
    #palette { width: 64; height: auto; border: solid $primary;
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
