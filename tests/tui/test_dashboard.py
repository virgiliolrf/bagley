import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_dashboard_has_three_panes():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        assert app.query_one("#hosts-panel") is not None
        assert app.query_one("#chat-panel") is not None
        assert app.query_one("#target-panel") is not None


@pytest.mark.asyncio
async def test_f2_focuses_hosts():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("f2")
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == "hosts-panel"


@pytest.mark.asyncio
async def test_f3_focuses_chat():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("f3")
        await pilot.pause()
        assert app.focused is not None
        assert app.focused.id == "chat-panel"
