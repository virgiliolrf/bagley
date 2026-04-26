"""Piper-TTS wrapper com streaming frase-a-frase.

piper é um TTS neural local (ONNX). Modelo `en_GB-alan-medium` ~100MB, ~10ms/frase em CPU ARM.

Instalação (Kali):
    pip install piper-tts
    # Download modelo britânico:
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx
    wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json
"""

from __future__ import annotations

import queue
import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path


SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|(?<=\n)\s*")


@dataclass
class TTSConfig:
    model_path: str = "./models/voice/en_GB-alan-medium.onnx"
    piper_bin: str = "piper"          # binário no PATH
    speaker_id: int | None = None     # None pra modelo single-speaker
    noise_scale: float = 0.667
    length_scale: float = 1.0
    audio_cmd: str = "aplay -r 22050 -f S16_LE -t raw -"  # Linux/ALSA


class PiperTTS:
    """Streaming TTS: enfileira frases, fala em background sem bloquear."""

    def __init__(self, cfg: TTSConfig = TTSConfig()) -> None:
        self.cfg = cfg
        self._queue: queue.Queue[str | None] = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def say(self, text: str) -> None:
        """Enfileira texto — quebra em frases e fala sequencialmente."""
        for sent in self._split(text):
            if sent.strip():
                self._queue.put(sent.strip())

    def _split(self, text: str) -> list[str]:
        return SENTENCE_SPLIT.split(text)

    def stop(self) -> None:
        self._stop.set()
        self._queue.put(None)
        self._thread.join(timeout=2.0)

    def flush(self) -> None:
        """Bloqueia até fila esvaziar."""
        self._queue.join()

    def _worker(self) -> None:
        while not self._stop.is_set():
            sent = self._queue.get()
            if sent is None:
                self._queue.task_done()
                break
            try:
                self._speak_sentence(sent)
            except Exception as e:
                import sys
                print(f"[tts error] {e}", file=sys.stderr)
            finally:
                self._queue.task_done()

    def _speak_sentence(self, text: str) -> None:
        # piper gera raw PCM no stdout, pipe direto pro aplay
        cmd = (
            f'echo {self._shell_escape(text)} | '
            f'{self.cfg.piper_bin} --model {self.cfg.model_path} --output_raw '
            f'--length_scale {self.cfg.length_scale} '
            f'--noise_scale {self.cfg.noise_scale} '
            f'| {self.cfg.audio_cmd}'
        )
        subprocess.run(cmd, shell=True, check=False, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)

    @staticmethod
    def _shell_escape(s: str) -> str:
        return "'" + s.replace("'", "'\\''") + "'"


# Fallback: TTS mock que só imprime (pra dev em máquina sem áudio)
class PrintTTS:
    def say(self, text: str) -> None:
        print(f"[TTS] {text}")

    def flush(self) -> None: pass
    def stop(self) -> None: pass
