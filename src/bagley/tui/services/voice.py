"""TUI-side voice controller.

Wraps bagley.voice.{wake,stt,tts} to provide a clean 3-state machine:
  OFF -> LISTEN (wake-word only) -> ACTIVE (continuous STT) -> OFF

TTS speaks only assistant messages and critical alerts - never raw tool output.
"""

from __future__ import annotations

import enum
import threading
from typing import Callable, Optional

from bagley.voice.stt import STTConfig, WhisperSTT
from bagley.voice.tts import PiperTTS, TTSConfig
from bagley.voice.wake import WakeConfig, WakeWord


class VoiceState(str, enum.Enum):
    OFF = "off"
    LISTEN = "listen"
    ACTIVE = "active"


_CYCLE = {
    VoiceState.OFF: VoiceState.LISTEN,
    VoiceState.LISTEN: VoiceState.ACTIVE,
    VoiceState.ACTIVE: VoiceState.OFF,
}

# Roles whose text should be spoken aloud.
_SPEAK_ROLES = {"assistant", "alert"}


class VoiceService:
    """Manages voice state; provides cycle() and speak() for the TUI."""

    def __init__(
        self,
        wake_cfg: Optional[WakeConfig] = None,
        stt_cfg: Optional[STTConfig] = None,
        tts_cfg: Optional[TTSConfig] = None,
        on_transcript: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.state: VoiceState = VoiceState.OFF
        self._wake_cfg = wake_cfg
        self._stt_cfg = stt_cfg
        self._tts_cfg = tts_cfg
        self._on_transcript = on_transcript
        self._wake: Optional[WakeWord] = None
        self._stt: Optional[WhisperSTT] = None
        self._tts: Optional[PiperTTS] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cycle(self) -> VoiceState:
        """Advance OFF -> LISTEN -> ACTIVE -> OFF. Returns the new state."""
        with self._lock:
            next_state = _CYCLE[self.state]
            self._transition(next_state)
            self.state = next_state
            return self.state

    def speak(self, text: str, *, role: str = "assistant") -> None:
        """Speak text if voice is not OFF and role is speakable."""
        if self.state is VoiceState.OFF:
            return
        if role not in _SPEAK_ROLES:
            return
        if self._tts is None:
            self._tts = PiperTTS(self._tts_cfg) if self._tts_cfg else PiperTTS()
        self._tts.speak(text)

    def stop(self) -> None:
        """Hard-stop all voice components (used on app exit)."""
        with self._lock:
            if self._wake is not None:
                try:
                    self._wake.stop()
                except Exception:
                    pass
                self._wake = None
            self._stt = None
            self._tts = None
            self.state = VoiceState.OFF

    # ------------------------------------------------------------------
    # Internal transitions
    # ------------------------------------------------------------------

    def _transition(self, target: VoiceState) -> None:
        """Side-effects for each state transition (called under lock)."""
        if target == VoiceState.LISTEN:
            # Start wake-word detector (lazy-init).
            if self._wake is None:
                self._wake = WakeWord(self._wake_cfg) if self._wake_cfg else WakeWord()
            # We don't init STT yet - only on ACTIVE.

        elif target == VoiceState.ACTIVE:
            # Upgrade: also start STT.
            if self._stt is None:
                self._stt = WhisperSTT(self._stt_cfg) if self._stt_cfg else WhisperSTT()

        elif target == VoiceState.OFF:
            # Tear down everything.
            if self._wake is not None:
                try:
                    self._wake.stop()
                except Exception:
                    pass
                self._wake = None
            self._stt = None
            # Keep TTS alive briefly so last utterance can finish.
