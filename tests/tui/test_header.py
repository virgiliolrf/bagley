import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_header_shows_os_and_mode():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        header = app.query_one("#header")
        rendered = header.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "Bagley" in text
        assert app.state.os_info.system in text
        assert "RECON" in text


@pytest.mark.asyncio
async def test_header_updates_when_mode_changes():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(140, 40)) as pilot:
        app.state.mode = "EXPLOIT"
        header = app.query_one("#header")
        header.refresh_content()
        rendered = header.render()
        text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
        assert "EXPLOIT" in text
