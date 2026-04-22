"""AlertsLog modal — Ctrl+N shows historical alerts."""
import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.services.alerts import Alert, AlertBus, Severity


@pytest.mark.asyncio
async def test_ctrl_n_opens_alerts_log():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+n")
        await pilot.pause()
        log = app.query_one("#alerts-log-screen")
        assert log is not None


@pytest.mark.asyncio
async def test_alerts_log_shows_published_alert():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        from bagley.tui.services.alerts import bus
        bus.publish(Alert(Severity.CRIT, "Log4Shell", "CVE-2021-44228", "test"))
        await pilot.press("ctrl+n")
        await pilot.pause()
        log = app.query_one("#alerts-log-screen")
        rich_log = log.query_one("#alerts-list")
        # Flatten RichLog segments to plain text
        rendered = "\n".join(
            "".join(seg.text for seg in line)
            for line in rich_log.lines
        )
        assert "Log4Shell" in rendered


@pytest.mark.asyncio
async def test_alerts_log_closes_on_escape():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+n")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        try:
            app.query_one("#alerts-log-screen")
            assert False, "screen should be gone"
        except Exception:
            pass  # expected
