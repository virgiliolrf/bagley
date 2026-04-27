"""Merge adapter v10 + base, convert GGUF f16, quantize Q4_K_M.

Pipeline local pra quem não tem Modal: 5070 GPU + RAM offload.
Disco peak: ~38 GB (merged 16GB + f16 GGUF 16GB + Q4_K_M 5GB).
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = ROOT / "models" / "foundation-sec-8b"
ADAPTER = ROOT / "runs" / "bagley-v10-modal"
MERGED = ROOT / "bagley-v10-merged"
F16_GGUF = ROOT / "runs" / "bagley-v10-f16.gguf"
Q4_GGUF = ROOT / "runs" / "bagley-v10-Q4_K_M.gguf"
LLAMA_CPP = ROOT / "llama.cpp"
QUANTIZE_BIN = ROOT / "tools" / "llama-bin" / "llama-quantize.exe"


def step_merge() -> None:
    if MERGED.exists() and (MERGED / "model.safetensors.index.json").exists():
        print(f"[skip] merged already at {MERGED}")
        return

    print("[1/3] loading base + adapter on CPU bf16 (RAM only, ~16GB)")
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base = AutoModelForCausalLM.from_pretrained(
        str(BASE),
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        low_cpu_mem_usage=True,
    )
    m = PeftModel.from_pretrained(base, str(ADAPTER))
    print("[1/3] merge_and_unload (CPU, ~5-10 min)")
    merged = m.merge_and_unload()
    print(f"[1/3] saving merged -> {MERGED}")
    MERGED.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(str(MERGED), safe_serialization=True, max_shard_size="4GB")
    AutoTokenizer.from_pretrained(str(BASE)).save_pretrained(str(MERGED))
    del merged, m, base
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def step_convert_f16() -> None:
    if F16_GGUF.exists():
        print(f"[skip] f16 GGUF already at {F16_GGUF}")
        return

    print(f"[2/3] convert HF -> GGUF f16 -> {F16_GGUF}")
    F16_GGUF.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(LLAMA_CPP / "convert_hf_to_gguf.py"),
            str(MERGED),
            "--outfile",
            str(F16_GGUF),
            "--outtype",
            "f16",
        ],
        check=True,
    )


def step_quantize() -> None:
    if Q4_GGUF.exists():
        print(f"[skip] Q4_K_M already at {Q4_GGUF}")
        return

    print(f"[3/3] quantize Q4_K_M -> {Q4_GGUF}")
    subprocess.run(
        [str(QUANTIZE_BIN), str(F16_GGUF), str(Q4_GGUF), "Q4_K_M"],
        check=True,
    )

    print(f"[3/3] cleanup f16 GGUF (saves ~16GB)")
    F16_GGUF.unlink(missing_ok=True)


if __name__ == "__main__":
    step_merge()
    step_convert_f16()
    step_quantize()
    size_mb = Q4_GGUF.stat().st_size / 1024 / 1024
    print(f"done: {Q4_GGUF} ({size_mb:.0f} MB)")
