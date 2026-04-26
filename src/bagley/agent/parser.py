"""Parser de tool_calls no formato Hermes.

Busca <tool_call>{...}</tool_call> no texto do assistant. Robusto a whitespace e aninhamento simples.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


@dataclass
class ToolCall:
    name: str
    arguments: dict
    raw: str           # bloco original incluindo tags
    span: tuple[int, int]  # posição no texto


def extract(text: str) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for m in TOOL_CALL_RE.finditer(text):
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        name = obj.get("name")
        args = obj.get("arguments") or {}
        if not name or not isinstance(args, dict):
            continue
        calls.append(ToolCall(name=name, arguments=args, raw=m.group(0), span=m.span()))
    return calls


def strip_tool_calls(text: str) -> str:
    """Remove todos os blocos tool_call do texto, deixa só a prosa do assistant."""
    return TOOL_CALL_RE.sub("", text).strip()
