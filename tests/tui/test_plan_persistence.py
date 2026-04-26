"""Tests for plan YAML persistence."""

import os
import tempfile
from pathlib import Path

from bagley.tui.plan_mode.plan import Plan, Step, StepStatus
from bagley.tui.plan_mode.persistence import save_plan, load_plan, plan_dir


def _make_plan() -> Plan:
    steps = [
        Step(kind="run", cmd="nmap -sV 10.0.0.1", description="Port scan"),
        Step(kind="prompt", cmd="summarize", description="Ask Bagley to summarize"),
    ]
    return Plan(goal="recon 10.0.0.1", steps=steps, tab_id="10.0.0.1")


def test_save_creates_file(tmp_path):
    p = _make_plan()
    saved = save_plan(p, base_dir=tmp_path)
    assert saved.exists()
    assert saved.suffix == ".yml"
    assert "10.0.0.1" in saved.name


def test_roundtrip(tmp_path):
    original = _make_plan()
    saved = save_plan(original, base_dir=tmp_path)
    restored = load_plan(saved)
    assert restored.goal == original.goal
    assert len(restored.steps) == len(original.steps)
    assert restored.steps[0].cmd == "nmap -sV 10.0.0.1"
    assert restored.steps[0].kind == "run"
    assert restored.steps[1].kind == "prompt"


def test_roundtrip_preserves_status(tmp_path):
    p = _make_plan()
    p.steps[0].status = StepStatus.DONE
    p.steps[1].status = StepStatus.SKIPPED
    saved = save_plan(p, base_dir=tmp_path)
    restored = load_plan(saved)
    assert restored.steps[0].status == StepStatus.DONE
    assert restored.steps[1].status == StepStatus.SKIPPED


def test_plan_dir_default():
    d = plan_dir()
    assert d.name == "plans"
    assert ".bagley" in str(d)
