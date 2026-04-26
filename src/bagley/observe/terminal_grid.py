"""Multi-terminal awareness via tmux capture-pane.

Bagley enumera todos os panes ativos, lê conteúdo, correlaciona.

Uso:
    grid = TerminalGrid()
    panes = grid.list_panes()
    for p in panes:
        content = grid.read_pane(p.id, lines=50)
        # analisa o que tá rolando

Requer tmux instalado e sessão tmux ativa. Se não estiver em tmux, use fallback `screen -X hardcopy`.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Pane:
    id: str              # tmux pane id (%0, %1 etc)
    window: str
    session: str
    command: str         # current foreground command
    title: str
    width: int
    height: int


def _tmux(*args, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True, **kwargs)


class TerminalGrid:
    def __init__(self) -> None:
        if not self._tmux_available():
            raise RuntimeError("tmux not available or no session running")

    def _tmux_available(self) -> bool:
        r = _tmux("list-sessions")
        return r.returncode == 0

    def list_panes(self) -> list[Pane]:
        r = _tmux("list-panes", "-a",
                  "-F", "#{pane_id}\t#{window_name}\t#{session_name}\t"
                        "#{pane_current_command}\t#{pane_title}\t#{pane_width}\t#{pane_height}")
        if r.returncode != 0:
            return []
        panes: list[Pane] = []
        for line in r.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            panes.append(Pane(
                id=parts[0], window=parts[1], session=parts[2],
                command=parts[3], title=parts[4],
                width=int(parts[5]), height=int(parts[6]),
            ))
        return panes

    def read_pane(self, pane_id: str, lines: int = 100) -> str:
        """Captura as últimas `lines` linhas do pane."""
        r = _tmux("capture-pane", "-t", pane_id, "-p", "-S", f"-{lines}")
        if r.returncode != 0:
            return ""
        return r.stdout

    def new_pane(self, session: str = "bagley", window: str = "work",
                 command: str = "") -> str | None:
        """Abre novo pane. Retorna pane_id ou None."""
        # Cria session se não existe
        _tmux("new-session", "-d", "-s", session)
        _tmux("new-window", "-t", session, "-n", window)
        r = _tmux("split-window", "-t", f"{session}:{window}", "-P",
                  "-F", "#{pane_id}", command) if command \
            else _tmux("split-window", "-t", f"{session}:{window}", "-P", "-F", "#{pane_id}")
        if r.returncode != 0:
            return None
        return r.stdout.strip()

    def send(self, pane_id: str, text: str, enter: bool = True) -> bool:
        args = ["send-keys", "-t", pane_id, text]
        if enter:
            args.append("Enter")
        return _tmux(*args).returncode == 0

    def kill_pane(self, pane_id: str) -> bool:
        return _tmux("kill-pane", "-t", pane_id).returncode == 0


class TerminalWatcher:
    """Poll-based watcher que notifica sobre mudanças em todos os panes."""

    def __init__(self, grid: TerminalGrid, poll_interval: float = 2.0) -> None:
        self.grid = grid
        self.poll_interval = poll_interval
        self._last_hashes: dict[str, int] = {}
        self._stop = False

    def poll_once(self) -> list[tuple[Pane, str]]:
        """Retorna lista de (pane, novo_conteúdo) pros panes que mudaram."""
        changes: list[tuple[Pane, str]] = []
        for pane in self.grid.list_panes():
            content = self.grid.read_pane(pane.id, lines=200)
            h = hash(content)
            if self._last_hashes.get(pane.id) != h:
                self._last_hashes[pane.id] = h
                changes.append((pane, content))
        return changes

    def watch_forever(self, callback) -> None:
        while not self._stop:
            for pane, content in self.poll_once():
                try:
                    callback(pane, content)
                except Exception:
                    pass
            time.sleep(self.poll_interval)

    def stop(self) -> None:
        self._stop = True
