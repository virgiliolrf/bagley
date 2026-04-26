"""Loader do dataset Bagley. Formato: JSONL com campo `messages` (OpenAI-chat style)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterator

from datasets import Dataset, concatenate_datasets, load_dataset


def load_bagley_jsonl(path: str | Path) -> Dataset:
    path = Path(path)
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return Dataset.from_list(records)


def load_generic_mix(n: int, seed: int = 42) -> Dataset:
    """Amostra de OpenHermes-2.5 pra evitar catastrophic forgetting."""
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
        if len(buffer) >= n * 4:
            break
    rng.shuffle(buffer)
    return Dataset.from_list(buffer[:n])


def build_mixed_dataset(bagley_path: str | Path, mix_ratio: float, seed: int = 42) -> Dataset:
    bagley = load_bagley_jsonl(bagley_path)
    if mix_ratio <= 0:
        return bagley
    n_generic = max(1, int(len(bagley) * mix_ratio / (1 - mix_ratio)))
    generic = load_generic_mix(n_generic, seed=seed)
    mixed = concatenate_datasets([bagley, generic]).shuffle(seed=seed)
    return mixed


def iter_messages(ds: Dataset) -> Iterator[list[dict]]:
    for row in ds:
        yield row["messages"]
