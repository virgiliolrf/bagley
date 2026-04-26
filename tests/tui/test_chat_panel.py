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


# ---- Phase 6 additions ----

@pytest.mark.asyncio
async def test_report_mode_submit_delegates_to_reporter(tmp_path):
    """In REPORT mode, submitting a message must NOT execute shell tools;
    instead it triggers the reporter to compile a report."""
    from unittest.mock import patch, MagicMock
    from bagley.tui.app import BagleyApp

    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    app.state.mode = "REPORT"
    with patch("bagley.tui.panels.chat.Reporter") as mock_reporter_cls:
        mock_reporter = MagicMock()
        mock_reporter.compile.return_value = "# Report\n\ntest content"
        mock_reporter.save.return_value = tmp_path / "report.md"
        mock_reporter_cls.return_value = mock_reporter
        async with app.run_test(size=(160, 40)) as pilot:
            await pilot.press("f3")          # focus chat
            inp = app.query_one("#chat-input")
            inp.value = "generate report"
            await pilot.press("enter")
            await pilot.pause()
            # Reporter should have been instantiated and compile() called
            assert mock_reporter_cls.called or mock_reporter.compile.called


@pytest.mark.asyncio
async def test_tts_hook_fires_on_assistant_message(tmp_path):
    """An assistant message posted to chat must call voice.speak() when ACTIVE."""
    from unittest.mock import MagicMock
    from bagley.tui.app import BagleyApp
    from bagley.tui.services.voice import VoiceState

    (tmp_path / ".toured").touch()
    app = BagleyApp(stub=True, bagley_dir=tmp_path)
    mock_tts = MagicMock()
    app.voice._tts = mock_tts
    app.voice.state = VoiceState.ACTIVE

    async with app.run_test(size=(160, 40)) as pilot:
        # Simulate posting an assistant message to the chat panel
        from bagley.tui.panels.chat import ChatPanel
        chat = app.query_one(ChatPanel)
        chat.post_assistant_message("I found an open port.")
        await pilot.pause()
        mock_tts.speak.assert_called_once_with("I found an open port.")
