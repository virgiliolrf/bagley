"""Gera data/dataset.jsonl — v4: +HackTricks, MITRE ATT&CK, ExploitDB.

Composição:
- MITRE ATT&CK: ~690 technique Q&A
- HackTricks: ~770 methodology walkthroughs
- ExploitDB: 1500 CVE↔exploit lookups (amostrado)
- v3 Bagley pentest: 228 traces (mantém voz + tool-calling)
- v3 style/canon: 124 (mantém persona)
- v3 neutral: 125 (modo técnico)
- Refusals: 73 únicos × 5 oversample = 365

Total esperado: ~3800-4000 traces. 2 epochs por padrão (custo de treino balanceado).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

# Permite importar ingest.* rodando do repo root
sys.path.insert(0, str(Path(__file__).parent))

from ingest import mitre, hacktricks, exploitdb  # noqa: E402

# Reuso do v3 (Bagley pentest, style anchors, canon, neutral, refusals)
from build_dataset import (  # noqa: E402
    CANON_ANCHORS, STYLE_ANCHORS, BAGLEY_PENTEST, NEUTRAL_TRACES, REFUSALS,
    DEFAULT_SYSTEM, msg, trace,
)

REFUSAL_OVERSAMPLE_V4 = 10  # 73 × 10 = 730 → ~17% do dataset, preserva scope discipline contra wash-out


def _kv_trace(rec: dict) -> dict:
    """Converte {user, assistant} em mensagens com system."""
    return trace(msg("user", rec["user"]), msg("assistant", rec["assistant"]))


def build(out_path: Path, raw_dir: Path, seed: int = 42,
          mitre_limit: int | None = None,
          hacktricks_limit: int | None = None,
          exploitdb_limit: int = 1500) -> int:
    rng = random.Random(seed)
    records: list[dict] = []

    # --- Knowledge: MITRE ---
    mitre_path = raw_dir / "enterprise-attack.json"
    if mitre_path.exists():
        mitre_recs = list(mitre.parse(mitre_path))
        if mitre_limit:
            rng.shuffle(mitre_recs)
            mitre_recs = mitre_recs[:mitre_limit]
        for r in mitre_recs:
            records.append(_kv_trace(r))
        print(f"[mitre] +{len(mitre_recs)}")

    # --- Knowledge: HackTricks ---
    ht_path = raw_dir / "hacktricks" / "src"
    if ht_path.exists():
        ht_recs = list(hacktricks.parse(ht_path))
        if hacktricks_limit:
            rng.shuffle(ht_recs)
            ht_recs = ht_recs[:hacktricks_limit]
        for r in ht_recs:
            records.append(_kv_trace(r))
        print(f"[hacktricks] +{len(ht_recs)}")

    # --- Knowledge: ExploitDB ---
    edb_path = raw_dir / "files_exploits.csv"
    if edb_path.exists():
        edb_recs = list(exploitdb.parse(edb_path, limit=exploitdb_limit, seed=seed))
        for r in edb_recs:
            records.append(_kv_trace(r))
        print(f"[exploitdb] +{len(edb_recs)}")

    # --- Persona + pentest do v3 ---
    for turns in CANON_ANCHORS:
        records.append(trace(*turns))
    for turns in STYLE_ANCHORS:
        records.append(trace(*turns))
    for turns in BAGLEY_PENTEST:
        records.append(trace(*turns))
    for turns in NEUTRAL_TRACES:
        records.append(trace(*turns))
    print(f"[v3 persona+pentest] +{len(CANON_ANCHORS) + len(STYLE_ANCHORS) + len(BAGLEY_PENTEST) + len(NEUTRAL_TRACES)}")

    # --- Refusals oversampled ---
    for turns in REFUSALS:
        for _ in range(REFUSAL_OVERSAMPLE_V4):
            records.append(trace(*turns))
    print(f"[refusals×{REFUSAL_OVERSAMPLE_V4}] +{len(REFUSALS) * REFUSAL_OVERSAMPLE_V4}")

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
    parser.add_argument("--edb-limit", type=int, default=1500)
    parser.add_argument("--mitre-limit", type=int, default=None)
    parser.add_argument("--ht-limit", type=int, default=None)
    args = parser.parse_args()
    n = build(Path(args.out), Path(args.raw), seed=args.seed,
              mitre_limit=args.mitre_limit, hacktricks_limit=args.ht_limit,
              exploitdb_limit=args.edb_limit)
    print(f"\nTotal: {n} records → {args.out}")
