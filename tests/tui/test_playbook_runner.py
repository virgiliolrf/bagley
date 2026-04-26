"""Tests for playbook runner — step execution and if-condition evaluation."""

from bagley.tui.playbooks.loader import Playbook, PlaybookStep
from bagley.tui.playbooks.runner import PlaybookRunner, substitute_vars, eval_condition


def test_substitute_vars_basic():
    assert substitute_vars("nmap -sV {target}", {"target": "10.0.0.1"}) == "nmap -sV 10.0.0.1"


def test_substitute_vars_multiple():
    assert substitute_vars("{a} {b}", {"a": "hello", "b": "world"}) == "hello world"


def test_eval_condition_ports_in():
    # Simple expression: "80 in ports"
    context = {"ports": [22, 80, 443]}
    assert eval_condition("80 in ports", context) is True
    assert eval_condition("8080 in ports", context) is False


def test_eval_condition_invalid_returns_false():
    assert eval_condition("INVALID SYNTAX !!!{}", {}) is False


def test_runner_converts_to_plan(tmp_path):
    pb = Playbook(
        name="test",
        description="",
        target_template="{target}",
        steps=[
            PlaybookStep(kind="run", run="nmap -sV {target}"),
            PlaybookStep(kind="prompt", prompt="summarize"),
        ],
    )
    runner = PlaybookRunner(playbook=pb, variables={"target": "10.0.0.1"})
    plan = runner.to_plan(tab_id="10.0.0.1")
    assert plan.goal == "test"
    assert len(plan.steps) == 2
    assert plan.steps[0].cmd == "nmap -sV 10.0.0.1"
    assert plan.steps[1].kind == "prompt"
    assert plan.steps[1].cmd == "summarize"


def test_runner_if_step_becomes_conditional_step(tmp_path):
    pb = Playbook(
        name="test",
        description="",
        target_template="{target}",
        steps=[
            PlaybookStep(kind="if", condition="80 in ports", run="gobuster dir -u http://{target}"),
        ],
    )
    runner = PlaybookRunner(playbook=pb, variables={"target": "10.0.0.1"})
    plan = runner.to_plan(tab_id="10.0.0.1")
    assert plan.steps[0].kind == "if"
    assert plan.steps[0].condition == "80 in ports"
    assert "gobuster" in plan.steps[0].cmd
