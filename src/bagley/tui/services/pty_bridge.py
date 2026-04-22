"""PTY bridge: real PTY on Linux/macOS, subprocess fallback on Windows.

Usage:
    bridge = PtyBridge(cmd=["bash"])   # or SubprocessBridge on Windows
    bridge.start()
    bridge.write(b"ls\n")
    chunk = bridge.read(timeout=0.5)   # bytes or b""
    bridge.close()
    alive = bridge.is_alive()
"""
from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from typing import Optional


class Bridge(ABC):
    """Abstract base for PTY and subprocess bridges."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def write(self, data: bytes) -> None: ...

    @abstractmethod
    def read(self, timeout: float = 0.1) -> bytes: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def is_alive(self) -> bool: ...


class PtyBridge(Bridge):
    """POSIX PTY wrapper. Linux/macOS only.

    Forks a child process attached to a pseudo-terminal. Reads from the master
    fd with a configurable timeout so the TUI read loop stays non-blocking.
    """

    def __init__(self, cmd: list[str]) -> None:
        if sys.platform == "win32":
            raise RuntimeError("PtyBridge is not supported on Windows; use SubprocessBridge")
        self._cmd = cmd
        self._master_fd: Optional[int] = None
        self._pid: Optional[int] = None

    def start(self) -> None:
        import pty  # stdlib, POSIX only
        self._pid, self._master_fd = pty.fork()
        if self._pid == 0:
            # child
            os.execvp(self._cmd[0], self._cmd)
            # execvp never returns on success; if it fails the child exits

    def write(self, data: bytes) -> None:
        if self._master_fd is not None:
            os.write(self._master_fd, data)

    def read(self, timeout: float = 0.1) -> bytes:
        if self._master_fd is None:
            return b""
        r, _, _ = select.select([self._master_fd], [], [], timeout)
        if r:
            try:
                return os.read(self._master_fd, 4096)
            except OSError:
                return b""
        return b""

    def close(self) -> None:
        if self._pid is not None:
            try:
                os.kill(self._pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if self._master_fd is not None:
            try:
                os.close(self._master_fd)
            except OSError:
                pass
        self._pid = None
        self._master_fd = None

    def is_alive(self) -> bool:
        if self._pid is None:
            return False
        try:
            result = os.waitpid(self._pid, os.WNOHANG)
            return result == (0, 0)
        except ChildProcessError:
            return False


class SubprocessBridge(Bridge):
    """Non-interactive subprocess fallback for Windows.

    Cannot drive interactive programs (no PTY allocation). Captures stdout/
    stderr as a byte stream. Used as a degraded fallback so the TUI renders
    tool output even if it cannot provide an interactive shell.
    """

    def __init__(self, cmd: list[str]) -> None:
        self._cmd = cmd
        self._proc: Optional[subprocess.Popen] = None
        self._buf: bytes = b""
        self._lock = threading.Lock()
        self._reader: Optional[threading.Thread] = None

    def start(self) -> None:
        self._proc = subprocess.Popen(
            self._cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self._reader = threading.Thread(target=self._drain, daemon=True)
        self._reader.start()

    def _drain(self) -> None:
        assert self._proc is not None
        assert self._proc.stdout is not None
        for chunk in iter(lambda: self._proc.stdout.read(4096), b""):
            with self._lock:
                self._buf += chunk

    def write(self, data: bytes) -> None:
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.write(data)
                self._proc.stdin.flush()
            except BrokenPipeError:
                pass

    def read(self, timeout: float = 0.1) -> bytes:
        with self._lock:
            chunk = self._buf
            self._buf = b""
        return chunk

    def read_all(self, timeout: float = 5.0) -> bytes:
        if self._proc:
            try:
                self._proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                pass
        return self.read()

    def close(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None

    def is_alive(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.poll() is None
