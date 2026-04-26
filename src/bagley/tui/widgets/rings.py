"""ProgressRings, Minimap, and SeverityBars ASCII visualization widgets.

ProgressRings  — kill-chain stage progress (●●●○○○○  43%)
Minimap        — 254-cell subnet dot map (lives in ReconScreen)
SeverityBars   — horizontal ASCII bars for CRIT/HIGH/MED/LOW counts
"""

from __future__ import annotations

import math
from textual.widgets import Static

# Kill-chain stage labels (7 stages, index 0..6)
_KC_LABELS = ["recon", "enum", "exploit", "postex", "privesc", "persist", "cleanup"]
_KC_TOTAL  = len(_KC_LABELS)

# Subnet minimap
_MINI_STATES: dict[str, str] = {
    "up":       "[green]●[/]",
    "down":     "[red]●[/]",
    "scanning": "[yellow]●[/]",
    "unknown":  "[dim]·[/]",
}

# Severity bar colors
_SEV_COLOR: dict[str, str] = {
    "critical": "red",
    "high":     "orange3",
    "medium":   "yellow",
    "low":      "cyan",
}


# --------------------------------------------------------------------------- #
#  ProgressRings                                                                #
# --------------------------------------------------------------------------- #

class ProgressRings(Static):
    """Renders kill-chain progress as filled/empty circles with percentage."""

    DEFAULT_CSS = """
    ProgressRings { height: auto; padding: 0 1; }
    """

    def __init__(self, stage: int = 0, **kwargs) -> None:
        super().__init__(id="killchain-rings", **kwargs)
        self._stage = stage

    def _render_text(self) -> str:
        filled  = "●" * self._stage
        empty   = "○" * (_KC_TOTAL - self._stage)
        pct     = int(round(self._stage / _KC_TOTAL * 100))
        dots    = f"[green]{filled}[/][dim]{empty}[/]  {pct}%"
        labels  = "  ".join(
            f"[bold]{l}[/]" if i < self._stage else f"[dim]{l}[/]"
            for i, l in enumerate(_KC_LABELS)
        )
        return f"{dots}\n{labels}"

    def on_mount(self) -> None:
        self.update(self._render_text())

    def refresh_stage(self, stage: int) -> None:
        self._stage = max(0, min(stage, _KC_TOTAL))
        self.update(self._render_text())


# --------------------------------------------------------------------------- #
#  Minimap                                                                      #
# --------------------------------------------------------------------------- #

class Minimap(Static):
    """254-cell dotmap for a /24 subnet in the recon tab.

    Call refresh_data({'10.0.0.1': 'up', '10.0.0.2': 'scanning', ...}) to update.
    """

    DEFAULT_CSS = """
    Minimap { height: auto; padding: 0 1; }
    """

    _COLS = 32  # dots per row → 8 rows for 254 cells

    def __init__(self, subnet_prefix: str = "10.10.0", **kwargs) -> None:
        super().__init__(id="subnet-minimap", **kwargs)
        self._prefix   = subnet_prefix
        self._states: dict[str, str] = {}   # last-octet str → state string

    def on_mount(self) -> None:
        self._render_map()

    def refresh_data(self, host_states: dict[str, str]) -> None:
        """Accept {ip: state} mapping; state in {up, down, scanning, unknown}."""
        self._states = {}
        for ip, state in host_states.items():
            last = ip.rsplit(".", 1)[-1]
            self._states[last] = state
        self._render_map()

    def _render_map(self) -> None:
        cells: list[str] = []
        for i in range(1, 255):
            key = str(i)
            state = self._states.get(key, "unknown")
            cells.append(_MINI_STATES.get(state, _MINI_STATES["unknown"]))
        rows: list[str] = []
        for r in range(0, 254, self._COLS):
            rows.append(" ".join(cells[r : r + self._COLS]))
        rendered = "\n".join(rows)
        # Store the raw markup string so tests can inspect content without a
        # mounted app; also pushed into Static.update for real rendering.
        self._raw_markup = rendered
        try:
            self.update(rendered)
        except Exception:
            pass

    # Read-only view of the most recently rendered markup text. Tests use
    # `minimap.renderable` to introspect Minimap content without mounting.
    @property
    def renderable(self):  # type: ignore[override]
        return getattr(self, "_raw_markup", "")


# --------------------------------------------------------------------------- #
#  SeverityBars                                                                 #
# --------------------------------------------------------------------------- #

class SeverityBars(Static):
    """Horizontal ASCII bars for CRIT / HIGH / MED / LOW finding counts."""

    DEFAULT_CSS = """
    SeverityBars { height: auto; padding: 0 1; }
    """

    def __init__(self, bar_width: int = 20, **kwargs) -> None:
        super().__init__(id="severity-bars", **kwargs)
        self._bar_width = bar_width
        self._counts: dict[str, int] = {
            "critical": 0, "high": 0, "medium": 0, "low": 0
        }

    def _render_text(self) -> str:
        max_count = max(self._counts.values()) or 1
        lines: list[str] = []
        labels = [("CRIT", "critical"), ("HIGH", "high"), ("MED", "medium"), ("LOW", "low")]
        for label, key in labels:
            count  = self._counts.get(key, 0)
            filled = int(round(count / max_count * self._bar_width))
            empty  = self._bar_width - filled
            color  = _SEV_COLOR[key]
            bar    = f"[{color}]{'▓' * filled}[/][dim]{'░' * empty}[/]"
            lines.append(f"{label:4} {bar} {count}")
        return "\n".join(lines)

    def on_mount(self) -> None:
        self.update(self._render_text())

    def refresh_data(self, counts: dict[str, int]) -> None:
        """Accept {severity_lower: count} dict and re-render."""
        self._counts.update(counts)
        self.update(self._render_text())
