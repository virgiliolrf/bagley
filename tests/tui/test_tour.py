"""Tests for the first-launch tour: flag logic, Esc skip, no repeat."""

from __future__ import annotations

from pathlib import Path

import pytest

from bagley.tui.services.tour import TourService


# ---------------------------------------------------------------------------
# Flag logic (no Textual involved - pure filesystem)
# ---------------------------------------------------------------------------

def test_tour_not_done_when_flag_absent(tmp_path: Path):
    svc = TourService(bagley_dir=tmp_path)
    assert not svc.is_done()


def test_mark_done_creates_flag_file(tmp_path: Path):
    svc = TourService(bagley_dir=tmp_path)
    svc.mark_done()
    assert (tmp_path / ".toured").exists()


def test_is_done_returns_true_after_mark(tmp_path: Path):
    svc = TourService(bagley_dir=tmp_path)
    svc.mark_done()
    assert svc.is_done()


def test_second_instance_sees_flag(tmp_path: Path):
    TourService(bagley_dir=tmp_path).mark_done()
    svc2 = TourService(bagley_dir=tmp_path)
    assert svc2.is_done()


# ---------------------------------------------------------------------------
# TUI integration - first launch shows tour, second skips
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_launch_tour_shown(tmp_path: Path):
    from bagley.tui.app import BagleyApp

    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        # Tour overlay should be mounted
        overlays = app.query("#tour-overlay")
        assert len(overlays) > 0


@pytest.mark.asyncio
async def test_esc_dismisses_tour_and_sets_flag(tmp_path: Path):
    from bagley.tui.app import BagleyApp

    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        # Skip tour via public action on overlay
        try:
            overlay = app.query_one("#tour-overlay")
            overlay.action_skip_tour()
        except Exception:
            pass
        await pilot.pause()
        # Overlay gone
        assert len(app.query("#tour-overlay")) == 0
    # Flag written
    assert (tmp_path / ".toured").exists()


@pytest.mark.asyncio
async def test_second_launch_skips_tour(tmp_path: Path):
    from bagley.tui.app import BagleyApp

    # Pre-write the flag so tour is already "done".
    (tmp_path / ".toured").touch()

    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        # No tour overlay on second launch
        assert len(app.query("#tour-overlay")) == 0
