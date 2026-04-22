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
