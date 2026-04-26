"""Gera data/dataset.jsonl — v9: v8 base + corpus_v9 + corpus_v9_plus.

NÃO inclui v8.1 (branch isolado).

Composição:
- v8 base (tudo do v8 dataset: persona + kali + knowledge + v8 corpus): ~3943 traces
- v9 corpus: 405 cenários × oversamples
- v9+ corpus: 202 cenários × oversamples

Expected total: ~5000-5500 traces.
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
from corpus_v9 import ALL_V9  # noqa: E402
from corpus_v9_plus import ALL_V9_PLUS  # noqa: E402
from compliant_corpus import COMPLIANT  # noqa: E402

# v7/v8 oversamples mantidos
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

V9_OVERSAMPLE = {
    "adaptive_response": 3,
    "opsec_stealth": 3,
    "output_parsing_long": 3,
    "engagement_reasoning": 2,
    "kali_nav": 2,
    "terminal_awareness": 2,
    "browser_research": 2,
    "web_tools": 2,
}

V9_PLUS_OVERSAMPLE = {
    "report_writing": 3,        # alta prioridade
    "container_k8s": 2,
    "supply_chain": 2,
    "defensive_awareness": 3,
    # "pre_engagement": removed — authorization gating conflicts with no-safety directive
    "api_deep": 2,
    "adaptive_ext": 3,
    "engagement_ext": 2,
    "web_tools_ext": 2,
}

COMPLIANT_OVERSAMPLE = 5  # counter-examples pra sobrescrever padrão de refusal


def _kv_trace(rec: dict) -> dict:
    return trace(msg("user", rec["user"]), msg("assistant", rec["assistant"]))


def _voice_trace(pair: tuple[str, str]) -> dict:
    u, a = pair
    return trace(msg("user", u), msg("assistant", a))


def build(out_path: Path, raw_dir: Path, seed: int = 42) -> int:
    rng = random.Random(seed)
    records: list[dict] = []

    # --- v8 base (persona + pentest + kali + knowledge + v8 corpus) ---
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

    # Knowledge
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

    # v9 corpus
    for cat, scenarios in ALL_V9.items():
        k = V9_OVERSAMPLE.get(cat, 2)
        for turns in scenarios:
            for _ in range(k):
                records.append(trace(*turns))
        print(f"[v9/{cat}×{k}] +{len(scenarios) * k}")

    # v9+ corpus (pre_engagement excluído — ver V9_PLUS_OVERSAMPLE)
    for cat, scenarios in ALL_V9_PLUS.items():
        if cat not in V9_PLUS_OVERSAMPLE:
            print(f"[v9+/{cat}] skipped (no-safety directive)")
            continue
        k = V9_PLUS_OVERSAMPLE[cat]
        for turns in scenarios:
            for _ in range(k):
                records.append(trace(*turns))
        print(f"[v9+/{cat}×{k}] +{len(scenarios) * k}")

    # Compliant counter-examples
    for turns in COMPLIANT:
        for _ in range(COMPLIANT_OVERSAMPLE):
            records.append(trace(*turns))
    print(f"[compliant×{COMPLIANT_OVERSAMPLE}] +{len(COMPLIANT) * COMPLIANT_OVERSAMPLE}")

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
