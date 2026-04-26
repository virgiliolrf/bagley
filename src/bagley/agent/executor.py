"""Executor com human-in-the-loop. Toda execução passa por confirmação + blocklist.

Dois modos:
- execute(): subprocess padrão, output ao fim
- execute_with_stream(): PTY tap, callback por linha em real-time (pra commentator)
"""

from __future__ import annotations

import datetime as dt
import os
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from bagley.agent.safeguards import Scope, check_all


AUDIT_LOG = Path(os.environ.get("AUDIT_LOG", ".bagley/audit.log"))


@dataclass
class Execution:
    command: str
    returncode: int
    stdout: str
    stderr: str
    blocked: bool = False
    reason: str = ""


def _audit(entry: str) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{dt.datetime.now().isoformat()} {entry}\n")


def confirm(command: str, prompt_fn=input) -> bool:
    ans = prompt_fn(f"Executar? [y/N]: ").strip().lower()
    return ans in {"y", "yes", "s", "sim"}


def execute(command: str, *, scope: Scope | None = None, confirm_fn=confirm,
            timeout: int = 120, disable_safeguard: bool = False) -> Execution:
    if disable_safeguard:
        _audit(f"SAFEGUARD_BYPASS {command!r}")
    else:
        verdict = check_all(command, scope)
        if not verdict.allowed:
            _audit(f"BLOCKED {command!r} — {verdict.reason}")
            return Execution(command, -1, "", verdict.reason, blocked=True, reason=verdict.reason)

    if not confirm_fn(command):
        _audit(f"DECLINED {command!r}")
        return Execution(command, -1, "", "user declined", blocked=True, reason="declined")

    _audit(f"EXEC {command!r}{' [SAFEGUARD_OFF]' if disable_safeguard else ''}")
    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        _audit(f"TIMEOUT {command!r}")
        return Execution(command, -1, exc.stdout or "", exc.stderr or "timeout", blocked=False, reason="timeout")
    return Execution(command, proc.returncode, proc.stdout, proc.stderr)


def execute_with_stream(
    command: str, *,
    scope: Scope | None = None,
    confirm_fn=confirm,
    on_line: Callable[[str], None] | None = None,
    timeout: int = 300,
    disable_safeguard: bool = False,
) -> Execution:
    """Executa via PTY, chama on_line(line) em tempo real. Linux/macOS only.

    Fallback pro subprocess.run() em Windows (sem PTY nativo).
    """
    if disable_safeguard:
        _audit(f"SAFEGUARD_BYPASS_STREAM {command!r}")
    else:
        verdict = check_all(command, scope)
        if not verdict.allowed:
            _audit(f"BLOCKED {command!r} — {verdict.reason}")
            return Execution(command, -1, "", verdict.reason, blocked=True, reason=verdict.reason)
    if not confirm_fn(command):
        _audit(f"DECLINED {command!r}")
        return Execution(command, -1, "", "user declined", blocked=True, reason="declined")

    _audit(f"EXEC_STREAM {command!r}{' [SAFEGUARD_OFF]' if disable_safeguard else ''}")
    if platform.system() == "Windows":
        # Fallback — sem PTY, executa normal e faz on_line pós-factum
        ex = execute(command, scope=scope, confirm_fn=lambda c: True, timeout=timeout,
                     disable_safeguard=disable_safeguard)
        if on_line and ex.stdout:
            for line in ex.stdout.splitlines():
                try:
                    on_line(line)
                except Exception:
                    pass
        return ex

    # Unix path — usa observe.terminal.execute_streamed
    from bagley.observe.terminal import execute_streamed
    result = execute_streamed(command, on_line=on_line, timeout=timeout)
    return Execution(
        command=command,
        returncode=result.returncode,
        stdout=result.output,
        stderr="",  # PTY junta; mantemos só stdout
    )
