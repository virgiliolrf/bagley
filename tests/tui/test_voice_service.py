"""Tests for the TUI-side voice controller.

All audio / mic / wake-word I/O is mocked — no real sound hardware is touched.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bagley.tui.services.voice import VoiceService, VoiceState


# ---------------------------------------------------------------------------
# State machine: off -> listen -> active -> off (cyclic)
# ---------------------------------------------------------------------------

def test_initial_state_is_off():
    svc = VoiceService()
    assert svc.state == VoiceState.OFF


def test_cycle_off_to_listen():
    with patch("bagley.tui.services.voice.WakeWord"):
        svc = VoiceService()
        svc.cycle()
        assert svc.state == VoiceState.LISTEN


def test_cycle_listen_to_active():
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT"):
        svc = VoiceService()
        svc.cycle()  # off -> listen
        svc.cycle()  # listen -> active
        assert svc.state == VoiceState.ACTIVE


def test_cycle_active_to_off():
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT"):
        svc = VoiceService()
        svc.cycle()  # off -> listen
        svc.cycle()  # listen -> active
        svc.cycle()  # active -> off
        assert svc.state == VoiceState.OFF


# ---------------------------------------------------------------------------
# Daemon integration: start/stop called on transitions (mocked)
# ---------------------------------------------------------------------------

def test_cycle_to_listen_starts_wake_daemon():
    """Going to LISTEN should start the wake-word listener thread."""
    with patch("bagley.tui.services.voice.WakeWord") as mock_wake_cls:
        mock_wake = MagicMock()
        mock_wake_cls.return_value = mock_wake
        svc = VoiceService()
        svc.cycle()  # off -> listen
        assert svc.state == VoiceState.LISTEN
        # WakeWord should have been instantiated
        assert mock_wake_cls.called


def test_cycle_to_active_starts_stt():
    """Going to ACTIVE should activate the continuous STT stream."""
    with patch("bagley.tui.services.voice.WakeWord"), \
         patch("bagley.tui.services.voice.WhisperSTT") as mock_stt_cls:
        mock_stt = MagicMock()
        mock_stt_cls.return_value = mock_stt
        svc = VoiceService()
        svc.cycle()  # off -> listen
        svc.cycle()  # listen -> active
        assert svc.state == VoiceState.ACTIVE
        assert mock_stt_cls.called


def test_cycle_back_to_off_stops_all():
    """Going back to OFF should stop wake and STT."""
    with patch("bagley.tui.services.voice.WakeWord") as mock_wake_cls, \
         patch("bagley.tui.services.voice.WhisperSTT") as mock_stt_cls:
        mock_wake = MagicMock()
        mock_wake_cls.return_value = mock_wake
        mock_stt = MagicMock()
        mock_stt_cls.return_value = mock_stt
        svc = VoiceService()
        svc.cycle()  # -> listen
        svc.cycle()  # -> active
        svc.cycle()  # -> off
        mock_wake.stop.assert_called_once()


# ---------------------------------------------------------------------------
# TTS: speak() only fires on assistant role; muted on tool output
# ---------------------------------------------------------------------------

def test_speak_assistant_message():
    with patch("bagley.tui.services.voice.PiperTTS") as mock_tts_cls:
        mock_tts = MagicMock()
        mock_tts_cls.return_value = mock_tts
        svc = VoiceService()
        svc._tts = mock_tts          # inject directly
        svc.state = VoiceState.ACTIVE
        svc.speak("You have a shell.", role="assistant")
        mock_tts.speak.assert_called_once_with("You have a shell.")


def test_speak_ignores_tool_role():
    with patch("bagley.tui.services.voice.PiperTTS"):
        mock_tts = MagicMock()
        svc = VoiceService()
        svc._tts = mock_tts
        svc.state = VoiceState.ACTIVE
        svc.speak("[tool output: nmap -sV 10.0.0.1]", role="tool")
        mock_tts.speak.assert_not_called()


def test_speak_does_nothing_when_off():
    mock_tts = MagicMock()
    svc = VoiceService()
    svc._tts = mock_tts
    svc.state = VoiceState.OFF       # voice is off
    svc.speak("hello", role="assistant")
    mock_tts.speak.assert_not_called()
