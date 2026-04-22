"""Smart paste dispatcher — classify and route pasted content."""

from __future__ import annotations

import enum
import re
from typing import Optional


class PasteClassification(str, enum.Enum):
    NMAP = "nmap"
    SHODAN = "shodan"
    HASH_LIST = "hash_list"
    CVE = "cve"
    URL = "url"
    IP_LIST = "ip_list"
    PLAIN_TEXT = "plain_text"


_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_CVE_RE = re.compile(r"^cve-\d{4}-\d{4,}$", re.IGNORECASE)
_URL_RE = re.compile(r"^https?://\S+", re.IGNORECASE)
_HEX32_RE = re.compile(r"^[a-fA-F0-9]{32,128}$")


class SmartPasteDispatcher:
    """Classify pasted content and provide extraction helpers."""

    def classify(self, text: str) -> PasteClassification:
        """Return the most specific PasteClassification for *text*."""
        stripped = text.strip()

        # Single-line patterns first
        if _CVE_RE.match(stripped):
            return PasteClassification.CVE
        if _URL_RE.match(stripped):
            return PasteClassification.URL

        # Multi-line content
        lines = [l.strip() for l in stripped.splitlines() if l.strip()]
        if not lines:
            return PasteClassification.PLAIN_TEXT

        # Nmap: look for "Nmap scan report for" marker
        if any("Nmap scan report for" in l or "PORT   STATE" in l or "PORT     STATE" in l
               for l in lines):
            return PasteClassification.NMAP

        # Shodan JSON: starts with { and contains "ip_str"
        if stripped.startswith("{") and "ip_str" in stripped:
            return PasteClassification.SHODAN

        # Hash list: every non-empty line is a valid hex hash
        if all(_HEX32_RE.match(l) for l in lines):
            return PasteClassification.HASH_LIST

        # IP list: every non-empty line is a bare IPv4
        if all(_IP_RE.match(l) for l in lines):
            return PasteClassification.IP_LIST

        return PasteClassification.PLAIN_TEXT

    def extract_ips(self, text: str) -> list[str]:
        """Extract all IPv4 addresses from an IP-list-classified text."""
        return [
            l.strip()
            for l in text.splitlines()
            if _IP_RE.match(l.strip())
        ]
