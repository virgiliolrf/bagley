"""Tests for PlanOverlay widget — navigation, approve, skip, edit, Esc."""

import pytest
from textual.app import App, ComposeResult

from bagley.tui.plan_mode.overlay import PlanOverlay
from bagley.tui.plan_mode.plan import Plan, Step


def _make_plan() -> Plan:
    return Plan(
        goal="recon 10.0.0.1",
        steps=[
            Step(kind="run", cmd="nmap -sV 10.0.0.1", description="Port scan"),
            Step(kind="run", cmd="gobuster dir ...", description="Dir bust"),
            Step(kind="run", cmd="enum4linux-ng ...", description="SMB enum"),
        ],
        tab_id="10.0.0.1",
    )


class _TestApp(App):
    def compose(self) -> ComposeResult:
        yield PlanOverlay(_make_plan(), id="overlay")


@pytest.mark.asyncio
async def test_overlay_renders_steps():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        text = overlay.render_steps_text()
        assert "▶" in text  # ▶
        assert "Port scan" in text
        assert "·" in text  # ·


@pytest.mark.asyncio
async def test_overlay_enter_advances():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        await pilot.press("enter")
        await pilot.pause()
        assert overlay.plan.current_index == 1


@pytest.mark.asyncio
async def test_overlay_skip_advances_without_run():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        await pilot.press("s")
        await pilot.pause()
        from bagley.tui.plan_mode.plan import StepStatus
        assert overlay.plan.steps[0].status == StepStatus.SKIPPED
        assert overlay.plan.current_index == 1


@pytest.mark.asyncio
async def test_overlay_approve_all():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        await pilot.press("A")
        await pilot.pause()
        assert overlay.plan.is_done()


@pytest.mark.asyncio
async def test_overlay_esc_posts_message():
    dismissed = []

    class _TrackApp(App):
        def compose(self) -> ComposeResult:
            yield PlanOverlay(_make_plan(), id="overlay")

        def on_plan_overlay_dismissed(self, event) -> None:
            dismissed.append(True)

    app = _TrackApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("escape")
        await pilot.pause()
    assert dismissed


@pytest.mark.asyncio
async def test_overlay_up_down_navigation():
    app = _TestApp()
    async with app.run_test(size=(120, 40)) as pilot:
        overlay = app.query_one("#overlay", PlanOverlay)
        # Cursor starts at 0; pressing down moves to 1
        await pilot.press("down")
        await pilot.pause()
        assert overlay.cursor == 1
        await pilot.press("up")
        await pilot.pause()
        assert overlay.cursor == 0
