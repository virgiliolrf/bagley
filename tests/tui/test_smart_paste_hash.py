"""Tests for hash type detection."""

from bagley.tui.parsers.hashes import detect_hash_type, parse_hash_list, HashType

MD5    = "5d41402abc4b2a76b9719d911017c592"
SHA1   = "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"
SHA256 = "2c624232cdd221771294dfbb310acbc8abb9d04d8814c3b4b2f9f5b4c2d7d45b"
NTLM   = "b4b9b02e6f09a9bd760f388b67351e2b"  # same length as MD5, lowercase hex


def test_md5_detected():
    assert detect_hash_type(MD5) == HashType.MD5


def test_sha1_detected():
    assert detect_hash_type(SHA1) == HashType.SHA1


def test_sha256_detected():
    assert detect_hash_type(SHA256) == HashType.SHA256


def test_unknown_returns_none():
    assert detect_hash_type("notahash") is None
    assert detect_hash_type("") is None


def test_parse_hash_list_multiline():
    text = f"{MD5}\n{SHA1}\n{SHA256}\nnot-a-hash\n"
    results = parse_hash_list(text)
    assert len(results) == 3
    assert results[0] == (MD5, HashType.MD5)
    assert results[1] == (SHA1, HashType.SHA1)
    assert results[2] == (SHA256, HashType.SHA256)
