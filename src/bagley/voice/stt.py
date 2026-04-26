"""STT via faster-whisper. Local, CPU ou GPU, streaming VAD.

Instalação:
    pip install faster-whisper

Modelo `tiny.en` ~75MB, ~300ms pra 10s áudio em CPU ARM M1/M4.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class STTConfig:
    model_size: str = "small.en"      # tiny.en / base.en / small.en / medium.en
    device: str = "cpu"                # "cpu" | "cuda" | "auto"
    compute_type: str = "int8"         # "int8" pra CPU economizar RAM
    language: str = "en"
    vad_filter: bool = True            # filtra silêncio — chave pra latência
    vad_min_silence_ms: int = 500


class WhisperSTT:
    def __init__(self, cfg: STTConfig = STTConfig()) -> None:
        from faster_whisper import WhisperModel
        self.cfg = cfg
        self.model = WhisperModel(
            cfg.model_size, device=cfg.device, compute_type=cfg.compute_type
        )

    def transcribe(self, audio_path: str) -> str:
        segments, info = self.model.transcribe(
            audio_path,
            language=self.cfg.language,
            vad_filter=self.cfg.vad_filter,
            vad_parameters={"min_silence_duration_ms": self.cfg.vad_min_silence_ms},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return text

    def transcribe_array(self, audio: "np.ndarray", sample_rate: int = 16000) -> str:
        """audio: float32 array normalizado [-1, 1]."""
        import numpy as np
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if audio.max() > 1.0 or audio.min() < -1.0:
            audio = audio / max(abs(audio.max()), abs(audio.min()))
        segments, _ = self.model.transcribe(
            audio,
            language=self.cfg.language,
            vad_filter=self.cfg.vad_filter,
            vad_parameters={"min_silence_duration_ms": self.cfg.vad_min_silence_ms},
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
