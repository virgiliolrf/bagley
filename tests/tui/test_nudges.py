"""NudgeEngine heuristic tests."""
import tempfile
import pytest
from bagley.memory.store import MemoryStore, Finding
from bagley.tui.services.alerts import AlertBus, Severity
from bagley.tui.services.nudges import NudgeEngine
from bagley.tui.state import AppState, detect_os


def _fresh_store() -> MemoryStore:
    return MemoryStore(tempfile.mktemp(suffix=".db"))


def _fresh_state() -> AppState:
    return AppState(os_info=detect_os())


def test_idle_nudge_fires_after_15_ticks():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)

    # Simulate 14 idle ticks — should NOT fire
    for _ in range(14):
        eng._idle_ticks += 1
    eng._evaluate()
    assert not any(a.title == "Idle nudge" for a in alerts)

    # 15th tick — should fire
    eng._idle_ticks += 1
    eng._evaluate()
    assert any("next step" in a.body.lower() or "idle" in a.title.lower() for a in alerts)
    store.close()


def test_idle_nudge_resets_after_firing():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)

    eng._idle_ticks = 15
    eng._evaluate()
    count_before = len([a for a in alerts if "idle" in a.title.lower()])
    eng._evaluate()   # second call at same tick value should NOT fire again
    count_after = len([a for a in alerts if "idle" in a.title.lower()])
    assert count_after == count_before
    store.close()


def test_findings_nudge_fires_with_3_plus_high():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    for i in range(3):
        store.add_finding(Finding(f"10.0.0.{i+1}", "high", "SQLi", f"finding {i}"))
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)
    eng._evaluate()
    assert any("high" in a.body.lower() or "untouched" in a.body.lower() for a in alerts)
    store.close()


def test_findings_nudge_does_not_fire_with_2_high():
    bus = AlertBus()
    alerts = []
    bus.subscribe(alerts.append)
    store = _fresh_store()
    store.add_finding(Finding("10.0.0.1", "high", "A", "one"))
    store.add_finding(Finding("10.0.0.2", "high", "B", "two"))
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)
    eng._evaluate()
    finding_alerts = [a for a in alerts if "high" in a.body.lower() or "untouched" in a.body.lower()]
    assert finding_alerts == []
    store.close()


def test_nudge_engine_tick_increments_idle():
    bus = AlertBus()
    store = _fresh_store()
    state = _fresh_state()
    eng = NudgeEngine(state=state, store=store, bus=bus)
    before = eng._idle_ticks
    eng.tick()
    assert eng._idle_ticks == before + 1
    store.close()
