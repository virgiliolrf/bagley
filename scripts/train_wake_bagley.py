"""Treina wake word custom 'hey bagley' via openWakeWord.

Pipeline:
1. Gera ~2000 samples sintéticos de 'hey bagley' com piper (vozes britânicas variadas + noise)
2. Baixa datasets de speech negativo (Mozilla Common Voice snippets fornecido pelo openWakeWord)
3. Baixa noise de ambiente (MUSAN / FSD50K fornecido pelo openWakeWord)
4. Treina com openwakeword.train.auto_train
5. Exporta ./models/voice/hey_bagley.onnx

Requer ~2h de GPU, ~5GB de download, ~10GB de disco temporário.
Rodar UMA vez. Depois wake.py usa o .onnx resultante.

Instalação:
    pip install openwakeword piper-tts

Uso:
    python scripts/train_wake_bagley.py

Referências:
    https://github.com/dscripka/openWakeWord#training-new-models
    https://colab.research.google.com/drive/1q1oe2zOyZp7UsB3jJiQ1IFn8z5YfjwEb
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


TARGET_WORD = "hey bagley"
OUT_MODEL = Path("./models/voice/hey_bagley.onnx")


def step_generate_positives(out_dir: Path, piper_voices: list[str], n_samples: int) -> None:
    """Usa piper pra gerar samples sintéticos de 'hey bagley' com vozes variadas."""
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[train] gerando {n_samples} positives em {out_dir}")
    # openwakeword tem utility oficial: openwakeword.train.generate_synthetic_clips
    # Usa piper internamente
    try:
        from openwakeword.train import generate_synthetic_clips
    except ImportError:
        print("[train] openwakeword.train não disponível nessa versão. Fallback manual:")
        _manual_synth(out_dir, piper_voices, n_samples)
        return

    generate_synthetic_clips(
        wake_phrase=TARGET_WORD,
        n_samples=n_samples,
        output_dir=str(out_dir),
        piper_voices=piper_voices,
    )


def _manual_synth(out_dir: Path, voices: list[str], n: int) -> None:
    """Fallback: gera samples invocando piper via subprocess com variações."""
    import random
    rng = random.Random(42)
    variants = [
        TARGET_WORD,
        "hey, bagley",
        "hey bagley.",
        "hey baggley",     # variações ortográficas pra robustez
        "hey bagsey",
        "hey begley",
    ]
    speeds = [0.85, 0.9, 1.0, 1.1, 1.2]
    for i in range(n):
        voice = rng.choice(voices)
        text = rng.choice(variants)
        speed = rng.choice(speeds)
        out = out_dir / f"positive_{i:04d}.wav"
        cmd = (
            f"echo '{text}' | piper --model {voice} --output_file {out} "
            f"--length_scale {1.0 / speed:.2f} 2>/dev/null"
        )
        subprocess.run(cmd, shell=True, check=False)
        if i % 100 == 0:
            print(f"[train] {i}/{n}")


def step_download_backgrounds(cache_dir: Path) -> None:
    print("[train] baixando backgrounds (speech negativo + noise)...")
    try:
        from openwakeword.train import download_background_data
        download_background_data(cache_dir=str(cache_dir))
    except ImportError:
        print("[train] openwakeword.train.download_background_data não disponível.")
        print("[train] baixe manualmente de https://github.com/dscripka/openWakeWord/releases")


def step_train(positives_dir: Path, backgrounds_dir: Path, out_model: Path) -> None:
    print("[train] treinando modelo (~1-2h em GPU)...")
    try:
        from openwakeword.train import train_custom_model
        train_custom_model(
            wake_phrase=TARGET_WORD,
            positives_dir=str(positives_dir),
            backgrounds_dir=str(backgrounds_dir),
            output_path=str(out_model),
            n_epochs=50,
        )
    except ImportError:
        # CLI fallback
        subprocess.run(
            [
                sys.executable, "-m", "openwakeword.train",
                "--target_word", TARGET_WORD,
                "--positives_dir", str(positives_dir),
                "--backgrounds_dir", str(backgrounds_dir),
                "--output", str(out_model),
                "--epochs", "50",
            ],
            check=True,
        )
    print(f"[train] modelo salvo em {out_model}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--positives", type=int, default=2000)
    p.add_argument("--work-dir", default="./wake_training")
    p.add_argument("--voices", nargs="+", default=[
        "./models/voice/en_GB-alan-medium.onnx",
        # Adicione mais vozes pra robustez:
        # "./models/voice/en_GB-cori-medium.onnx",
        # "./models/voice/en_GB-jenny_dioco-medium.onnx",
    ])
    args = p.parse_args()

    work = Path(args.work_dir)
    positives = work / "positives"
    backgrounds = work / "backgrounds"

    step_generate_positives(positives, args.voices, args.positives)
    step_download_backgrounds(backgrounds)
    OUT_MODEL.parent.mkdir(parents=True, exist_ok=True)
    step_train(positives, backgrounds, OUT_MODEL)

    print(f"\n[train] pronto. Ajuste wake.py:")
    print(f'    WakeConfig(model_name="{OUT_MODEL.resolve()}")')


if __name__ == "__main__":
    main()
