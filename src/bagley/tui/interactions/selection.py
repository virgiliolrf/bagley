"""Regex-based classifier for selected text.

Priority (highest → lowest):
  URL > CVE > SHA256 > MD5 > IPV4 > PORT > PATH > UNKNOWN

LEARN: classifiers run in priority order; the first match wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class SelectionType(Enum):
    URL = auto()
    CVE = auto()
    SHA256 = auto()
    MD5 = auto()
    IPV4 = auto()
    PORT = auto()
    PATH = auto()
    UNKNOWN = auto()


@dataclass
class ClassifyResult:
    type: SelectionType
    value: str          # normalised match value (stripped)
    raw: str            # original input


# ── Regex patterns ────────────────────────────────────────────────────────────

_RE_URL = re.compile(
    r"""(?:https?|ftp|ftps)://[^\s/$.?#][^\s]*""",
    re.IGNORECASE,
)

_RE_CVE = re.compile(
    r"""CVE-\d{4}-\d{4,7}""",
    re.IGNORECASE,
)

_RE_SHA256 = re.compile(
    r"""^[0-9a-fA-F]{64}$""",
)

_RE_MD5 = re.compile(
    r"""^[0-9a-fA-F]{32}$""",
)

_RE_IPV4 = re.compile(
    r"""(?<!\d)
        (25[0-5]|2[0-4]\d|[01]?\d\d?)\.
        (25[0-5]|2[0-4]\d|[01]?\d\d?)\.
        (25[0-5]|2[0-4]\d|[01]?\d\d?)\.
        (25[0-5]|2[0-4]\d|[01]?\d\d?)
        (?:/\d{1,2})?               # optional CIDR
        (?!\d)""",
    re.VERBOSE,
)

_RE_PORT = re.compile(
    r"""^(\d{1,5})/(tcp|udp)$""",
    re.IGNORECASE,
)

_RE_PATH_UNIX = re.compile(
    r"""^/[^\s]+""",
)

_RE_PATH_WIN = re.compile(
    r"""^[A-Za-z]:\\[^\s]+""",
)


def classify(text: str) -> ClassifyResult:
    """Return a :class:`ClassifyResult` for *text*.

    Strips surrounding whitespace before matching.
    """
    raw = text
    t = text.strip()

    # URL — highest priority (may contain IP, CVE in path)
    if _RE_URL.search(t):
        m = _RE_URL.search(t)
        return ClassifyResult(SelectionType.URL, m.group(0), raw)

    # CVE
    if _RE_CVE.search(t):
        m = _RE_CVE.search(t)
        return ClassifyResult(SelectionType.CVE, m.group(0).upper(), raw)

    # SHA256 (64 hex chars)
    if _RE_SHA256.match(t):
        return ClassifyResult(SelectionType.SHA256, t.lower(), raw)

    # MD5 (32 hex chars)
    if _RE_MD5.match(t):
        return ClassifyResult(SelectionType.MD5, t.lower(), raw)

    # IPv4 / CIDR
    if _RE_IPV4.search(t):
        m = _RE_IPV4.search(t)
        return ClassifyResult(SelectionType.IPV4, m.group(0), raw)

    # Port / protocol
    if _RE_PORT.match(t):
        return ClassifyResult(SelectionType.PORT, t.lower(), raw)

    # Absolute path (Unix or Windows)
    if _RE_PATH_UNIX.match(t) or _RE_PATH_WIN.match(t):
        return ClassifyResult(SelectionType.PATH, t, raw)

    return ClassifyResult(SelectionType.UNKNOWN, t, raw)
