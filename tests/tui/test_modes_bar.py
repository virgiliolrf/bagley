import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.modes import MODES


def test_modes_registry_has_nine_entries():
    names = [m.name for m in MODES]
    assert names == [
        "RECON", "ENUM", "EXPLOIT", "POST",
        "PRIVESC", "STEALTH", "OSINT", "REPORT", "LEARN",
    ]


@pytest.mark.asyncio
async def test_modes_bar_renders_all_nine():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        bar = app.query_one("#modes-bar")
        rendered = bar.render().plain if hasattr(bar.render(), "plain") else str(bar.render())
        for name in ["RECON", "ENUM", "EXPLOIT", "POST", "PRIVESC",
                      "STEALTH", "OSINT", "REPORT", "LEARN"]:
            assert name in rendered


@pytest.mark.asyncio
async def test_alt_digit_switches_mode():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+3")
        await pilot.pause()
    assert app.state.mode == "EXPLOIT"
