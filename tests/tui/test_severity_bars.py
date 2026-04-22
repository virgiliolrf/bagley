"""SeverityBars rendering tests."""
import pytest
from bagley.tui.widgets.rings import SeverityBars


def test_severity_bars_empty_counts():
    sb = SeverityBars()
    sb.refresh_data({"critical": 0, "high": 0, "medium": 0, "low": 0})
    text = sb._render_text()
    assert "░" in text    # all empty bars
    assert "▓" not in text


def test_severity_bars_full_crit():
    sb = SeverityBars()
    sb.refresh_data({"critical": 10, "high": 0, "medium": 0, "low": 0})
    text = sb._render_text()
    lines = [l for l in text.splitlines() if "CRIT" in l.upper()]
    assert len(lines) == 1
    assert "▓" in lines[0]


def test_severity_bars_counts_shown():
    sb = SeverityBars()
    sb.refresh_data({"critical": 3, "high": 7, "medium": 2, "low": 1})
    text = sb._render_text()
    assert "3" in text
    assert "7" in text


def test_severity_bars_bar_proportional():
    sb = SeverityBars(bar_width=10)
    sb.refresh_data({"critical": 5, "high": 10, "medium": 0, "low": 0})
    text = sb._render_text()
    crit_line = next(l for l in text.splitlines() if "CRIT" in l.upper())
    high_line  = next(l for l in text.splitlines() if "HIGH" in l.upper())
    # HIGH (10) should have more filled cells than CRIT (5)
    assert high_line.count("▓") >= crit_line.count("▓")


@pytest.mark.asyncio
async def test_severity_bars_mounts_in_hosts_panel():
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        bars = app.query_one("#severity-bars")
        assert bars is not None
