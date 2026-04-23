"""Timeline scrubber widget.

Renders events as labelled tick-marks along a horizontal bar. Left/Right key presses
move the selection; the widget posts ``TimelineSeek`` so the parent screen can
dim the workspace to the state at that moment and show a diff panel.

Layout (single-row):
    [SCAN]----[PORT]----[FINDING]----[CRED]----[SHELL]
                          ^ selected (highlighted)

The widget occupies a fixed height of 3 rows: tick marks, label row, and a thin
connector bar. Heights are stable so the surrounding layout does not reflow.
"""
from __future__ import annotations

import datetime
from typing import Optional

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.message import Message
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

from bagley.tui.services.history import EngagementHistory, TimelineEvent

_STYLE_TICK = Style(color="bright_black")
_STYLE_SELECTED = Style(color="bright_yellow", bold=True, reverse=True)
_STYLE_LINE = Style(color="bright_black")
_STYLE_LABEL = Style(color="white")
_STYLE_LABEL_SEL = Style(color="bright_yellow", bold=True)

_KIND_ICONS = {
    "SCAN":    "S",
    "PORT":    "P",
    "FINDING": "F",
    "CRED":    "C",
    "SHELL":   "►",
    "INGEST":  "I",
    "NOTE":    "N",
}


class TimelineSeek(Message):
    """Posted when the scrubber moves to a new position."""

    def __init__(self, event: TimelineEvent, index: int) -> None:
        super().__init__()
        self.event = event
        self.index = index


class Timeline(Widget):
    """Horizontal timeline scrubber. Height = 3 rows."""

    DEFAULT_CSS = """
    Timeline {
        height: 3;
        background: $background;
    }
    """

    can_focus = True
    selected_index: reactive[int] = reactive(0)

    def __init__(self, history: EngagementHistory, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history = history
        self._events: list[TimelineEvent] = []
        self._tick_cols: list[int] = []

    def on_mount(self) -> None:
        self.reload()

    def reload(self) -> None:
        self._events = list(self._history.events)
        self._compute_tick_cols()
        if self.selected_index >= len(self._events) and self._events:
            self.selected_index = len(self._events) - 1
        self.refresh()

    @property
    def event_count(self) -> int:
        return len(self._events)

    def _compute_tick_cols(self) -> None:
        """Map events uniformly across widget width."""
        w = self.size.width or 80
        n = len(self._events)
        if n == 0:
            self._tick_cols = []
            return
        if n == 1:
            self._tick_cols = [w // 2]
            return
        margin = 4
        usable = w - 2 * margin
        self._tick_cols = [
            margin + int(i / (n - 1) * usable) for i in range(n)
        ]

    def on_key(self, event: events.Key) -> None:
        if event.key == "right":
            self._move(1)
            event.stop()
        elif event.key == "left":
            self._move(-1)
            event.stop()

    def _move(self, delta: int) -> None:
        if not self._events:
            return
        new_idx = max(0, min(len(self._events) - 1, self.selected_index + delta))
        self.selected_index = new_idx
        self.post_message(TimelineSeek(event=self._events[new_idx], index=new_idx))
        self.refresh()

    def render_line(self, y: int) -> Strip:
        w = self.size.width or 80
        if y == 0:
            return self._render_connector_row(w)
        if y == 1:
            return self._render_tick_row(w)
        if y == 2:
            return self._render_label_row(w)
        return Strip.blank(w)

    def _render_connector_row(self, w: int) -> Strip:
        row = [(" ", _STYLE_LINE)] * w
        if len(self._tick_cols) >= 2:
            for i in range(self._tick_cols[0], self._tick_cols[-1] + 1):
                if 0 <= i < w:
                    row[i] = ("─", _STYLE_LINE)
        return Strip([Segment(ch, st) for ch, st in row])

    def _render_tick_row(self, w: int) -> Strip:
        row = [(" ", _STYLE_LINE)] * w
        for idx, col in enumerate(self._tick_cols):
            if 0 <= col < w:
                is_sel = idx == self.selected_index
                ev = self._events[idx]
                icon = _KIND_ICONS.get(ev.kind.name, "·")
                style = _STYLE_SELECTED if is_sel else _STYLE_TICK
                row[col] = (icon, style)
        return Strip([Segment(ch, st) for ch, st in row])

    def _render_label_row(self, w: int) -> Strip:
        row = [(" ", Style.null())] * w
        for idx, col in enumerate(self._tick_cols):
            if 0 <= col < w:
                ev = self._events[idx]
                label = ev.label[:8]
                is_sel = idx == self.selected_index
                style = _STYLE_LABEL_SEL if is_sel else _STYLE_LABEL
                start = max(0, col - len(label) // 2)
                for i, ch in enumerate(label):
                    if 0 <= start + i < w:
                        row[start + i] = (ch, style)
        return Strip([Segment(ch, st) for ch, st in row])

    def on_resize(self) -> None:
        self._compute_tick_cols()
        self.refresh()
