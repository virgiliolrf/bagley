import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_ctrl_k_opens_palette():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+k")
        await pilot.pause()
        # palette is a ModalScreen; when pushed it becomes the active screen
        assert app.screen is not None
        assert app.screen.query("#palette") or app.query("#palette")


@pytest.mark.asyncio
async def test_palette_selects_new_tab_action():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("ctrl+k")
        await pilot.pause()
        inp = app.screen.query_one("#palette-input")
        inp.value = "new tab"
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
    assert len(app.state.tabs) == 2
