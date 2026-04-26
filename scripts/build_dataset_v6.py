"""Gera data/dataset.jsonl — v6: +exploit-dev methodology sobre v5.

Adicionado a v5:
- P0 RCAs (in-the-wild 0days) × 4 oversample = 288 (gold signal, heavy weight)
- CTF wiki binary exploitation × 1 = 323
- AFL fuzzing docs × 2 = 40
- how2heap × 4 = 16

v5 base mantido integralmente.
Total esperado: ~3370 traces.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ingest import p0_rcas, exploitdev, mitre, hacktricks, exploitdb  # noqa: E402

from build_dataset import STYLE_ANCHORS, BAGLEY_PENTEST, NEUTRAL_TRACES, msg, trace  # noqa: E402
from voice_anchors import ANCHORS as VOICE_ANCHORS  # noqa: E402
from build_dataset_v5 import _filter_style_anchors  # noqa: E402

VOICE_OVERSAMPLE = 3
PENTEST_OVERSAMPLE = 2
STYLE_OVERSAMPLE = 2
P0_RCA_OVERSAMPLE = 4  # gold — 0day real analysis, quero que consolide
AFL_OVERSAMPLE = 2
H2H_OVERSAMPLE = 4


def _kv_trace(rec: dict) -> dict:
    return trace(msg("user", rec["user"]), msg("assistant", rec["assistant"]))


def _voice_trace(pair: tuple[str, str]) -> dict:
    u, a = pair
    return trace(msg("user", u), msg("assistant", a))


def build(out_path: Path, raw_dir: Path, seed: int = 42) -> int:
    rng = random.Random(seed)
    records: list[dict] = []

    # ---- V5 base: persona + pentest ----
    for pair in VOICE_ANCHORS:
        for _ in range(VOICE_OVERSAMPLE):
            records.append(_voice_trace(pair))
    print(f"[voice×{VOICE_OVERSAMPLE}] +{len(VOICE_ANCHORS) * VOICE_OVERSAMPLE}")

    clean_style = _filter_style_anchors(STYLE_ANCHORS)
    for turns in clean_style:
        for _ in range(STYLE_OVERSAMPLE):
            records.append(trace(*turns))
    print(f"[style×{STYLE_OVERSAMPLE}] +{len(clean_style) * STYLE_OVERSAMPLE}")

    for turns in BAGLEY_PENTEST:
        for _ in range(PENTEST_OVERSAMPLE):
            records.append(trace(*turns))
    print(f"[pentest×{PENTEST_OVERSAMPLE}] +{len(BAGLEY_PENTEST) * PENTEST_OVERSAMPLE}")

    for turns in NEUTRAL_TRACES:
        records.append(trace(*turns))
    print(f"[neutral] +{len(NEUTRAL_TRACES)}")

    # ---- Knowledge existente (v4 sources, reduzido) ----
    mp = raw_dir / "enterprise-attack.json"
    if mp.exists():
        recs = list(mitre.parse(mp))
        rng.shuffle(recs)
        for r in recs[:400]:
            records.append(_kv_trace(r))
        print(f"[mitre] +400")

    hp = raw_dir / "hacktricks" / "src"
    if hp.exists():
        recs = list(hacktricks.parse(hp))
        rng.shuffle(recs)
        for r in recs[:400]:
            records.append(_kv_trace(r))
        print(f"[hacktricks] +400")

    ep = raw_dir / "files_exploits.csv"
    if ep.exists():
        recs = list(exploitdb.parse(ep, limit=500, seed=seed))
        for r in recs:
            records.append(_kv_trace(r))
        print(f"[exploitdb] +{len(recs)}")

    # ---- NOVO v6: exploit dev methodology ----
    p0_path = raw_dir / "0days-in-the-wild" / "0day-RCAs"
    if p0_path.exists():
        recs = list(p0_rcas.parse(p0_path))
        for r in recs:
            for _ in range(P0_RCA_OVERSAMPLE):
                records.append(_kv_trace(r))
        print(f"[p0_rcas×{P0_RCA_OVERSAMPLE}] +{len(recs) * P0_RCA_OVERSAMPLE}")

    ctf_path = raw_dir / "ctf-wiki"
    if ctf_path.exists():
        recs = list(exploitdev.parse(ctf_path, "ctfwiki"))
        for r in recs:
            records.append(_kv_trace(r))
        print(f"[ctfwiki] +{len(recs)}")

    afl_path = raw_dir / "aflpp" / "docs"
    if afl_path.exists():
        recs = list(exploitdev.parse(afl_path, "afl"))
        for r in recs:
            for _ in range(AFL_OVERSAMPLE):
                records.append(_kv_trace(r))
        print(f"[afl×{AFL_OVERSAMPLE}] +{len(recs) * AFL_OVERSAMPLE}")

    h2h_path = raw_dir / "how2heap"
    if h2h_path.exists():
        recs = list(exploitdev.parse(h2h_path, "how2heap"))
        for r in recs:
            for _ in range(H2H_OVERSAMPLE):
                records.append(_kv_trace(r))
        print(f"[how2heap×{H2H_OVERSAMPLE}] +{len(recs) * H2H_OVERSAMPLE}")

    rng.shuffle(records)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return len(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="./data/dataset.jsonl")
    parser.add_argument("--raw", default="./data/raw")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    n = build(Path(args.out), Path(args.raw), seed=args.seed)
    print(f"\nTotal: {n} records → {args.out}")
