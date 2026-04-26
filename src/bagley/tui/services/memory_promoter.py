"""MemoryPromoter — scan assistant response text and promote findings to SQLite.

Detects:
    new_host       — bare IPv4 address appearing as "up" or via nmap host line
    new_port       — "<port>/tcp open" nmap output lines
    cve_match      — CVE-YYYY-NNNNN patterns; promotes as critical finding
    new_cred       — "credential:" / "password:" / "passwd:" / "cred:" followed by user:pass
    exploit_attempt — lines containing exploit/attempt/payload keywords
    shell_obtained  — "shell obtained" / "session opened" / "meterpreter" phrases

Each match calls the corresponding MemoryStore method and returns an event tuple
(kind: str, detail: str) to the caller so it can fire a toast.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bagley.memory.store import MemoryStore

# ---- compiled patterns ----
_RE_IP       = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b")
_RE_HOST_UP  = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3})\b.*\bis up\b", re.IGNORECASE)
_RE_PORT     = re.compile(
    r"\b(\d{1,5})/(tcp|udp)\s+open\s+(\S+)(?:\s+(.+))?", re.IGNORECASE
)
_RE_CVE      = re.compile(r"\b(CVE-\d{4}-\d{4,7})\b", re.IGNORECASE)
_RE_CRED     = re.compile(
    r"(?:credential|password|passwd|cred)[:\s]+([A-Za-z0-9_\-\.]+:[^\s,;\"']{3,64})",
    re.IGNORECASE,
)
_RE_SHELL    = re.compile(
    r"(shell obtained|meterpreter session|session \d+ opened|reverse shell)",
    re.IGNORECASE,
)
_RE_EXPLOIT  = re.compile(
    r"\b(exploit(?:ing|ed)?|payload sent|attempting exploit|running module)\b",
    re.IGNORECASE,
)


class MemoryPromoter:
    """Stateless scanner — one instance, call scan() per assistant message."""

    def scan(
        self,
        text: str,
        store: "MemoryStore",
        current_host: str | None,
    ) -> list[tuple[str, str]]:
        """Return list of (event_kind, detail_str) for every detected event."""
        if not text.strip():
            return []

        events: list[tuple[str, str]] = []

        # --- new host up ---
        for m in _RE_HOST_UP.finditer(text):
            ip = m.group(1)
            store.upsert_host(ip, state="up")
            events.append(("new_host", ip))

        # --- open port ---
        if current_host:
            for m in _RE_PORT.finditer(text):
                port  = int(m.group(1))
                proto = m.group(2).lower()
                svc   = m.group(3)
                ver   = (m.group(4) or "").strip()
                store.add_port(current_host, port, proto, svc, ver)
                events.append(("new_port", f"{port}/{proto} {svc}"))

        # --- CVE match ---
        seen_cves: set[str] = set()
        for m in _RE_CVE.finditer(text):
            cve = m.group(1).upper()
            if cve in seen_cves:
                continue
            seen_cves.add(cve)
            host = current_host or "unknown"
            from bagley.memory.store import Finding
            store.add_finding(Finding(
                host=host,
                severity="critical",
                category="CVE",
                summary=f"CVE match detected in chat: {cve}",
                cve=cve,
            ))
            events.append(("cve_match", cve))

        # --- credential extraction ---
        for m in _RE_CRED.finditer(text):
            raw = m.group(1).strip()
            if ":" in raw:
                user, _, cred = raw.partition(":")
            else:
                user, cred = "unknown", raw
            host = current_host or "unknown"
            store.add_cred(host, service="unknown", username=user, credential=cred,
                           source="auto-promote")
            events.append(("new_cred", f"{user}:***"))

        # --- exploit attempt ---
        for m in _RE_EXPLOIT.finditer(text):
            host = current_host or "unknown"
            store.add_attempt(host, technique=m.group(1), tool="chat", outcome="partial",
                              details=text[:120])
            events.append(("exploit_attempt", m.group(1)))
            break   # one event per message is enough

        # --- shell obtained ---
        if _RE_SHELL.search(text):
            host = current_host or "unknown"
            store.add_attempt(host, technique="shell", tool="chat", outcome="success",
                              details=text[:120])
            events.append(("shell_obtained", host))

        return events
