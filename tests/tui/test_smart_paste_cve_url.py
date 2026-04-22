"""Tests for smart paste — CVE ID and URL classification."""

from bagley.tui.interactions.smart_paste import SmartPasteDispatcher, PasteClassification


def test_classify_cve():
    d = SmartPasteDispatcher()
    assert d.classify("CVE-2021-41773") == PasteClassification.CVE
    assert d.classify("cve-2023-1234") == PasteClassification.CVE


def test_classify_url():
    d = SmartPasteDispatcher()
    assert d.classify("https://example.com/path?q=1") == PasteClassification.URL
    assert d.classify("http://10.0.0.1:8080/admin") == PasteClassification.URL


def test_classify_nmap_output():
    nmap_text = "Nmap scan report for 10.0.0.1\nPORT   STATE SERVICE\n22/tcp open  ssh\n"
    d = SmartPasteDispatcher()
    assert d.classify(nmap_text) == PasteClassification.NMAP


def test_classify_hash_list():
    hashes = "5d41402abc4b2a76b9719d911017c592\naaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d\n"
    d = SmartPasteDispatcher()
    assert d.classify(hashes) == PasteClassification.HASH_LIST


def test_classify_plain_fallback():
    d = SmartPasteDispatcher()
    assert d.classify("just some random text") == PasteClassification.PLAIN_TEXT
