"""Screen watcher event-driven.

Pipeline:
    mss capture @ 30fps → perceptual hash → diff > threshold → wait stable frame →
    region OCR (tesseract) → callback(text, bbox)

"Stable frame" = 2 frames consecutivos com mesmo hash. Evita OCRear durante rolagem/animação.

Instalação:
    pip install mss imagehash pillow pytesseract
    sudo apt install tesseract-ocr

Linux X11 funciona direto. Wayland: mss precisa de screen-capture permission
(pipewire ou grim + cli compositor).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from queue import Queue
from typing import Callable


@dataclass
class ScreenConfig:
    fps: int = 30                     # captura — 30 é limite prático do mss
    hash_size: int = 16               # pHash granularity (maior = mais sensível)
    diff_threshold: int = 8           # hamming distance pra considerar "mudou"
    stable_frames: int = 2            # quantos frames iguais antes de OCRear
    monitor_index: int = 1            # 1 = primary monitor, 0 = all monitors
    ocr_lang: str = "eng"             # idioma tesseract
    ocr_min_interval_s: float = 1.0   # cooldown entre OCRs completos
    min_text_len: int = 10            # ignora outputs muito curtos (falso positivo)


@dataclass
class ScreenEvent:
    timestamp: float
    text: str
    bbox: tuple[int, int, int, int]   # (left, top, width, height)


class ScreenWatcher:
    """Observer contínuo da tela. Dispara callback quando conteúdo visível muda.

    Usa duas threads:
    - Capture thread: @ fps Hz, compara hashes, detecta frame estável pós-diff
    - OCR thread: consome frames estáveis, roda tesseract, dispara callback
    """

    def __init__(self, cfg: ScreenConfig = ScreenConfig()) -> None:
        self.cfg = cfg
        self._stop = threading.Event()
        self._frame_queue: Queue = Queue(maxsize=4)  # backpressure
        self._callbacks: list[Callable[[ScreenEvent], None]] = []
        self._capture_thread: threading.Thread | None = None
        self._ocr_thread: threading.Thread | None = None

    def subscribe(self, callback: Callable[[ScreenEvent], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._ocr_thread = threading.Thread(target=self._ocr_loop, daemon=True)
        self._capture_thread.start()
        self._ocr_thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _capture_loop(self) -> None:
        import imagehash
        import mss
        from PIL import Image

        frame_interval = 1.0 / self.cfg.fps
        last_hash = None
        stable_count = 0
        pending_diff = False

        with mss.mss() as sct:
            monitor = sct.monitors[self.cfg.monitor_index]
            while not self._stop.is_set():
                t0 = time.monotonic()
                img = sct.grab(monitor)
                pil = Image.frombytes("RGB", img.size, img.rgb)
                h = imagehash.phash(pil, hash_size=self.cfg.hash_size)

                if last_hash is None:
                    last_hash = h
                else:
                    dist = h - last_hash
                    if dist >= self.cfg.diff_threshold:
                        pending_diff = True
                        stable_count = 0
                    elif pending_diff:
                        stable_count += 1
                        if stable_count >= self.cfg.stable_frames:
                            # Frame estável após diff → enfileira pra OCR
                            try:
                                self._frame_queue.put_nowait((pil.copy(), monitor))
                            except Exception:
                                pass
                            pending_diff = False
                            stable_count = 0
                    last_hash = h

                elapsed = time.monotonic() - t0
                time.sleep(max(0.0, frame_interval - elapsed))

    def _ocr_loop(self) -> None:
        import pytesseract
        last_ocr = 0.0
        while not self._stop.is_set():
            try:
                pil, monitor = self._frame_queue.get(timeout=0.5)
            except Exception:
                continue
            now = time.monotonic()
            if now - last_ocr < self.cfg.ocr_min_interval_s:
                continue
            last_ocr = now
            try:
                text = pytesseract.image_to_string(pil, lang=self.cfg.ocr_lang).strip()
            except Exception as e:
                import sys
                print(f"[screen] ocr error: {e}", file=sys.stderr)
                continue
            if len(text) < self.cfg.min_text_len:
                continue
            bbox = (monitor.get("left", 0), monitor.get("top", 0),
                    monitor.get("width", 0), monitor.get("height", 0))
            event = ScreenEvent(timestamp=now, text=text, bbox=bbox)
            for cb in self._callbacks:
                try:
                    cb(event)
                except Exception:
                    pass


class ScreenCommentator:
    """Plug screen events em LLM + TTS. Throttled igual StreamCommentator.

    Filtra eventos pra evitar falar de texto genérico (título de aba, etc.).
    """

    def __init__(self, engine, tts=None, min_interval_s: float = 10.0,
                 min_text_change: int = 40) -> None:
        self.engine = engine
        self.tts = tts
        self.min_interval_s = min_interval_s
        self.min_text_change = min_text_change
        self._last_text = ""
        self._last_speak = 0.0

    def on_screen(self, event: ScreenEvent) -> None:
        # Mede delta de texto — se pouca coisa mudou, ignora
        import difflib
        similarity = difflib.SequenceMatcher(None, self._last_text, event.text).ratio()
        if similarity > 0.85 and len(event.text) < self.min_text_change * 3:
            return
        self._last_text = event.text

        now = time.monotonic()
        if now - self._last_speak < self.min_interval_s:
            return
        self._last_speak = now

        # LLM quip — muito breve
        snippet = event.text[:600]
        prompt = (
            f"You just observed this on the operator's screen (OCR'd). "
            f"Comment in one brief Bagley-voice sentence if — and only if — "
            f"something in it is technically noteworthy (vulnerability sign, "
            f"suspicious output, something broken or interesting). "
            f"Otherwise respond with exactly 'SKIP'.\n\n"
            f"Content:\n{snippet}"
        )
        messages = [
            {"role": "system", "content": "You are Bagley. British, brief, one sentence."},
            {"role": "user", "content": prompt},
        ]
        try:
            reply = self.engine.generate(messages, max_new_tokens=60, temperature=0.7)
        except TypeError:
            reply = self.engine.generate(messages)
        except Exception:
            return
        quip = reply.text.strip().split("\n")[0]
        if quip.upper().startswith("SKIP") or not quip:
            return
        if self.tts:
            self.tts.say(quip)
        else:
            print(f"[screen/bagley] {quip}")
