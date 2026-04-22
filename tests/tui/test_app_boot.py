import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_app_boots_and_mounts_header():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(120, 40)) as pilot:
        assert app.state.mode == "RECON"
        header = app.query_one("#header")
        assert header is not None


@pytest.mark.asyncio
async def test_app_quits_on_ctrl_d():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+d")
        await pilot.pause()
    assert app._exit is True
