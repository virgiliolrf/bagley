import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_statusline_shows_turn_and_engine():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        footer = app.query_one("#statusline")
        text = str(footer.render())
        assert "turn=0" in text
        assert "engine=stub" in text
        assert "F1" in text or "palette" in text
