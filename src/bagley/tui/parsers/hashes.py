"""Hash type detection by length and character set."""

from __future__ import annotations

import enum
import re


class HashType(str, enum.Enum):
    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    SHA512 = "SHA512"
    NTLM = "NTLM"


_HEX_RE = re.compile(r"^[a-fA-F0-9]+$")

_LENGTH_MAP: dict[int, HashType] = {
    32: HashType.MD5,
    40: HashType.SHA1,
    64: HashType.SHA256,
    128: HashType.SHA512,
}


def detect_hash_type(value: str) -> HashType | None:
    """Return the most likely HashType for *value*, or None if not a hash."""
    value = value.strip()
    if not value or not _HEX_RE.match(value):
        return None
    return _LENGTH_MAP.get(len(value))


def parse_hash_list(text: str) -> list[tuple[str, HashType]]:
    """Parse a newline-separated list of hashes and return typed pairs."""
    results: list[tuple[str, HashType]] = []
    for line in text.splitlines():
        line = line.strip()
        ht = detect_hash_type(line)
        if ht is not None:
            results.append((line, ht))
    return results
