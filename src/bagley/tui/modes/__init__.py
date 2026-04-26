"""Operational modes — registry with allowlist, persona suffix, confirm policy, color."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Mode:
    index: int
    name: str
    color: str
    persona_suffix: str
    confirm_policy: str                     # "auto" | "explicit"
    allowlist: Optional[frozenset[str]]     # None = inherit / unrestricted (LEARN)


MODES: list[Mode] = [
    Mode(
        1, "RECON", "cyan",
        "Cautious observer. Read-only. No packets that touch the target beyond banner grabs.",
        "auto",
        frozenset({"nmap", "dig", "whois", "traceroute", "masscan"}),
    ),
    Mode(
        2, "ENUM", "orange3",
        "Curious, detail-oriented. Low-impact active enumeration.",
        "auto",
        frozenset({"gobuster", "ffuf", "nikto", "enum4linux-ng", "smbmap", "ssh-audit"}),
    ),
    Mode(
        3, "EXPLOIT", "red",
        "Aggressive. Proposes exploits. No handholding.",
        "explicit",
        frozenset({"sqlmap", "msfconsole", "hydra", "medusa", "exploit-db", "searchsploit"}),
    ),
    Mode(
        4, "POST", "magenta",
        "Methodical looter on a shell. Prefer LOLBins.",
        "explicit",
        frozenset({"linpeas", "winpeas", "mimikatz", "lazagne", "find", "ls", "cat"}),
    ),
    Mode(
        5, "PRIVESC", "dark_orange",
        "Surgical escalator.",
        "explicit",
        frozenset({"linpeas", "linux-exploit-suggester", "pspy", "find", "id", "uname"}),
    ),
    Mode(
        6, "STEALTH", "grey50",
        "Paranoid. Delays. Fragmentation. Tor/proxychains.",
        "explicit",
        frozenset({"nmap", "proxychains", "tor", "torsocks"}),
    ),
    Mode(
        7, "OSINT", "green",
        "Passive stalker. No packets to target.",
        "auto",
        frozenset({"shodan", "censys", "theharvester", "dnsenum", "whois", "dig"}),
    ),
    Mode(
        8, "REPORT", "white",
        "Formal writer. No exec.",
        "auto",
        frozenset(),                        # empty = no shell exec
    ),
    Mode(
        9, "LEARN", "cyan",
        "Didactic. Explain every flag, CVE, and side effect.",
        "explicit",
        None,                               # None = inherit active mode's allowlist
    ),
]


def by_name(name: str) -> Mode:
    for m in MODES:
        if m.name == name:
            return m
    raise KeyError(name)


def by_index(idx: int) -> Mode:
    return MODES[idx - 1]
