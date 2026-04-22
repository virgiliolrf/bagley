import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_target_panel_shows_no_target_on_recon_tab():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        info = app.query_one("#target-info")
        text = str(info.render())
        assert "no target" in text.lower()


@pytest.mark.asyncio
async def test_target_panel_killchain_shows_all_seven_stages():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        kc = app.query_one("#killchain")
        text = str(kc.render())
        for stage in ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]:
            assert stage in text.lower()


@pytest.mark.asyncio
async def test_target_panel_reflects_killchain_stage_marker():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        app.state.tabs[0].killchain_stage = 2
        app.query_one("#target-panel").refresh_content()
        kc = app.query_one("#killchain")
        text = str(kc.render())
        assert "▸" in text
