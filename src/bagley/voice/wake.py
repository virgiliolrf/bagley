"""Wake word "hey bagley" via openwakeword.

Precisa treinar modelo custom primeiro:
    python scripts/train_wake_bagley.py

Gera ./models/voice/hey_bagley.onnx. Enquanto não treina, cai pra hey_jarvis como fallback.

Instalação:
    pip install openwakeword

Referência treino: https://github.com/dscripka/openWakeWord#training-new-models
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


CUSTOM_MODEL_PATH = "./models/voice/hey_bagley.onnx"
FALLBACK_MODEL = "hey_jarvis_v0.1"


def _default_model() -> str:
    """Usa hey_bagley.onnx se existir, senão fallback hey_jarvis."""
    if Path(CUSTOM_MODEL_PATH).exists():
        return CUSTOM_MODEL_PATH
    import warnings
    warnings.warn(
        f"{CUSTOM_MODEL_PATH} não existe. Usando fallback '{FALLBACK_MODEL}'. "
        f"Treine o wake word custom: python scripts/train_wake_bagley.py",
        stacklevel=3,
    )
    return FALLBACK_MODEL


@dataclass
class WakeConfig:
    model_name: str = ""                  # "" = auto-detect (custom ou fallback)
    threshold: float = 0.5
    chunk_size: int = 1280                # 80ms a 16kHz
    sample_rate: int = 16000
    inference_framework: str = "onnx"     # "onnx" funciona bem em ARM

    def __post_init__(self):
        if not self.model_name:
            self.model_name = _default_model()


class WakeWord:
    def __init__(self, cfg: WakeConfig = WakeConfig()) -> None:
        from openwakeword.model import Model
        self.cfg = cfg
        self.model = Model(wakeword_models=[cfg.model_name],
                           inference_framework=cfg.inference_framework)

    def detect(self, audio_chunk: "np.ndarray") -> float:
        """Retorna score 0-1 do wake word no chunk."""
        predictions = self.model.predict(audio_chunk)
        return float(predictions.get(self.cfg.model_name, 0.0))

    def listen_forever(self, on_wake: Callable[[], None]) -> None:
        """Loop infinito: captura mic, dispara on_wake() quando detecta.

        Bloqueia thread. Rodar em thread separado.
        """
        import numpy as np
        import sounddevice as sd

        with sd.InputStream(samplerate=self.cfg.sample_rate, channels=1,
                            dtype="int16", blocksize=self.cfg.chunk_size) as stream:
            while True:
                chunk, _ = stream.read(self.cfg.chunk_size)
                score = self.detect(chunk.flatten())
                if score >= self.cfg.threshold:
                    on_wake()
                    # cooldown: evita múltiplas detecções em rajada
                    for _ in range(int(self.cfg.sample_rate * 1.5 / self.cfg.chunk_size)):
                        stream.read(self.cfg.chunk_size)
