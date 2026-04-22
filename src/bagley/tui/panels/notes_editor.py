"""NotesEditor — editable markdown notes area for TargetPanel.

Activates on F4 / focus. Persists content to TabState.notes_md.
Bagley can call append_note(text) to add a timestamped line without
requiring user focus.
"""

from __future__ import annotations

import datetime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static, TextArea

from bagley.tui.state import AppState


class NotesEditor(Vertical):
    """Markdown notes section: Static header + TextArea body."""

    DEFAULT_CSS = """
    NotesEditor { height: auto; min-height: 6; padding: 0 1; }
    NotesEditor > TextArea { height: 6; border: round $accent; }
    """

    def __init__(self, state: AppState, **kwargs) -> None:
        super().__init__(id="notes-editor", **kwargs)
        self._state = state
        self.can_focus = True

    def compose(self) -> ComposeResult:
        yield Static("[b orange3]◆ NOTES[/]  [dim](F4 to edit)[/]", id="notes-header")
        tab = self._active_tab()
        ta = TextArea(
            text=tab.notes_md if tab else "",
            id="notes-textarea",
            language="markdown",
            show_line_numbers=False,
        )
        yield ta

    def _active_tab(self):
        if not self._state.tabs:
            return None
        return self._state.tabs[self._state.active_tab]

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        tab = self._active_tab()
        if tab is not None:
            tab.notes_md = event.text_area.text

    def on_focus(self) -> None:
        try:
            self.query_one("#notes-textarea", TextArea).focus()
        except Exception:
            pass

    def append_note(self, text: str) -> None:
        """Bagley-side auto-append: inserts 'HH:MM — <text>' at end of textarea."""
        ts = datetime.datetime.now().strftime("%H:%M")
        line = f"\n{ts} — {text}"
        ta = self.query_one("#notes-textarea", TextArea)
        end_row = len(ta.text.splitlines())
        end_col = len(ta.text.splitlines()[-1]) if ta.text.splitlines() else 0
        ta.insert(line, location=(end_row, end_col))
        # sync state
        tab = self._active_tab()
        if tab is not None:
            tab.notes_md = ta.text
