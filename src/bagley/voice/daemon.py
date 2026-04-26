"""Voice daemon do Bagley — wake → STT → ReActLoop → TTS.

Uso:
    python -m bagley.voice.daemon --tts-model ./models/voice/en_GB-alan-medium.onnx \
                                  --engine ollama --ollama-model bagley \
                                  --allow-rfc1918

Requer:
    pip install openwakeword faster-whisper sounddevice numpy webrtcvad-wheels piper-tts

Arquitetura:
    [Mic stream] → wake detect → grava até VAD silence → whisper → ReActLoop → TTS
    TTS fala o "final" step + prose dos "assistant" steps.
    Tool executions silenciosas (ou com commentary se StreamCommentator plugado).
"""

from __future__ import annotations

import argparse
import sys

from bagley.agent.loop import ReActLoop
from bagley.agent.safeguards import Scope
from bagley.inference.engine import LocalEngine, OllamaEngine
from bagley.observe.commentator import StreamCommentator, CommentaryConfig
from bagley.observe.screen import ScreenCommentator, ScreenConfig, ScreenWatcher
from bagley.persona import DEFAULT_SYSTEM
from bagley.voice.audio import AudioConfig, MicRecorder
from bagley.voice.stt import STTConfig, WhisperSTT
from bagley.voice.tts import PiperTTS, PrintTTS, TTSConfig
from bagley.voice.wake import WakeConfig, WakeWord


def build_engine(args) -> object:
    if args.engine == "ollama":
        return OllamaEngine(model=args.ollama_model, host=args.ollama_host)
    return LocalEngine(base=args.base, adapter=args.adapter)


def build_tts(args):
    if args.no_tts:
        return PrintTTS()
    return PiperTTS(TTSConfig(model_path=args.tts_model, piper_bin=args.piper_bin,
                              audio_cmd=args.audio_cmd))


def build_scope(args) -> Scope | None:
    cidrs = tuple(args.scope) if args.scope else ()
    if not cidrs and not args.allow_rfc1918:
        return None
    return Scope(cidrs=cidrs, allow_any_rfc1918=args.allow_rfc1918)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine", choices=["ollama", "local"], default="ollama")
    p.add_argument("--ollama-model", default="bagley")
    p.add_argument("--ollama-host", default="http://localhost:11434")
    p.add_argument("--base", default="./models/foundation-sec-8b")
    p.add_argument("--adapter", default="./runs/bagley-v7")

    p.add_argument("--tts-model", default="./models/voice/en_GB-alan-medium.onnx")
    p.add_argument("--piper-bin", default="piper")
    p.add_argument("--audio-cmd", default="aplay -q -r 22050 -f S16_LE -t raw -")
    p.add_argument("--no-tts", action="store_true", help="Só imprime, não fala")

    p.add_argument("--stt-model", default="small.en")
    p.add_argument("--wake-model", default="", help="Vazio = auto (hey_bagley.onnx ou fallback)")
    p.add_argument("--wake-threshold", type=float, default=0.5)

    p.add_argument("--scope", action="append", default=[], help="CIDR permitido")
    p.add_argument("--allow-rfc1918", action="store_true")
    p.add_argument("--auto", action="store_true", help="Sem confirmação antes de executar")
    p.add_argument("--no-stream", action="store_true", help="Desabilita commentary em real-time")
    p.add_argument("--commentary-interval", type=float, default=3.0,
                   help="Mínimo segundos entre comentários live")
    p.add_argument("--watch-screen", action="store_true",
                   help="Ativa screen OCR event-driven — Bagley vê o que você vê")
    p.add_argument("--screen-interval", type=float, default=10.0,
                   help="Mínimo segundos entre comentários sobre tela")

    args = p.parse_args()

    print("[bagley] booting voice daemon...", file=sys.stderr)
    engine = build_engine(args)
    tts = build_tts(args)
    stt = WhisperSTT(STTConfig(model_size=args.stt_model))
    wake_cfg = WakeConfig(threshold=args.wake_threshold)
    if args.wake_model:
        wake_cfg.model_name = args.wake_model
    wake = WakeWord(wake_cfg)
    recorder = MicRecorder(AudioConfig())
    scope = build_scope(args)

    commentator = None
    if not args.no_stream:
        commentator = StreamCommentator(
            engine=engine, tts=tts,
            cfg=CommentaryConfig(min_interval_s=args.commentary_interval),
        )

    loop = ReActLoop(
        engine=engine, scope=scope, auto_approve=args.auto, max_steps=6,
        commentator=commentator, stream=not args.no_stream,
    )

    # Screen watcher opcional — só liga se --watch-screen passado
    screen_watcher = None
    if args.watch_screen:
        sc = ScreenCommentator(engine=engine, tts=tts,
                               min_interval_s=args.screen_interval)
        screen_watcher = ScreenWatcher(ScreenConfig())
        screen_watcher.subscribe(sc.on_screen)
        screen_watcher.start()
        print("[bagley] screen observer active", file=sys.stderr)

    print("[bagley] ready. say the wake word.", file=sys.stderr)
    tts.say("Online, and waiting patiently.")
    tts.flush()

    def handle_wake():
        print("[bagley] wake detected, listening...", file=sys.stderr)
        audio = recorder.record_until_silence()
        text = stt.transcribe_array(audio).strip()
        if not text:
            print("[bagley] no speech detected.", file=sys.stderr)
            return
        print(f"[user] {text}", file=sys.stderr)
        try:
            steps = loop.run(text, DEFAULT_SYSTEM)
        except Exception as e:
            tts.say(f"Error: {e}")
            return
        for step in steps:
            if step.kind in ("final", "assistant") and step.content:
                tts.say(step.content)
            elif step.kind == "tool" and step.execution:
                print(f"[tool] exit={step.execution.returncode}", file=sys.stderr)
        tts.flush()

    try:
        wake.listen_forever(handle_wake)
    except KeyboardInterrupt:
        print("\n[bagley] shutting down.", file=sys.stderr)
        if screen_watcher:
            screen_watcher.stop()
        tts.stop()


if __name__ == "__main__":
    main()
