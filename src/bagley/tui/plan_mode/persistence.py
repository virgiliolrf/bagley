"""Save and load Plan objects to/from .bagley/plans/*.yml."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from bagley.tui.plan_mode.plan import Plan, Step, StepStatus


def plan_dir(base: Optional[Path] = None) -> Path:
    """Return the default plans directory (.bagley/plans/)."""
    root = base or Path.cwd() / ".bagley"
    d = root / "plans"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_plan(plan: Plan, base_dir: Optional[Path] = None) -> Path:
    """Serialize *plan* to YAML and write to base_dir.

    File is named ``<tab_id>-<iso_ts>.yml`` with colons replaced so it
    is safe on Windows.
    """
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
    plan.timestamp = ts
    safe_tab = plan.tab_id.replace("/", "_").replace(":", "_")
    filename = f"{safe_tab}-{ts}.yml"

    dest = (base_dir or plan_dir()) / filename

    data = {
        "goal": plan.goal,
        "tab_id": plan.tab_id,
        "timestamp": plan.timestamp,
        "current_index": plan.current_index,
        "steps": [
            {
                "kind": s.kind,
                "cmd": s.cmd,
                "description": s.description,
                "status": s.status.value,
                "condition": s.condition,
                "output": s.output,
            }
            for s in plan.steps
        ],
    }

    dest.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return dest


def load_plan(path: Path) -> Plan:
    """Deserialize a YAML plan file back into a *Plan* object."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = [
        Step(
            kind=s["kind"],
            cmd=s["cmd"],
            description=s["description"],
            status=StepStatus(s.get("status", "pending")),
            condition=s.get("condition"),
            output=s.get("output"),
        )
        for s in data.get("steps", [])
    ]
    return Plan(
        goal=data["goal"],
        steps=steps,
        tab_id=data.get("tab_id", "unknown"),
        current_index=data.get("current_index", 0),
        timestamp=data.get("timestamp", ""),
    )
