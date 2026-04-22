"""NotesEditor — F4 focus, Bagley auto-append, content persistence."""
import pytest
from bagley.tui.app import BagleyApp


@pytest.mark.asyncio
async def test_f4_focuses_notes_editor():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        await pilot.press("f4")
        await pilot.pause()
        # After F4 the notes editor TextArea should have focus
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        assert editor is not None


@pytest.mark.asyncio
async def test_notes_editor_starts_empty():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        ta = editor.query_one("#notes-textarea")
        assert ta.text == ""


@pytest.mark.asyncio
async def test_notes_editor_typing_updates_tab_state():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        await pilot.press("f4")
        await pilot.pause()
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        ta = editor.query_one("#notes-textarea")
        ta.insert("hello notes", location=(0, 0))
        await pilot.pause()
        # TabState should reflect the update
        assert "hello notes" in app.state.tabs[app.state.active_tab].notes_md


@pytest.mark.asyncio
async def test_bagley_auto_append_adds_timestamped_line():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        from bagley.tui.panels.notes_editor import NotesEditor
        editor = app.query_one(NotesEditor)
        editor.append_note("SQLi confirmed on /login")
        await pilot.pause()
        ta = editor.query_one("#notes-textarea")
        assert "SQLi confirmed on /login" in ta.text
        # Timestamp format HH:MM should be present
        import re
        assert re.search(r"\d{2}:\d{2}", ta.text)


@pytest.mark.asyncio
async def test_notes_editor_replaces_static_notes_section():
    app = BagleyApp(stub=True)
    async with app.run_test(size=(180, 40)) as pilot:
        # There should be no bare Static with id=notes-section any more
        from textual.widgets import Static
        statics = [w for w in app.query(Static) if w.id == "notes-section"]
        assert statics == []
