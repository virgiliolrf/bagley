"""PTY spawn tests — Linux/macOS only."""
import sys
import time
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="Real PTY not available on Windows"
)

from bagley.tui.services.pty_bridge import PtyBridge


def test_pty_bridge_spawns_and_reads_output():
    bridge = PtyBridge(cmd=["bash", "-c", "echo hello_pty"])
    bridge.start()
    output = b""
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and b"hello_pty" not in output:
        chunk = bridge.read(timeout=0.1)
        if chunk:
            output += chunk
    bridge.close()
    assert b"hello_pty" in output


def test_pty_bridge_write_then_read():
    bridge = PtyBridge(cmd=["bash"])
    bridge.start()
    bridge.write(b"echo write_test\n")
    output = b""
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and b"write_test" not in output:
        chunk = bridge.read(timeout=0.1)
        if chunk:
            output += chunk
    bridge.close()
    assert b"write_test" in output


def test_pty_bridge_close_terminates_process():
    bridge = PtyBridge(cmd=["bash"])
    bridge.start()
    bridge.close()
    assert bridge.is_alive() is False
