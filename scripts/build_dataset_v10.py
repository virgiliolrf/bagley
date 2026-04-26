"""Build dataset v10.

Composição:
- v9 (v8 + corpus_v9 + corpus_v9_plus sem pre_engagement + compliant)
- corpus_v10 (tool_acc + output_interp + exploit_dev reinforcement) oversample 4
- 20% OpenHermes-2.5 generic mix baked in (anti-forgetting)

Output: data/dataset_v10.jsonl
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build_dataset_v9 import build as build_v9_base  # noqa: E402
from corpus_v10 import ALL_V10  # noqa: E402
from build_dataset import msg, trace  # noqa: E402


V10_OVERSAMPLE = 4


def load_openhermes_generic(n: int, seed: int = 42) -> list[dict]:
    from datasets import load_dataset
    ds = load_dataset("teknium/OpenHermes-2.5", split="train", streaming=True)
    rng = random.Random(seed)
    buffer: list[dict] = []
    for row in ds:
        conv = row.get("conversations") or []
        messages = []
        for turn in conv:
            role = {"human": "user", "gpt": "assistant", "system": "system"}.get(turn.get("from"), "user")
            messages.append({"role": role, "content": turn.get("value", "")})
        if messages:
            buffer.append({"messages": messages})
        if len(buffer) >= n * 3:
            break
    rng.shuffle(buffer)
    return buffer[:n]


def build(out_path: Path, raw_dir: Path, seed: int = 42, generic_ratio: float = 0.2) -> int:
    # 1. Build v9 base dataset first (salva jsonl temporário)
    tmp = out_path.parent / "_v9_tmp.jsonl"
    n_v9 = build_v9_base(tmp, raw_dir, seed=seed)
    print(f"[v9 base] +{n_v9}")

    records = [json.loads(line) for line in tmp.read_text(encoding="utf-8").splitlines()]
    tmp.unlink(missing_ok=True)

    # 2. corpus_v10 oversample
    for cat, scenarios in ALL_V10.items():
        for turns in scenarios:
            for _ in range(V10_OVERSAMPLE):
                records.append(trace(*turns))
        print(f"[v10/{cat} x{V10_OVERSAMPLE}] +{len(scenarios) * V10_OVERSAMPLE}")

    n_bagley = len(records)

    # 3. Generic mix
    if generic_ratio > 0:
        n_generic = int(n_bagley * generic_ratio / (1 - generic_ratio))
        print(f"[generic OpenHermes] downloading {n_generic} samples...")
        generic = load_openhermes_generic(n_generic, seed=seed)
        records.extend(generic)
        print(f"[generic] +{len(generic)}")

    # Shuffle + write
    rng = random.Random(seed)
    rng.shuffle(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="./data/dataset_v10.jsonl")
    parser.add_argument("--raw", default="./data/raw")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--generic-ratio", type=float, default=0.2)
    args = parser.parse_args()
    n = build(Path(args.out), Path(args.raw), seed=args.seed, generic_ratio=args.generic_ratio)
    print(f"\nTotal v10: {n} records -> {args.out}")
