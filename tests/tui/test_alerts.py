"""AlertBus and Alert dataclass tests."""
import time
import pytest
from bagley.tui.services.alerts import Alert, AlertBus, Severity


def test_alert_dataclass_fields():
    a = Alert(severity=Severity.WARN, title="TEST", body="something", source="scan")
    assert a.severity == Severity.WARN
    assert a.title == "TEST"
    assert isinstance(a.ts, float)


def test_alert_severity_ordering():
    assert Severity.INFO < Severity.OK < Severity.WARN < Severity.CRIT


def test_bus_publish_calls_subscriber():
    bus = AlertBus()
    received: list[Alert] = []
    bus.subscribe(received.append)
    a = Alert(Severity.INFO, "hello", "", "test")
    bus.publish(a)
    assert len(received) == 1
    assert received[0].title == "hello"


def test_bus_multiple_subscribers():
    bus = AlertBus()
    r1: list[Alert] = []
    r2: list[Alert] = []
    bus.subscribe(r1.append)
    bus.subscribe(r2.append)
    bus.publish(Alert(Severity.CRIT, "fire", "", "test"))
    assert len(r1) == 1
    assert len(r2) == 1


def test_bus_history_capped_at_200():
    bus = AlertBus()
    for i in range(210):
        bus.publish(Alert(Severity.INFO, f"a{i}", "", "test"))
    assert len(bus.history) == 200


def test_bus_unsubscribe():
    bus = AlertBus()
    received: list[Alert] = []
    bus.subscribe(received.append)
    bus.unsubscribe(received.append)
    bus.publish(Alert(Severity.INFO, "nope", "", "test"))
    assert received == []
