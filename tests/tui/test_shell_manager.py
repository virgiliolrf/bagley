"""ShellManager lifecycle tests."""
import sys
import pytest
from unittest.mock import MagicMock, patch
from bagley.tui.services.shell_manager import ShellManager, ShellRecord, ShellState


def _make_manager() -> ShellManager:
    return ShellManager()


def test_spawn_creates_record():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        record = mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    assert record.name == "rev-shell-1"
    assert record.tab_id == "10.10.14.1"
    assert record.state == ShellState.FOREGROUND
    mock_bridge.start.assert_called_once()


def test_background_moves_to_background_state():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        record = mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    mgr.background(name="rev-shell-1")
    assert mgr.get("rev-shell-1").state == ShellState.BACKGROUND


def test_foreground_restores_foreground_state():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    mgr.background(name="rev-shell-1")
    mgr.foreground(name="rev-shell-1")
    assert mgr.get("rev-shell-1").state == ShellState.FOREGROUND


def test_close_sends_sigterm_and_removes_from_registry():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        mgr.spawn(name="rev-shell-1", cmd=["bash"], tab_id="10.10.14.1")
    mgr.close(name="rev-shell-1")
    mock_bridge.close.assert_called_once()
    assert mgr.get("rev-shell-1") is None


def test_list_shells_returns_all():
    mgr = _make_manager()
    with patch("bagley.tui.services.shell_manager._make_bridge") as mock_bridge_factory:
        mock_bridge = MagicMock()
        mock_bridge.is_alive.return_value = True
        mock_bridge_factory.return_value = mock_bridge
        mgr.spawn(name="shell-a", cmd=["bash"], tab_id="10.10.14.1")
        mgr.spawn(name="shell-b", cmd=["bash"], tab_id="10.10.14.2")
    shells = mgr.list_shells()
    names = [s.name for s in shells]
    assert "shell-a" in names
    assert "shell-b" in names
