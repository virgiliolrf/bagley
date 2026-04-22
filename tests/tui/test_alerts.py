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


# ---- ToastLayer integration tests ----

import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.services.alerts import Alert, AlertBus, Severity, bus as global_bus


@pytest.mark.asyncio
async def test_toast_layer_mounts_in_app():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        layer = app.query_one("#toast-layer")
        assert layer is not None


@pytest.mark.asyncio
async def test_publish_info_creates_toast():
    # Reset global bus subscribers for test isolation
    test_bus = AlertBus()
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        layer = app.query_one("#toast-layer")
        layer._bus = test_bus
        test_bus.subscribe(layer._on_alert)
        test_bus.publish(Alert(Severity.INFO, "Test toast", "body text", "test"))
        await pilot.pause()
        toasts = layer.query(".toast-widget")
        assert len(toasts) >= 1


@pytest.mark.asyncio
async def test_toast_stack_capped_at_four():
    test_bus = AlertBus()
    app = BagleyApp(stub=True)
    async with app.run_test(size=(160, 40)) as pilot:
        layer = app.query_one("#toast-layer")
        layer._bus = test_bus
        test_bus.subscribe(layer._on_alert)
        for i in range(6):
            test_bus.publish(Alert(Severity.WARN, f"Toast {i}", "", "test"))
        await pilot.pause()
        toasts = layer.query(".toast-widget")
        assert len(toasts) <= 4
