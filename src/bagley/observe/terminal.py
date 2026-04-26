"""PTY tap — executa comando preservando TTY, stream line-by-line pro callback.

Uso:
    tap = TerminalTap()
    result = tap.execute("nmap -sV 10.10.10.5", on_line=lambda line: print(f"live: {line}"))

Diferente do subprocess.run() padrão:
- PTY preserva cores/TTY behavior de ferramentas tipo nmap que buffer-flush só em TTY
- Callback chamado a cada linha em tempo real
- Bagley pode comentar enquanto a ferramenta ainda roda

Apenas Linux/macOS — Windows não tem módulo pty nativo.
"""

from __future__ import annotations

import os
import pty
import select
import subprocess
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class StreamedExecution:
    command: str
    returncode: int
    output: str                       # stdout + stderr merged (PTY junta por padrão)
    duration_s: float


def execute_streamed(
    command: str,
    *,
    on_line: Callable[[str], None] | None = None,
    timeout: float = 300.0,
    env: dict | None = None,
) -> StreamedExecution:
    """Executa shell command em PTY, chama on_line(line) pra cada linha.

    Retorna output completo + returncode ao fim.
    """
    master_fd, slave_fd = pty.openpty()
    start = time.monotonic()
    proc = subprocess.Popen(
        ["/bin/bash", "-c", command],
        stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
        env=env or os.environ.copy(),
        close_fds=True,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)

    buffer = b""
    full_output: list[str] = []

    try:
        while True:
            if time.monotonic() - start > timeout:
                proc.kill()
                full_output.append(f"\n[timeout after {timeout}s]\n")
                break
            rlist, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in rlist:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, _, buffer = buffer.partition(b"\n")
                    text = line.decode("utf-8", errors="replace")
                    full_output.append(text + "\n")
                    if on_line:
                        try:
                            on_line(text)
                        except Exception:
                            pass
            if proc.poll() is not None:
                # drain resto
                try:
                    while True:
                        chunk = os.read(master_fd, 4096)
                        if not chunk:
                            break
                        buffer += chunk
                except OSError:
                    pass
                break
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass
        proc.wait(timeout=5)

    if buffer:
        tail = buffer.decode("utf-8", errors="replace")
        full_output.append(tail)
        if on_line:
            for line in tail.splitlines():
                try:
                    on_line(line)
                except Exception:
                    pass

    return StreamedExecution(
        command=command,
        returncode=proc.returncode or 0,
        output="".join(full_output),
        duration_s=time.monotonic() - start,
    )
