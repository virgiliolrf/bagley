"""OS-level event hooks: clipboard + window focus.

Linux X11 via python-xlib / pyperclip. Wayland parcial.

Instalação:
    pip install pyperclip python-xlib
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class FocusEvent:
    timestamp: float
    window_title: str
    window_class: str


@dataclass
class ClipboardEvent:
    timestamp: float
    content: str
    length: int


class ClipboardWatcher:
    """Poll clipboard 5Hz (cheap). Dispara callback em mudança."""

    def __init__(self, callback: Callable[[ClipboardEvent], None], poll_hz: float = 5.0) -> None:
        self.callback = callback
        self.poll_interval = 1.0 / poll_hz
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        try:
            import pyperclip
        except ImportError:
            import sys
            print("[clipboard] pyperclip não disponível, skip", file=sys.stderr)
            return
        last = ""
        while not self._stop.is_set():
            try:
                current = pyperclip.paste()
            except Exception:
                time.sleep(self.poll_interval)
                continue
            if current != last and current.strip():
                last = current
                ev = ClipboardEvent(timestamp=time.monotonic(),
                                    content=current[:2000], length=len(current))
                try:
                    self.callback(ev)
                except Exception:
                    pass
            time.sleep(self.poll_interval)


class FocusWatcher:
    """Detecta mudança de janela ativa via xdotool. Linux X11 only."""

    def __init__(self, callback: Callable[[FocusEvent], None], poll_hz: float = 2.0) -> None:
        self.callback = callback
        self.poll_interval = 1.0 / poll_hz
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        import subprocess
        last_window_id = ""
        while not self._stop.is_set():
            try:
                wid = subprocess.run(["xdotool", "getactivewindow"],
                                     capture_output=True, text=True, timeout=1).stdout.strip()
                if wid and wid != last_window_id:
                    title = subprocess.run(["xdotool", "getwindowname", wid],
                                           capture_output=True, text=True, timeout=1).stdout.strip()
                    wclass = subprocess.run(["xprop", "-id", wid, "WM_CLASS"],
                                            capture_output=True, text=True, timeout=1).stdout.strip()
                    last_window_id = wid
                    ev = FocusEvent(timestamp=time.monotonic(),
                                    window_title=title, window_class=wclass)
                    try:
                        self.callback(ev)
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(self.poll_interval)
