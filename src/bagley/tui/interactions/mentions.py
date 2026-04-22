"""@ mention popup entries and token substitution for ChatPanel."""

from __future__ import annotations

import re
from typing import Any


# ── Entry builder ─────────────────────────────────────────────────────────────

def build_mention_entries(context: dict[str, Any]) -> list[dict]:
    """Build the full list of @-completable entries from current session state."""
    entries: list[dict] = []

    # Scope IPs
    for ip in context.get("hosts", []):
        entries.append({"label": f"@{ip}", "kind": "host", "value": ip})

    # Credentials (all + per-user)
    creds: dict = context.get("creds", {})
    entries.append({"label": "@creds", "kind": "creds", "value": "\n".join(creds.values())})
    for user in creds:
        entries.append({"label": f"@creds.{user}", "kind": "cred_user", "value": creds[user]})

    # Last scan
    if context.get("scan_last"):
        entries.append({"label": "@scan.last", "kind": "scan", "value": context["scan_last"]})

    # Findings
    for cve, desc in context.get("findings", {}).items():
        entries.append({"label": f"@finding.{cve}", "kind": "finding", "value": desc})

    # Playbooks
    for pb_name in context.get("playbooks", []):
        entries.append({"label": f"@playbook.{pb_name}", "kind": "playbook", "value": pb_name})

    return entries


# ── Token substitutor ─────────────────────────────────────────────────────────

_MENTION_RE = re.compile(r"@([\w\.\-]+)")


class MentionSubstitutor:
    """Replace ``@token`` patterns in a message with their concrete content."""

    def __init__(self, context: dict[str, Any]) -> None:
        self._entries: dict[str, str] = {
            e["label"].lstrip("@"): e["value"]
            for e in build_mention_entries(context)
        }

    def substitute(self, text: str) -> str:
        """Return *text* with every known @token replaced by its value."""

        def _replace(m: re.Match) -> str:
            token = m.group(1)
            return self._entries.get(token, m.group(0))

        return _MENTION_RE.sub(_replace, text)


# ── Fuzzy filter helper ───────────────────────────────────────────────────────

def fuzzy_filter(entries: list[dict], query: str) -> list[dict]:
    """Return entries whose label contains every character of *query* in order."""
    q = query.lower()
    result = []
    for e in entries:
        label = e["label"].lower()
        idx = 0
        for ch in q:
            pos = label.find(ch, idx)
            if pos == -1:
                break
            idx = pos + 1
        else:
            result.append(e)
    return result
