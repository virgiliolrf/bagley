"""Tests for playbook YAML loader."""

import textwrap
from pathlib import Path

import pytest

from bagley.tui.playbooks.loader import (
    PlaybookStep,
    Playbook,
    load_playbook,
    scan_playbooks,
    PlaybookValidationError,
)


MINIMAL_YAML = textwrap.dedent("""
    name: HTB initial recon
    description: Fast first pass
    target: "{target}"
    steps:
      - run: "nmap -sV {target}"
      - if: "80 in ports"
        run: "gobuster dir -u http://{target} -w common.txt"
      - prompt: "summarize attack surface"
""").strip()


def test_load_minimal_playbook(tmp_path):
    f = tmp_path / "recon.yml"
    f.write_text(MINIMAL_YAML, encoding="utf-8")
    pb = load_playbook(f)
    assert pb.name == "HTB initial recon"
    assert pb.target_template == "{target}"
    assert len(pb.steps) == 3


def test_step_kinds(tmp_path):
    f = tmp_path / "recon.yml"
    f.write_text(MINIMAL_YAML, encoding="utf-8")
    pb = load_playbook(f)
    assert pb.steps[0].kind == "run"
    assert pb.steps[0].run == "nmap -sV {target}"
    assert pb.steps[1].kind == "if"
    assert pb.steps[1].condition == "80 in ports"
    assert pb.steps[2].kind == "prompt"
    assert pb.steps[2].prompt == "summarize attack surface"


def test_missing_name_raises(tmp_path):
    bad = "target: '{target}'\nsteps:\n  - run: 'nmap {target}'"
    f = tmp_path / "bad.yml"
    f.write_text(bad, encoding="utf-8")
    with pytest.raises(PlaybookValidationError, match="name"):
        load_playbook(f)


def test_scan_playbooks(tmp_path):
    (tmp_path / "a.yml").write_text(MINIMAL_YAML, encoding="utf-8")
    (tmp_path / "b.yml").write_text(MINIMAL_YAML.replace("HTB initial recon", "b"), encoding="utf-8")
    pbs = scan_playbooks(tmp_path)
    assert len(pbs) == 2
    names = {pb.name for pb in pbs}
    assert "HTB initial recon" in names
    assert "b" in names


def test_scan_empty_dir_returns_empty(tmp_path):
    assert scan_playbooks(tmp_path) == []
