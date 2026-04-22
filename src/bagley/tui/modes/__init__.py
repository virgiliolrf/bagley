"""Operational modes. Phase 1 registers all nine with identical RECON-level defaults."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mode:
    index: int
    name: str
    color: str
    persona_suffix: str
    confirm_policy: str = "explicit"


MODES: list[Mode] = [
    Mode(1, "RECON",    "cyan",       "Cautious observer. Read-only.",                  "auto"),
    Mode(2, "ENUM",     "orange3",    "Curious. Low-impact active enum.",               "auto"),
    Mode(3, "EXPLOIT",  "red",        "Aggressive. Proposes exploits.",                 "explicit"),
    Mode(4, "POST",     "magenta",    "Methodical looter on a shell.",                  "explicit"),
    Mode(5, "PRIVESC",  "dark_orange","Surgical escalator.",                            "explicit"),
    Mode(6, "STEALTH",  "grey50",     "Paranoid. Delays. Fragmentation.",               "explicit"),
    Mode(7, "OSINT",    "green",      "Passive stalker. No packets to target.",         "auto"),
    Mode(8, "REPORT",   "white",      "Formal writer. No exec.",                        "auto"),
    Mode(9, "LEARN",    "cyan",       "Didactic. Explain every flag and CVE.",          "explicit"),
]


def by_name(name: str) -> Mode:
    for m in MODES:
        if m.name == name:
            return m
    raise KeyError(name)


def by_index(idx: int) -> Mode:
    return MODES[idx - 1]
