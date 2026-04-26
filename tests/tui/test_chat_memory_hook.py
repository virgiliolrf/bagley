"""ChatPanel memory promotion + /memory command tests."""
import tempfile
import pytest
from bagley.tui.app import BagleyApp
from bagley.tui.services.alerts import bus, AlertBus, Severity


@pytest.mark.asyncio
async def test_slash_memory_shows_findings():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        inp = app.query_one("#chat-input")
        inp.value = "/memory"
        await pilot.press("f3")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        log = app.query_one("#chat-log")
        text = "\n".join(str(line) for line in log.lines)
        assert "memory" in text.lower() or "findings" in text.lower()


@pytest.mark.asyncio
async def test_promoter_fires_toast_on_port_in_response(monkeypatch):
    """Patch stub engine response to contain a port line; verify a toast appears."""
    from bagley.tui.panels import chat as chat_module

    # Patch the stub response to return a port-bearing line
    original_respond = None

    async def fake_respond(self_panel, user_msg: str):
        # Host-up pattern fires without current_host; 192.168.1.50 is up
        response_text = "Host 192.168.1.50 is up (latency 0.1s). 80/tcp open http Apache 2.4.49"
        log = self_panel.query_one("#chat-log")
        log.write(f"[magenta]bagley>[/] {response_text}")
        self_panel._state.turn += 1
        # Run promoter (same as real path)
        events = self_panel._promoter.scan(
            response_text, self_panel._store, current_host=None
        )
        for kind, detail in events:
            from bagley.tui.services.alerts import bus as _bus, Alert, Severity
            _bus.publish(Alert(Severity.INFO, f"◯ saved to memory", detail, "promoter"))

    received = []
    bus.subscribe(received.append)

    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        panel = app.query_one("#chat-panel")
        monkeypatch.setattr(panel, "_respond", lambda msg: app.call_later(fake_respond, panel, msg))
        inp = app.query_one("#chat-input")
        inp.value = "scan 10.0.0.1"
        await pilot.press("f3")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause(1.0)

    bus.unsubscribe(received.append)
    assert any("saved to memory" in a.title or "new_port" in a.body or a.source == "promoter"
               for a in received)
