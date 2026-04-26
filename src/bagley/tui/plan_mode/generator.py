"""Generate a Plan by prompting Bagley with a structured system suffix."""

from __future__ import annotations

import json
import re
from typing import Any

from bagley.tui.plan_mode.plan import Plan, Step

PLAN_SYSTEM_SUFFIX = """
You are in PLAN MODE. Your entire response MUST be a single valid JSON object and
nothing else — no prose before or after. Schema:

{
  "goal": "<the goal restated>",
  "steps": [
    {"kind": "run",    "cmd": "<shell command>",  "description": "<one sentence>"},
    {"kind": "prompt", "cmd": "<question/task>",  "description": "<one sentence>"},
    {"kind": "if",     "cmd": "<shell command>",  "description": "<one sentence>",
     "condition": "<python-evaluable condition using variables: ports, hosts>"}
  ]
}

Only use kinds: run, prompt, if.
Do not add commentary outside the JSON block.
"""


class PlanGenerator:
    """Ask the Bagley engine to generate a Plan for *goal*."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def generate(self, goal: str, tab_id: str = "recon") -> Plan:
        messages = [{"role": "user", "content": f"Generate a plan to: {goal}"}]
        raw = self.engine.generate(messages, system=PLAN_SYSTEM_SUFFIX)

        # Strip markdown fences if model wrapped the JSON
        raw = re.sub(r"^```[a-z]*\n?", "", raw.strip(), flags=re.MULTILINE)
        raw = re.sub(r"\n?```$", "", raw.strip(), flags=re.MULTILINE)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Could not parse plan JSON from model: {exc}") from exc

        steps = [
            Step(
                kind=s["kind"],
                cmd=s["cmd"],
                description=s.get("description", ""),
                condition=s.get("condition"),
            )
            for s in data.get("steps", [])
        ]
        return Plan(goal=data.get("goal", goal), steps=steps, tab_id=tab_id)
