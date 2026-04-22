"""Execute a Playbook by converting it to a Plan."""

from __future__ import annotations

import re
from typing import Any

from bagley.tui.plan_mode.plan import Plan, Step
from bagley.tui.playbooks.loader import Playbook


def substitute_vars(template: str, variables: dict[str, str]) -> str:
    """Replace ``{key}`` placeholders with *variables* values."""
    result = template
    for k, v in variables.items():
        result = result.replace(f"{{{k}}}", v)
    return result


def eval_condition(condition: str, context: dict[str, Any]) -> bool:
    """Safely evaluate a simple boolean condition string.

    *context* provides variable bindings (e.g. ``ports``, ``hosts``).
    Only allows ``in``, ``not in``, ``and``, ``or``, ``not`` and literals.
    Returns False on any evaluation error.
    """
    # Whitelist-based check: only allow safe tokens
    allowed = re.compile(r"^[\w\s\d\.\[\]\"\'\_\(\)]+$")
    if not allowed.match(condition):
        return False
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))  # noqa: S307
    except Exception:
        return False


class PlaybookRunner:
    """Converts a Playbook (with variable substitution) into a Plan."""

    def __init__(self, playbook: Playbook, variables: dict[str, str]) -> None:
        self.playbook = playbook
        self.variables = variables

    def to_plan(self, tab_id: str = "recon") -> Plan:
        """Build a Plan from the playbook steps with variables substituted."""
        steps: list[Step] = []
        for s in self.playbook.steps:
            if s.kind == "run":
                cmd = substitute_vars(s.run or "", self.variables)
                steps.append(Step(kind="run", cmd=cmd, description=f"Run: {cmd}"))
            elif s.kind == "prompt":
                steps.append(
                    Step(kind="prompt", cmd=s.prompt or "", description=f"Ask: {s.prompt}")
                )
            elif s.kind == "if":
                cmd = substitute_vars(s.run or "", self.variables)
                steps.append(
                    Step(
                        kind="if",
                        cmd=cmd,
                        description=f"If ({s.condition}): {cmd}",
                        condition=s.condition,
                    )
                )
        return Plan(goal=self.playbook.name, steps=steps, tab_id=tab_id)
