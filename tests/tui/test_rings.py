"""ProgressRings rendering tests."""
import pytest
from bagley.tui.widgets.rings import ProgressRings


def test_rings_stage_0_all_empty():
    r = ProgressRings()
    r._stage = 0
    text = r._render_text()
    assert "○" in text
    assert "●" not in text
    assert "0%" in text


def test_rings_stage_3_of_7_shows_correct_fill():
    r = ProgressRings()
    r._stage = 3
    text = r._render_text()
    assert text.count("●") == 3
    assert text.count("○") == 4
    assert "42%" in text or "43%" in text   # 3/7 ≈ 42.8%


def test_rings_stage_7_all_filled():
    r = ProgressRings()
    r._stage = 7
    text = r._render_text()
    assert "○" not in text
    assert "●" in text
    assert "100%" in text


def test_rings_stage_labels():
    r = ProgressRings()
    text = r._render_text()
    for label in ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]:
        assert label in text.lower()


@pytest.mark.asyncio
async def test_rings_mounts_in_target_panel():
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        rings = app.query_one("#killchain-rings")
        assert rings is not None
