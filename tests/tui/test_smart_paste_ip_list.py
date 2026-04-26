"""Tests for smart paste — IP list detection and scope-add flow."""

from bagley.tui.interactions.smart_paste import SmartPasteDispatcher, PasteClassification


IP_LIST = "10.0.0.1\n10.0.0.2\n10.0.0.3\n192.168.1.100\n"
NOT_IP_LIST = "hello world\nthis is text\nnot ips\n"
MIXED = "10.0.0.1\nsome text\n10.0.0.2\n"  # not pure IP list


def test_classify_ip_list():
    d = SmartPasteDispatcher()
    cls = d.classify(IP_LIST)
    assert cls == PasteClassification.IP_LIST


def test_classify_non_ip_list():
    d = SmartPasteDispatcher()
    cls = d.classify(NOT_IP_LIST)
    assert cls == PasteClassification.PLAIN_TEXT


def test_classify_mixed_is_plain():
    d = SmartPasteDispatcher()
    cls = d.classify(MIXED)
    assert cls == PasteClassification.PLAIN_TEXT


def test_extract_ips():
    d = SmartPasteDispatcher()
    ips = d.extract_ips(IP_LIST)
    assert ips == ["10.0.0.1", "10.0.0.2", "10.0.0.3", "192.168.1.100"]
