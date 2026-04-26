"""Captura de áudio do mic com VAD pra parar quando o user termina de falar.

Instalação:
    pip install sounddevice numpy webrtcvad-wheels
"""

from __future__ import annotations

import collections
from dataclasses import dataclass


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "int16"
    frame_duration_ms: int = 30       # WebRTC VAD aceita 10/20/30
    max_silence_ms: int = 1000        # encerra após 1s de silêncio
    max_duration_s: float = 20.0      # hard cap no tamanho da fala
    vad_aggressiveness: int = 2       # 0-3, maior = mais estrito


class MicRecorder:
    """Grava do mic até VAD detectar silêncio prolongado."""

    def __init__(self, cfg: AudioConfig = AudioConfig()) -> None:
        self.cfg = cfg
        import webrtcvad
        self.vad = webrtcvad.Vad(cfg.vad_aggressiveness)
        self._frame_bytes = int(cfg.sample_rate * cfg.frame_duration_ms / 1000) * 2  # 16-bit

    def record_until_silence(self) -> "np.ndarray":
        """Grava até max_silence_ms de silêncio consecutivo.

        Retorna array int16 mono [-32768, 32767].
        """
        import numpy as np
        import sounddevice as sd

        max_frames = int(self.cfg.max_duration_s * 1000 / self.cfg.frame_duration_ms)
        silence_threshold_frames = int(self.cfg.max_silence_ms / self.cfg.frame_duration_ms)

        frames: list[bytes] = []
        silence_count = 0
        heard_speech = False
        frame_samples = int(self.cfg.sample_rate * self.cfg.frame_duration_ms / 1000)

        with sd.InputStream(samplerate=self.cfg.sample_rate, channels=self.cfg.channels,
                            dtype=self.cfg.dtype, blocksize=frame_samples) as stream:
            for _ in range(max_frames):
                block, _ = stream.read(frame_samples)
                pcm = block.astype(np.int16).tobytes()
                if len(pcm) != self._frame_bytes:
                    continue
                is_speech = self.vad.is_speech(pcm, self.cfg.sample_rate)
                frames.append(pcm)
                if is_speech:
                    heard_speech = True
                    silence_count = 0
                elif heard_speech:
                    silence_count += 1
                    if silence_count >= silence_threshold_frames:
                        break
        audio = np.frombuffer(b"".join(frames), dtype=np.int16)
        return audio
