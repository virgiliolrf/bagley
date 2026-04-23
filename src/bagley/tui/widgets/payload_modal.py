"""Alt+Y Payload Builder Modal.

60x20 modal with type selector, LHOST/LPORT inputs, encoding selector,
live preview, and three actions:
  C - copy to clipboard (pyperclip)
  I - inject payload text into chat input
  L - spawn listener in a new ShellPane (stubbed until Phase 5 ShellPane is live)
"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
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
    """60x20 payload builder modal."""

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
        margin-top: 1;
    }
    #action-row { layout: horizontal; height: 3; margin-top: 1; }
    #action-row Button { margin: 0 1; }
    """

    BINDINGS = [
        Binding("ctrl+shift+c", "copy_payload", "Copy", show=True),
        Binding("ctrl+shift+i", "inject_payload", "Inject", show=True),
        Binding("ctrl+shift+l", "spawn_listener", "Listener", show=True),
        Binding("escape", "close_modal", "Close", show=True),
    ]

    def __init__(self, inject_callback=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._inject_callback = inject_callback

    def compose(self) -> ComposeResult:
        with Vertical(id="payload-modal"):
            yield Label("[b]Payload Builder[/b]")
            yield Select(_TYPES, id="type-select", value=PayloadType.BASH, allow_blank=False)
            yield Input(placeholder="LHOST (e.g. 10.10.14.5)", id="lhost-input")
            yield Input(placeholder="LPORT (e.g. 4444)", id="lport-input", value="4444")
            yield Select(_ENCODINGS, id="encoding-select", value=Encoding.NONE, allow_blank=False)
            yield Static("", id="payload-preview")
            with Horizontal(id="action-row"):
                yield Button("[C] Copy", id="btn-copy", variant="default")
                yield Button("[I] Inject", id="btn-inject", variant="primary")
                yield Button("[L] Listener", id="btn-listener", variant="warning")

    def on_mount(self) -> None:
        self._refresh_preview()

    @on(Select.Changed)
    def _on_select_change(self, _event) -> None:
        self._refresh_preview()

    @on(Input.Changed)
    def _on_input_change(self, _event) -> None:
        self._refresh_preview()

    def _build_config(self):
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
        try:
            preview = self.query_one("#payload-preview", Static)
        except Exception:
            return
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
            try:
                pyperclip.copy(payload)
            except Exception:
                pass
            try:
                self.notify("Payload copied to clipboard", severity="information")
            except Exception:
                pass

    def action_inject_payload(self) -> None:
        payload = self._current_payload()
        if self._inject_callback is not None:
            try:
                self._inject_callback(payload)
            except Exception:
                pass
        self.dismiss(payload)

    def action_spawn_listener(self) -> None:
        """Spawns a netcat listener in a new ShellPane (stub)."""
        try:
            lport = int(self.query_one("#lport-input", Input).value.strip())
        except ValueError:
            lport = 4444
        try:
            if hasattr(self.app, "SpawnListener"):
                self.app.post_message_no_wait(self.app.SpawnListener(lport=lport))
        except Exception:
            pass
        self.dismiss(None)

    def action_close_modal(self) -> None:
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
