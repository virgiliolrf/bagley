"""Converte HackTricks markdown → Hermes traces.

Cada página vira 1 trace:
- Título da página = user question ("How do I [title]?")
- Primeiros 1500 chars do conteúdo = assistant answer
- Se houver bloco ```bash ... ``` perto do topo, extrai pra tool_call

Filtros:
- Skip páginas muito curtas (<300 chars)
- Skip páginas de índice/menu (heurística: <3 parágrafos e poucos comandos)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

# Pastas com conteúdo pentest relevante (skip generic TODO/draft)
RELEVANT_DIRS = [
    "network-services-pentesting", "pentesting-web", "linux-hardening",
    "windows-hardening", "active-directory-methodology", "cryptography",
    "mobile-pentesting", "generic-methodologies-and-resources",
    "forensics", "reversing", "exploiting", "pentesting", "binary-exploitation",
    "a.i.", "physical-attacks", "radio-hacking", "hardware-physical-access",
]

CODE_BLOCK = re.compile(r"```(?:bash|sh|powershell|ps1|python|py)?\s*\n(.*?)```", re.DOTALL)
TITLE_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _clean_md(text: str) -> str:
    """Remove HTML-ish e referências relativas."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\{\{#include[^}]+\}\}", "", text)
    text = re.sub(r"\{% hint[^%]*%\}.*?\{% endhint %\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\{% tabs %\}.*?\{% endtabs %\}", "", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _title_from_file(path: Path, content: str) -> str:
    m = TITLE_H1.search(content[:500])
    if m:
        return m.group(1).strip()
    return path.stem.replace("-", " ").replace("_", " ").title()


def _is_index(content: str) -> bool:
    if len(content) < 300:
        return True
    lines = [l for l in content.split("\n") if l.strip()]
    link_lines = sum(1 for l in lines if re.match(r"^[\-\*]\s+\[", l))
    return link_lines > 0.6 * len(lines)


def _extract_commands(content: str, limit: int = 3) -> list[str]:
    cmds = []
    for match in CODE_BLOCK.finditer(content):
        block = match.group(1).strip()
        if not block:
            continue
        # pega primeira linha útil de cada bloco
        for line in block.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if len(line) < 400:
                cmds.append(line)
                break
        if len(cmds) >= limit:
            break
    return cmds


def parse(root: Path) -> Iterable[dict]:
    if not root.exists():
        return
    for md_path in root.rglob("*.md"):
        parts = md_path.relative_to(root).parts
        if not any(rd in parts for rd in RELEVANT_DIRS):
            continue
        try:
            content = md_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if _is_index(content):
            continue
        content = _clean_md(content)
        if len(content) < 300:
            continue

        title = _title_from_file(md_path, content)
        commands = _extract_commands(content)

        # Corpo textual: remove code blocks pro prosa-part
        prose = CODE_BLOCK.sub("", content)
        prose = re.sub(r"^#.*$", "", prose, flags=re.MULTILINE).strip()
        prose = prose[:1400]
        if not prose and not commands:
            continue

        parts_out: list[str] = []
        if prose:
            parts_out.append(prose)
        if commands:
            parts_out.append("\n\nKey commands:\n" + "\n".join(f"  $ {c}" for c in commands))
        assistant = "".join(parts_out).strip()
        if len(assistant) < 200:
            continue

        yield {
            "user": f"Walk me through: {title}",
            "assistant": assistant,
            "source": f"hacktricks:{md_path.relative_to(root)}",
        }


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./data/raw/hacktricks")
    count = 0
    for rec in parse(src):
        print(json.dumps(rec, ensure_ascii=False))
        count += 1
    print(f"\n# {count} records", file=sys.stderr)
