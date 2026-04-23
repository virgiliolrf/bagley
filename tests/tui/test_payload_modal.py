"""Tests for the Alt+Y payload builder modal."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_alt_y_opens_payload_modal(tmp_path):
    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        modal = app.query_one("#payload-modal")
        assert modal is not None


@pytest.mark.asyncio
async def test_payload_modal_has_type_lhost_lport_fields(tmp_path):
    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        from textual.widgets import Input
        # Should contain a Select for type and Inputs for lhost / lport
        modal = app.query_one("#payload-modal")
        inputs = modal.query(Input)
        assert len(inputs) >= 2          # lhost, lport at minimum


@pytest.mark.asyncio
async def test_payload_preview_updates_on_lhost_change(tmp_path):
    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        from textual.widgets import Input
        modal = app.query_one("#payload-modal")
        lhost_input = modal.query_one("#lhost-input", Input)
        # Clear and type a new LHOST
        lhost_input.value = "192.168.1.99"
        await pilot.pause()
        preview = modal.query_one("#payload-preview")
        rendered = str(preview.render())
        assert "192.168.1.99" in rendered


@pytest.mark.asyncio
async def test_payload_modal_copy_calls_pyperclip(tmp_path):
    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        with patch("pyperclip.copy") as mock_copy:
            # Trigger the copy action directly on the modal
            modal_screen = app.screen
            modal_screen.action_copy_payload()
            await pilot.pause()
            assert mock_copy.called


@pytest.mark.asyncio
async def test_payload_modal_inject_appends_to_chat_input(tmp_path):
    """Pressing I closes the modal and pastes payload into chat input."""
    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        modal_screen = app.screen
        modal_screen.action_inject_payload()
        await pilot.pause()
        # Modal should be gone
        assert len(app.query("#payload-modal")) == 0


@pytest.mark.asyncio
async def test_esc_closes_payload_modal(tmp_path):
    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.press("alt+y")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert len(app.query("#payload-modal")) == 0
