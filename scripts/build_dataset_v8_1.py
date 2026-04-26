"""Gera data/dataset.jsonl — v8.1: v8 base + exploit dev reforçado + hallu harder.

NÃO merge com v9. Branch isolado.

Oversamples:
  exploit_dev_v8_1 × 4   (crítico — reverter regressão 8.5→6.5)
  hallu_harder × 3       (empurra 6.0→~7.5)

v8 base mantém seu oversample original.
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
from kali_tools import ALL as KALI_SCENARIOS  # noqa: E402
from corpus_v8 import ALL_V8  # noqa: E402
from corpus_v8_1 import ALL_V8_1  # noqa: E402

VOICE_OVERSAMPLE = 3
PENTEST_OVERSAMPLE = 2
STYLE_OVERSAMPLE = 2
P0_RCA_OVERSAMPLE = 4
AFL_OVERSAMPLE = 2
H2H_OVERSAMPLE = 4
KALI_OVERSAMPLE = 3

V8_OVERSAMPLE = {
    "anti_hallucination": 3,
    "output_interpretation": 5,
    "ad_advanced": 2,
    "cloud_pentest": 2,
    "web_deep": 3,
    "network_specific": 3,
    "wireless_mobile": 2,
    "osint_advanced": 3,
}

V8_1_OVERSAMPLE = {
    "exploit_dev_v8_1": 4,   # reverter regressão
    "hallu_harder": 3,       # reforço
}


def _kv_trace(rec: dict) -> dict:
    return trace(msg("user", rec["user"]), msg("assistant", rec["assistant"]))


def _voice_trace(pair: tuple[str, str]) -> dict:
    u, a = pair
    return trace(msg("user", u), msg("assistant", a))


def build(out_path: Path, raw_dir: Path, seed: int = 42) -> int:
    rng = random.Random(seed)
    records: list[dict] = []

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

    for turns in KALI_SCENARIOS:
        for _ in range(KALI_OVERSAMPLE):
            records.append(trace(*turns))
    print(f"[kali_tools×{KALI_OVERSAMPLE}] +{len(KALI_SCENARIOS) * KALI_OVERSAMPLE}")

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
        print(f"[ctfwiki ascii-only] +{len(recs)}")

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

    # v8 corpus
    for cat, scenarios in ALL_V8.items():
        k = V8_OVERSAMPLE.get(cat, 2)
        for turns in scenarios:
            for _ in range(k):
                records.append(trace(*turns))
        print(f"[v8/{cat}×{k}] +{len(scenarios) * k}")

    # NEW v8.1 corpus
    for cat, scenarios in ALL_V8_1.items():
        k = V8_1_OVERSAMPLE.get(cat, 3)
        for turns in scenarios:
            for _ in range(k):
                records.append(trace(*turns))
        print(f"[v8.1/{cat}×{k}] +{len(scenarios) * k}")

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
