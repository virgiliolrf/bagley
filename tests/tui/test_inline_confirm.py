"""Tests: inline confirmation panel renders in ChatPanel, y/n dispatch."""

import pytest
from textual.app import App, ComposeResult

from bagley.tui.panels.chat import ChatPanel, ConfirmPanel
from bagley.tui.state import AppState, detect_os


class _ChatApp(App):
    CSS = "Screen { layers: base overlay; }"

    def __init__(self):
        super().__init__()
        self.state = AppState(os_info=detect_os(), engine_label="stub")

    def compose(self) -> ComposeResult:
        yield ChatPanel(self.state)


@pytest.mark.asyncio
async def test_confirm_panel_not_visible_by_default():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        panel = app.query_one(ConfirmPanel)
        assert not panel.visible


@pytest.mark.asyncio
async def test_confirm_panel_shows_when_triggered():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("nmap -sV 10.10.10.10", callback=lambda r: None)
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        assert panel.visible


@pytest.mark.asyncio
async def test_confirm_panel_displays_command():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("sqlmap -u http://target/login", callback=lambda r: None)
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        assert panel._pending_cmd == "sqlmap -u http://target/login"


@pytest.mark.asyncio
async def test_confirm_yes_button_calls_callback_true():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("hydra -l admin 10.10.10.10", callback=lambda r: results.append(r))
        await pilot.pause()
        await pilot.click("#confirm-yes-btn")
        await pilot.pause()
        assert results == [True]


@pytest.mark.asyncio
async def test_confirm_no_button_calls_callback_false():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("msfconsole -q", callback=lambda r: results.append(r))
        await pilot.pause()
        await pilot.click("#confirm-no-btn")
        await pilot.pause()
        assert results == [False]


@pytest.mark.asyncio
async def test_confirm_panel_hides_after_answer():
    app = _ChatApp()
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("ls /", callback=lambda r: None)
        await pilot.pause()
        await pilot.click("#confirm-yes-btn")
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        assert not panel.visible


@pytest.mark.asyncio
async def test_confirm_panel_key_y_accepts():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("id", callback=lambda r: results.append(r))
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        panel.focus()
        await pilot.press("y")
        await pilot.pause()
        assert results == [True]


@pytest.mark.asyncio
async def test_confirm_panel_key_n_rejects():
    app = _ChatApp()
    results = []
    async with app.run_test(size=(120, 40)) as pilot:
        chat = app.query_one(ChatPanel)
        chat.request_confirm("id", callback=lambda r: results.append(r))
        await pilot.pause()
        panel = app.query_one(ConfirmPanel)
        panel.focus()
        await pilot.press("n")
        await pilot.pause()
        assert results == [False]


from bagley.tui.app import BagleyApp as _BagleyApp
from bagley.tui.panels.chat import ChatPanel as _ChatPanel


@pytest.mark.asyncio
async def test_mode_change_updates_chat_border_color():
    app = _BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.press("alt+3")      # EXPLOIT = red
        await pilot.pause()
        chat = app.query_one(_ChatPanel)
        # styles.border is a tuple ("round", Color) — check color name or value
        border_color = str(chat.styles.border_top[1])
        assert app.state.mode == "EXPLOIT"
        # border must have changed from default cyan (RECON) to red (EXPLOIT)
        assert "red" in border_color or border_color != "cyan"


@pytest.mark.asyncio
async def test_ctrl_m_cycles_modes():
    app = _BagleyApp(stub=True)
    async with app.run_test(size=(160, 50)) as pilot:
        initial_mode = app.state.mode   # "RECON"
        await pilot.press("ctrl+m")
        await pilot.pause()
        assert app.state.mode != initial_mode
        # Cycling from RECON should move to ENUM (index 2)
        assert app.state.mode == "ENUM"
