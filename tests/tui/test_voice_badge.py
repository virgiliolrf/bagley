"""Tests for VoiceBadge widget - correct icon per VoiceState."""

from __future__ import annotations

import pytest
from bagley.tui.services.voice import VoiceState
from bagley.tui.widgets.voice_badge import VoiceBadge, BADGE_OFF, BADGE_LISTEN, BADGE_ACTIVE


# ---------------------------------------------------------------------------
# Unit: badge text per state
# ---------------------------------------------------------------------------

def test_badge_off_text_contains_off_icon():
    badge = VoiceBadge()
    badge.set_state(VoiceState.OFF)
    assert BADGE_OFF in badge.renderable


def test_badge_listen_text_contains_listen_icon():
    badge = VoiceBadge()
    badge.set_state(VoiceState.LISTEN)
    assert BADGE_LISTEN in badge.renderable


def test_badge_active_text_contains_active_icon():
    badge = VoiceBadge()
    badge.set_state(VoiceState.ACTIVE)
    assert BADGE_ACTIVE in badge.renderable


# ---------------------------------------------------------------------------
# Integration: header contains voice badge, state updates propagate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_header_mounts_voice_badge(tmp_path):
    from bagley.tui.app import BagleyApp
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    (tmp_path / ".toured").touch()
    async with app.run_test(size=(160, 40)) as pilot:
        badge = app.query_one("#voice-badge")
        assert badge is not None


@pytest.mark.asyncio
async def test_ctrl_v_cycles_voice_badge_to_listen(tmp_path):
    from bagley.tui.app import BagleyApp
    from unittest.mock import patch
    (tmp_path / ".toured").touch()
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT"):
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+v")
            await pilot.pause()
            badge = app.query_one("#voice-badge")
            assert BADGE_LISTEN in badge.renderable


@pytest.mark.asyncio
async def test_ctrl_v_twice_cycles_to_active(tmp_path):
    from bagley.tui.app import BagleyApp
    from unittest.mock import patch
    (tmp_path / ".toured").touch()
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT"):
        app = BagleyApp(stub=True, bagley_dir=tmp_path)
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("ctrl+v")
            await pilot.pause()
            await pilot.press("ctrl+v")
            await pilot.pause()
            badge = app.query_one("#voice-badge")
            assert BADGE_ACTIVE in badge.renderable
