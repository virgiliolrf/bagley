"""VoiceBadge - compact header indicator for voice state.

States:
  OFF    -> gray mic icon  (BADGE_OFF)
  LISTEN -> cyan mic icon  (BADGE_LISTEN)
  ACTIVE -> orange mic     (BADGE_ACTIVE)
"""

from __future__ import annotations

from textual.widgets import Static

from bagley.tui.services.voice import VoiceState

# Icon strings.
BADGE_OFF = "[dim]MIC off[/dim]"
BADGE_LISTEN = "[cyan]MIC listen[/cyan]"
BADGE_ACTIVE = "[bold orange1]MIC active[/bold orange1]"

_STATE_TEXT = {
    VoiceState.OFF: BADGE_OFF,
    VoiceState.LISTEN: BADGE_LISTEN,
    VoiceState.ACTIVE: BADGE_ACTIVE,
}


class VoiceBadge(Static):
    DEFAULT_CSS = """
    VoiceBadge { width: auto; height: 1; padding: 0 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(BADGE_OFF, id="voice-badge", **kwargs)
        self._state = VoiceState.OFF

    @property
    def renderable(self) -> str:
        return _STATE_TEXT[self._state]

    def set_state(self, state: VoiceState) -> None:
        self._state = state
        self.update(self.renderable)
