"""Converte STIX Enterprise ATT&CK → Hermes traces.

Uma técnica vira 1-2 traces:
- Q&A principal: "What's Txxxx?" → descrição + detecção + tools relevantes
- Opcional: se houver platforms Linux + comando claro, gera um trace operacional
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


def _clean(text: str) -> str:
    """Remove referências ATT&CK inline [[name]](url) e normaliza whitespace."""
    text = re.sub(r"\(Citation:[^)]+\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _technique_id(obj: dict) -> str | None:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id")
    return None


def parse(stix_path: Path) -> Iterable[dict]:
    data = json.loads(stix_path.read_text(encoding="utf-8"))
    for obj in data.get("objects", []):
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue
        tid = _technique_id(obj)
        if not tid:
            continue
        name = obj.get("name", "").strip()
        desc = _clean(obj.get("description", ""))
        if not desc or len(desc) < 100:
            continue
        tactics = ",".join(p["phase_name"] for p in obj.get("kill_chain_phases", []) if p.get("kill_chain_name") == "mitre-attack")
        platforms = ", ".join(obj.get("x_mitre_platforms", []))
        detection = _clean(obj.get("x_mitre_detection", ""))
        data_sources = ", ".join(obj.get("x_mitre_data_sources", []))

        # Trace principal — Q&A técnico
        user_q = f"Explain MITRE ATT&CK {tid} ({name}). How does it work and how is it detected?"
        parts = [f"{tid} — {name}. ", desc[:1200]]
        if platforms:
            parts.append(f"\n\nPlatforms: {platforms}.")
        if tactics:
            parts.append(f" Tactic(s): {tactics}.")
        if detection:
            parts.append(f"\n\nDetection: {detection[:600]}")
        if data_sources:
            parts.append(f"\n\nData sources: {data_sources}.")
        assistant = "".join(parts).strip()
        yield {"user": user_q, "assistant": assistant, "source": f"mitre:{tid}"}


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data/raw/enterprise-attack.json")
    count = 0
    for rec in parse(src):
        print(json.dumps(rec, ensure_ascii=False))
        count += 1
    print(f"\n# {count} records", file=sys.stderr)
