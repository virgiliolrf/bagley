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
