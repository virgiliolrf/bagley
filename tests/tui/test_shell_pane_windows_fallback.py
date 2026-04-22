"""Non-interactive subprocess fallback — Windows only."""
import sys
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows subprocess fallback only tested on Windows"
)

from bagley.tui.services.pty_bridge import SubprocessBridge


def test_subprocess_bridge_captures_stdout():
    bridge = SubprocessBridge(cmd=["cmd", "/c", "echo hello_win"])
    bridge.start()
    output = bridge.read_all(timeout=3.0)
    bridge.close()
    assert b"hello_win" in output


def test_subprocess_bridge_close_does_not_raise():
    bridge = SubprocessBridge(cmd=["cmd", "/c", "echo ok"])
    bridge.start()
    bridge.close()
    assert bridge.is_alive() is False
