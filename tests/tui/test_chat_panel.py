import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_chat_submit_updates_log_via_stub_engine():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        inp = app.query_one("#chat-input")
        inp.value = "hello"
        await pilot.press("f3")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        log = app.query_one("#chat-log")
        text = "\n".join(str(line) for line in log.lines)
        assert "hello" in text
        assert "bagley" in text.lower()
        assert app.state.turn == 1
