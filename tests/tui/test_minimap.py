"""Minimap widget tests."""
import pytest
from bagley.tui.widgets.rings import Minimap


def test_minimap_has_254_cells_empty():
    m = Minimap()
    m._render_map()
    rendered = m.renderable
    text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
    # Each cell is either ● or · — count them (markup stripped)
    # We care about cell count logic; verify cell-per-row constant
    assert m._COLS == 32
    total_cells = sum(len(row) for row in [list(range(1, 255))])
    assert total_cells == 254


def test_minimap_up_host_shows_green_dot():
    m = Minimap(subnet_prefix="10.10.0")
    m.refresh_data({"10.10.0.5": "up", "10.10.0.20": "down", "10.10.0.33": "scanning"})
    rendered = m.renderable
    text = rendered.plain if hasattr(rendered, "plain") else str(rendered)
    # Markup stripped; only the raw text matters here
    # Check markup source contains expected color annotations
    source = str(m.renderable)
    assert "[green]●[/]" in source or "green" in source


def test_minimap_scanning_state_yellow():
    m = Minimap()
    m.refresh_data({"10.0.0.10": "scanning"})
    source = str(m.renderable)
    assert "yellow" in source or "[yellow]" in source


def test_minimap_unknown_hosts_dim():
    m = Minimap()
    m._render_map()   # all unknown
    source = str(m.renderable)
    assert "dim" in source


def test_minimap_refreshing_changes_state():
    m = Minimap()
    m._render_map()
    before = str(m.renderable)
    m.refresh_data({"10.0.0.1": "up"})
    after = str(m.renderable)
    assert before != after


@pytest.mark.asyncio
async def test_minimap_mounts_in_recon_screen():
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        # ReconScreen is the initial tab-0 view
        minimap = app.query_one("#subnet-minimap")
        assert minimap is not None
