import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_tab_bar_initial_has_recon_and_plus():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        bar = app.query_one("#tab-bar")
        rendered = bar.render().plain if hasattr(bar.render(), "plain") else str(bar.render())
        assert "recon" in rendered
        assert "+" in rendered


@pytest.mark.asyncio
async def test_ctrl_t_opens_new_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+t")
        await pilot.pause()
    assert len(app.state.tabs) == 2
    assert app.state.tabs[1].kind == "target"
    assert app.state.active_tab == 1


@pytest.mark.asyncio
async def test_ctrl_w_closes_non_recon_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert len(app.state.tabs) == 2
        await pilot.press("ctrl+w")
        await pilot.pause()
    assert len(app.state.tabs) == 1
    assert app.state.active_tab == 0


@pytest.mark.asyncio
async def test_ctrl_w_does_not_close_recon_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+w")
        await pilot.pause()
    assert len(app.state.tabs) == 1


@pytest.mark.asyncio
async def test_ctrl_digit_switches_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.press("ctrl+t")
        await pilot.press("ctrl+t")
        await pilot.press("ctrl+1")
        await pilot.pause()
    assert app.state.active_tab == 0
