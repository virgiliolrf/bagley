"""Timeline scrubber widget tests."""
import datetime
import pytest
from textual.app import App, ComposeResult
from bagley.tui.widgets.timeline import Timeline, TimelineSeek
from bagley.tui.services.history import EngagementHistory, TimelineEvent, EventKind


def _ts(offset_s: int = 0) -> datetime.datetime:
    return datetime.datetime(2026, 4, 26, 12, 0, 0) + datetime.timedelta(seconds=offset_s)


def _make_history() -> EngagementHistory:
    h = EngagementHistory(tab_id="10.10.14.1")
    h.append(TimelineEvent(kind=EventKind.SCAN,    ts=_ts(0),  label="scan",    data={}))
    h.append(TimelineEvent(kind=EventKind.PORT,    ts=_ts(10), label="port 80", data={}))
    h.append(TimelineEvent(kind=EventKind.FINDING, ts=_ts(20), label="CVE",     data={}))
    h.append(TimelineEvent(kind=EventKind.CRED,    ts=_ts(30), label="admin",   data={}))
    h.append(TimelineEvent(kind=EventKind.SHELL,   ts=_ts(40), label="shell",   data={}))
    return h


class _TimelineApp(App):
    def __init__(self, history: EngagementHistory) -> None:
        super().__init__()
        self._history = history

    def compose(self) -> ComposeResult:
        yield Timeline(history=self._history, id="tl")


@pytest.mark.asyncio
async def test_timeline_mounts_with_events():
    app = _TimelineApp(_make_history())
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        assert tl is not None
        assert tl.event_count == 5


@pytest.mark.asyncio
async def test_timeline_scrub_right_advances_index():
    app = _TimelineApp(_make_history())
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        tl.focus()
        await pilot.pause()
        start_idx = tl.selected_index
        await pilot.press("right")
        assert tl.selected_index > start_idx or tl.selected_index == tl.event_count - 1


@pytest.mark.asyncio
async def test_timeline_scrub_left_decrements_index():
    app = _TimelineApp(_make_history())
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        tl.focus()
        await pilot.pause()
        # Move right first
        await pilot.press("right")
        await pilot.press("right")
        idx_before = tl.selected_index
        await pilot.press("left")
        assert tl.selected_index < idx_before or tl.selected_index == 0


@pytest.mark.asyncio
async def test_timeline_appending_event_increases_count():
    h = _make_history()
    app = _TimelineApp(h)
    async with app.run_test(size=(120, 5)) as pilot:
        tl = app.query_one("#tl", Timeline)
        count_before = tl.event_count
        h.append(TimelineEvent(kind=EventKind.NOTE, ts=_ts(50), label="note", data={}))
        tl.reload()
        await pilot.pause()
        assert tl.event_count == count_before + 1
