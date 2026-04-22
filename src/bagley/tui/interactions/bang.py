"""Bang re-exec: !!, !N, !prefix expansion from tab command history."""

from __future__ import annotations

import re


class BangExpansionError(ValueError):
    """Raised when a bang expression cannot be resolved."""


class BangExpander:
    """Expand bash-style history shortcuts against a command history list.

    History is ordered oldest-first; index 1 = first command.
    """

    _DOUBLE_BANG = re.compile(r"^!!$")
    _BANG_N = re.compile(r"^!(\d+)$")
    _BANG_PREFIX = re.compile(r"^!([A-Za-z0-9_/\-\.]+)$")

    def __init__(self, cmd_history: list[str]) -> None:
        self.cmd_history = cmd_history

    def expand(self, text: str) -> str:
        """Return the expanded string, or *text* unchanged if not a bang expr."""
        if self._DOUBLE_BANG.match(text):
            if not self.cmd_history:
                raise BangExpansionError("History is empty — cannot expand !!")
            return self.cmd_history[-1]

        m = self._BANG_N.match(text)
        if m:
            n = int(m.group(1))
            if n < 1 or n > len(self.cmd_history):
                raise BangExpansionError(
                    f"History index {n} out of range (1..{len(self.cmd_history)})"
                )
            return self.cmd_history[n - 1]

        m = self._BANG_PREFIX.match(text)
        if m:
            prefix = m.group(1)
            for cmd in reversed(self.cmd_history):
                if cmd.startswith(prefix):
                    return cmd
            raise BangExpansionError(
                f"No command in history starts with '{prefix}'"
            )

        return text  # Not a bang expression
