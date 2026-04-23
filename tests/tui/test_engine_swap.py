"""Tests for the Ctrl+Shift+M hot-swap engine modal."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_ctrl_shift_m_opens_engine_modal(tmp_path):
    (tmp_path / ".toured").touch()
    with patch("bagley.tui.widgets.engine_swap_modal.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v9", kind=EngineKind.LOCAL, path=Path("/runs/bagley-v9")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            modal = app.query_one("#engine-swap-modal")
            assert modal is not None


@pytest.mark.asyncio
async def test_engine_modal_lists_engines(tmp_path):
    (tmp_path / ".toured").touch()
    with patch("bagley.tui.widgets.engine_swap_modal.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v9", kind=EngineKind.LOCAL, path=Path("/runs/bagley-v9")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            from textual.widgets import ListView
            modal = app.query_one("#engine-swap-modal")
            lvs = modal.query(ListView)
            assert len(lvs) > 0
            # Also check items
            assert len(lvs[0].children) >= 2


@pytest.mark.asyncio
async def test_selecting_engine_updates_state_label(tmp_path):
    """After selection, app.state.engine_label is updated."""
    (tmp_path / ".toured").touch()
    with patch("bagley.tui.widgets.engine_swap_modal.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v10-modal", kind=EngineKind.LOCAL, path=Path("/runs/v10")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            # Trigger selection of first item directly through the modal
            modal_screen = app.screen
            from textual.widgets import ListView
            lv = modal_screen.query_one("#engine-list", ListView)
            lv.index = 0
            modal_screen._select_current()
            await pilot.pause()
            assert app.state.engine_label == "bagley-v10-modal"


@pytest.mark.asyncio
async def test_chat_history_preserved_after_swap(tmp_path):
    """Chat history in active tab must survive an engine swap."""
    (tmp_path / ".toured").touch()
    with patch("bagley.tui.widgets.engine_swap_modal.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [
            EngineEntry(label="bagley-v9", kind=EngineKind.LOCAL, path=Path("/runs/v9")),
            EngineEntry(label="stub", kind=EngineKind.STUB),
        ]
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        # Pre-seed chat history in state
        app.state.tabs[0].chat = [{"role": "user", "content": "seed message"}]
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            modal_screen = app.screen
            from textual.widgets import ListView
            lv = modal_screen.query_one("#engine-list", ListView)
            lv.index = 0
            modal_screen._select_current()
            await pilot.pause()
            # History must still be present
            assert app.state.tabs[0].chat[0]["content"] == "seed message"


@pytest.mark.asyncio
async def test_esc_closes_engine_modal(tmp_path):
    (tmp_path / ".toured").touch()
    with patch("bagley.tui.widgets.engine_swap_modal.list_engines") as mock_list:
        from bagley.tui.services.engine_registry import EngineEntry, EngineKind
        mock_list.return_value = [EngineEntry(label="stub", kind=EngineKind.STUB)]
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+shift+m")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            assert len(app.query("#engine-swap-modal")) == 0
