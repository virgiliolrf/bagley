"""Tests for plan dataclasses and generator."""

from bagley.tui.plan_mode.plan import Plan, Step, StepStatus


def test_step_defaults():
    s = Step(kind="run", cmd="nmap -sV 10.10.14.1", description="Port scan target")
    assert s.status == StepStatus.PENDING
    assert s.kind == "run"
    assert s.cmd == "nmap -sV 10.10.14.1"
    assert s.description == "Port scan target"


def test_plan_empty():
    p = Plan(goal="recon 10.10.14.1", steps=[])
    assert p.goal == "recon 10.10.14.1"
    assert p.steps == []
    assert p.current_index == 0


def test_plan_current_step():
    steps = [
        Step(kind="run", cmd="nmap -sV 10.10.14.1", description="Scan"),
        Step(kind="run", cmd="gobuster ...", description="Dir bust"),
    ]
    p = Plan(goal="test", steps=steps)
    assert p.current_step() is steps[0]


def test_plan_advance():
    steps = [
        Step(kind="run", cmd="cmd1", description="d1"),
        Step(kind="run", cmd="cmd2", description="d2"),
    ]
    p = Plan(goal="test", steps=steps)
    p.advance()
    assert p.current_index == 1
    assert steps[0].status == StepStatus.DONE


def test_plan_skip():
    steps = [
        Step(kind="run", cmd="cmd1", description="d1"),
        Step(kind="run", cmd="cmd2", description="d2"),
    ]
    p = Plan(goal="test", steps=steps)
    p.skip()
    assert p.current_index == 1
    assert steps[0].status == StepStatus.SKIPPED


def test_plan_is_done_when_all_advanced():
    steps = [Step(kind="run", cmd="c", description="d")]
    p = Plan(goal="test", steps=steps)
    assert not p.is_done()
    p.advance()
    assert p.is_done()
