"""Load and validate .playbooks/*.yml files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


class PlaybookValidationError(ValueError):
    """Raised when a playbook YAML fails schema validation."""


@dataclass
class PlaybookStep:
    kind: str                           # "run" | "if" | "prompt"
    run: Optional[str] = None           # shell command (run / if steps)
    condition: Optional[str] = None     # if-step condition
    prompt: Optional[str] = None        # prompt step text


@dataclass
class Playbook:
    name: str
    description: str
    target_template: str
    steps: list[PlaybookStep] = field(default_factory=list)
    source: Optional[Path] = None


def _parse_step(raw: dict) -> PlaybookStep:
    if "prompt" in raw:
        return PlaybookStep(kind="prompt", prompt=raw["prompt"])
    if "if" in raw:
        return PlaybookStep(kind="if", condition=raw["if"], run=raw.get("run", ""))
    if "run" in raw:
        return PlaybookStep(kind="run", run=raw["run"])
    raise PlaybookValidationError(f"Unknown step schema: {raw}")


def load_playbook(path: Path) -> Playbook:
    """Parse a single playbook YAML file and return a Playbook."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PlaybookValidationError("Playbook must be a YAML mapping")
    if "name" not in data:
        raise PlaybookValidationError("Playbook is missing required field 'name'")

    steps = [_parse_step(s) for s in data.get("steps", [])]
    return Playbook(
        name=data["name"],
        description=data.get("description", ""),
        target_template=data.get("target", "{target}"),
        steps=steps,
        source=path,
    )


def scan_playbooks(directory: Optional[Path] = None) -> list[Playbook]:
    """Scan *directory* (default: .playbooks/) for *.yml files and load them."""
    d = directory or (Path.cwd() / ".playbooks")
    if not d.exists():
        return []
    playbooks: list[Playbook] = []
    for yml in sorted(d.glob("*.yml")):
        try:
            playbooks.append(load_playbook(yml))
        except (PlaybookValidationError, yaml.YAMLError):
            pass  # Skip malformed files silently; caller can log
    return playbooks
