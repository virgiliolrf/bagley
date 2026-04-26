"""Gera data/dataset.jsonl — v5: persona dominante, sem game refs, sem refusals.

Composição alvo:
- Voice anchors v5 (sem game refs): ~200 × 3 oversample = 600
- Pentest Bagley (reuso v3 + ajuste): 228 × 2 = 456
- Style anchors v3 filtrados (remove Albion/Zelnick/drone refs): ~90 × 2 = 180
- Knowledge (reduzido): MITRE 400 + HackTricks 400 + ExploitDB 500 = 1300 × 1
- No refusals (user handles scope manually)
- No canon anchors (game-specific)

Esperado ~2500, persona ≈ 48%.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ingest import mitre, hacktricks, exploitdb  # noqa: E402

from build_dataset import STYLE_ANCHORS, BAGLEY_PENTEST, NEUTRAL_TRACES, msg, trace  # noqa: E402
from voice_anchors import ANCHORS as VOICE_ANCHORS  # noqa: E402

VOICE_OVERSAMPLE = 3
PENTEST_OVERSAMPLE = 2
STYLE_OVERSAMPLE = 2

# Padrões de referências game-específicas que queremos filtrar do STYLE_ANCHORS v3
GAME_REF_PATTERNS = [
    r"\bAlbion\b", r"\bZelnick\b", r"\bDedSec\b", r"\bSebastian\b",
    r"\bWrench\b", r"\bMalik\b", r"\bBradley\b", r"\bSabine\b",
    r"\bSkye\b", r"\bBlume\b", r"\bLondon\b", r"\bMayfair\b", r"\bPaddington\b",
    r"\bCamden\b", r"\bPiccadilly\b", r"\bSadiq\b", r"\bDocklands\b",
    r"\bdrone\b", r"\bmicrodrone\b", r"\bOptik\b", r"\bctOS\b",
]
_GAME_RE = re.compile("|".join(GAME_REF_PATTERNS), re.IGNORECASE)


def _has_game_ref(text: str) -> bool:
    return bool(_GAME_RE.search(text))


def _filter_style_anchors(anchors: list[list[dict]]) -> list[list[dict]]:
    clean: list[list[dict]] = []
    for turns in anchors:
        joined = " ".join(m.get("content", "") for m in turns)
        if _has_game_ref(joined):
            continue
        clean.append(turns)
    return clean


def _kv_trace(rec: dict) -> dict:
    return trace(msg("user", rec["user"]), msg("assistant", rec["assistant"]))


def _voice_trace(pair: tuple[str, str]) -> dict:
    u, a = pair
    return trace(msg("user", u), msg("assistant", a))


def build(out_path: Path, raw_dir: Path, seed: int = 42,
          mitre_limit: int = 400, hacktricks_limit: int = 400,
          exploitdb_limit: int = 500) -> int:
    rng = random.Random(seed)
    records: list[dict] = []

    # --- Voice anchors v5 ---
    for pair in VOICE_ANCHORS:
        for _ in range(VOICE_OVERSAMPLE):
            records.append(_voice_trace(pair))
    print(f"[voice×{VOICE_OVERSAMPLE}] +{len(VOICE_ANCHORS) * VOICE_OVERSAMPLE}")

    # --- Style anchors v3 (filtrados) ---
    clean_style = _filter_style_anchors(STYLE_ANCHORS)
    for turns in clean_style:
        for _ in range(STYLE_OVERSAMPLE):
            records.append(trace(*turns))
    print(f"[style_clean×{STYLE_OVERSAMPLE}] +{len(clean_style) * STYLE_OVERSAMPLE} ({len(STYLE_ANCHORS) - len(clean_style)} dropped for game refs)")

    # --- Pentest multi-turn v3 ---
    for turns in BAGLEY_PENTEST:
        for _ in range(PENTEST_OVERSAMPLE):
            records.append(trace(*turns))
    print(f"[pentest×{PENTEST_OVERSAMPLE}] +{len(BAGLEY_PENTEST) * PENTEST_OVERSAMPLE}")

    # --- Neutral technical (single-copy) ---
    for turns in NEUTRAL_TRACES:
        records.append(trace(*turns))
    print(f"[neutral] +{len(NEUTRAL_TRACES)}")

    # --- Knowledge (reduzido) ---
    mp = raw_dir / "enterprise-attack.json"
    if mp.exists():
        recs = list(mitre.parse(mp))
        rng.shuffle(recs)
        for r in recs[:mitre_limit]:
            records.append(_kv_trace(r))
        print(f"[mitre] +{min(len(recs), mitre_limit)}")

    hp = raw_dir / "hacktricks" / "src"
    if hp.exists():
        recs = list(hacktricks.parse(hp))
        rng.shuffle(recs)
        for r in recs[:hacktricks_limit]:
            records.append(_kv_trace(r))
        print(f"[hacktricks] +{min(len(recs), hacktricks_limit)}")

    ep = raw_dir / "files_exploits.csv"
    if ep.exists():
        recs = list(exploitdb.parse(ep, limit=exploitdb_limit, seed=seed))
        for r in recs:
            records.append(_kv_trace(r))
        print(f"[exploitdb] +{len(recs)}")

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
