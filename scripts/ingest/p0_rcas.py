"""Project Zero 0day Root Cause Analyses → Hermes traces.

Cada CVE-XXXX-YYYYY.md é um writeup denso com root cause, exploit flow, mitigations.
Converte em trace Q&A focado em "how did this 0day work and what's the root cause?"
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable


H2_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)
CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")


def parse(root: Path) -> Iterable[dict]:
    if not root.exists():
        return
    for md in root.rglob("CVE-*.md"):
        try:
            content = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if len(content) < 500:
            continue
        cve_m = CVE_RE.search(md.name)
        cve = cve_m.group(0) if cve_m else md.stem

        # Extrai título/product do primeiro H1 ou frontmatter
        title_m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else cve

        # Limita tamanho do conteúdo pro trace ser treinável
        body = content.strip()
        # Remove YAML frontmatter se houver
        if body.startswith("---"):
            end = body.find("\n---", 3)
            if end > 0:
                body = body[end + 4:].lstrip()
        # Limita a ~2000 chars de análise
        body = body[:2000]

        yield {
            "user": f"Explain the root cause and exploitation path of {cve}. This was a real in-the-wild 0day.",
            "assistant": f"{title}\n\n{body}".strip(),
            "source": f"p0_rca:{cve}",
        }


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data/raw/0days-in-the-wild/0day-RCAs")
    count = 0
    for rec in parse(src):
        print(json.dumps(rec, ensure_ascii=False))
        count += 1
    print(f"\n# {count} records", file=sys.stderr)
