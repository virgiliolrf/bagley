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

# ── Generator tests ─────────────────────────────────────────────────────────

from bagley.tui.plan_mode.generator import PlanGenerator, PLAN_SYSTEM_SUFFIX


class _StubEngine:
    """Returns a hard-coded JSON plan string regardless of input."""

    PLAN_JSON = """
    {
      "goal": "recon 10.0.0.1",
      "steps": [
        {"kind": "run", "cmd": "nmap -sV 10.0.0.1", "description": "Port scan"},
        {"kind": "prompt", "cmd": "summarize attack surface", "description": "Ask Bagley"}
      ]
    }
    """

    def generate(self, messages, system="", **kwargs):
        return self.PLAN_JSON


def test_generator_produces_plan():
    gen = PlanGenerator(engine=_StubEngine())
    plan = gen.generate(goal="recon 10.0.0.1", tab_id="10.0.0.1")
    assert isinstance(plan, Plan)
    assert plan.goal == "recon 10.0.0.1"
    assert len(plan.steps) == 2
    assert plan.steps[0].kind == "run"
    assert plan.steps[1].kind == "prompt"
    assert plan.tab_id == "10.0.0.1"


def test_generator_system_suffix_present():
    assert "JSON" in PLAN_SYSTEM_SUFFIX
    assert "steps" in PLAN_SYSTEM_SUFFIX


def test_generator_bad_json_raises():
    class _BadEngine:
        def generate(self, messages, system="", **kwargs):
            return "NOT JSON AT ALL }{{"

    gen = PlanGenerator(engine=_BadEngine())
    import pytest as _pytest
    with _pytest.raises(ValueError, match="parse"):
        gen.generate(goal="anything", tab_id="tab0")
