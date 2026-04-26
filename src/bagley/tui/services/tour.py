"""First-launch tour driver.

Manages the `.bagley/.toured` flag. Creates the flag via mark_done();
exposes is_done() for the app to query on startup.

The actual overlay rendering is handled by `widgets/tour_overlay.py`
(Task 11). This module owns only the flag and step data.
"""

from __future__ import annotations

from pathlib import Path


# Tour steps: (pane_id, caption)
TOUR_STEPS: list[tuple[str, str]] = [
    ("#hosts-panel", "Hosts, ports, and findings for your scope live here."),
    ("#chat-panel",  "Chat with Bagley here - ReAct stream, confirmations, plan mode."),
    ("#target-panel", "Target details, kill-chain progress, creds, and notes are here."),
    ("#modes-bar",   "Switch operational mode (RECON -> EXPLOIT -> REPORT...) from this bar."),
    ("#palette",     "Ctrl+K opens the command palette - search all actions from here."),
]

_FLAG_NAME = ".toured"
_DEFAULT_BAGLEY_DIR = Path(".bagley")


class TourService:
    def __init__(self, bagley_dir: Path | None = None) -> None:
        self._dir = bagley_dir or self._default_dir()

    @staticmethod
    def _default_dir() -> Path:
        return _DEFAULT_BAGLEY_DIR

    @property
    def _flag_path(self) -> Path:
        return self._dir / _FLAG_NAME

    def is_done(self) -> bool:
        return self._flag_path.exists()

    def mark_done(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._flag_path.touch()

    @property
    def steps(self) -> list[tuple[str, str]]:
        return TOUR_STEPS
