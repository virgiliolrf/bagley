"""Tests for the payload generation library.

Validates each payload type, encoding correctness, and edge cases.
"""

from __future__ import annotations

import base64
import urllib.parse

import pytest

from bagley.tui.services.payload_gen import (
    PayloadConfig,
    PayloadType,
    Encoding,
    generate,
)


LHOST = "10.10.14.5"
LPORT = 4444


# ---------------------------------------------------------------------------
# Payload type coverage
# ---------------------------------------------------------------------------

def test_bash_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "bash" in out.lower() or "/dev/tcp" in out


def test_python_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.PYTHON, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "import" in out


def test_nc_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.NC, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "nc" in out.lower() or "ncat" in out.lower()


def test_php_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.PHP, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "<?php" in out or "<?=" in out


def test_ps1_payload_contains_lhost_and_lport():
    cfg = PayloadConfig(type=PayloadType.PS1, lhost=LHOST, lport=LPORT)
    out = generate(cfg)
    assert LHOST in out
    assert str(LPORT) in out
    assert "Net.Sockets" in out or "TCPClient" in out


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def test_base64_encoding_roundtrips():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT, encoding=Encoding.BASE64)
    out = generate(cfg)
    # The output should be decodable and contain the raw payload content
    decoded = base64.b64decode(out).decode("utf-8")
    assert LHOST in decoded
    assert str(LPORT) in decoded


def test_url_encoding_percent_encodes_special_chars():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT, encoding=Encoding.URL)
    raw = generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT))
    encoded = generate(cfg)
    # At minimum, spaces and / should be encoded
    decoded = urllib.parse.unquote(encoded)
    assert decoded == raw


def test_none_encoding_returns_raw():
    cfg = PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT, encoding=Encoding.NONE)
    raw = generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=LPORT))
    assert generate(cfg) == raw


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_lhost_raises():
    with pytest.raises(ValueError, match="lhost"):
        generate(PayloadConfig(type=PayloadType.BASH, lhost="", lport=4444))


def test_invalid_lport_zero_raises():
    with pytest.raises(ValueError, match="lport"):
        generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=0))


def test_invalid_lport_over_65535_raises():
    with pytest.raises(ValueError, match="lport"):
        generate(PayloadConfig(type=PayloadType.BASH, lhost=LHOST, lport=99999))
