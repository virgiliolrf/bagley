"""ObserveService tests — mock terminal.py tap."""
import pytest
from unittest.mock import MagicMock, patch
from bagley.tui.services.observe import ObserveService, ObserveError


def _make_service() -> ObserveService:
    return ObserveService()


def test_attach_calls_tap_with_pid():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = False
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.attach(pid=1234)
    mock_tap.attach.assert_called_once_with(1234)


def test_attach_when_already_active_raises():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = True
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        with pytest.raises(ObserveError, match="already attached"):
            svc.attach(pid=1234)


def test_stop_calls_tap_detach():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = True
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.stop()
    mock_tap.detach.assert_called_once()


def test_stop_when_not_active_is_noop():
    svc = _make_service()
    mock_tap = MagicMock()
    mock_tap.is_active.return_value = False
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.stop()  # should not raise
    mock_tap.detach.assert_not_called()


def test_read_chunk_returns_bytes_from_tap():
    svc = _make_service()
    mock_tap = MagicMock()
    # Inactive before attach, active afterwards — matches real tap semantics.
    mock_tap.is_active.side_effect = [False, True]
    mock_tap.read_chunk.return_value = b"some output\n"
    with patch("bagley.tui.services.observe._get_tap", return_value=mock_tap):
        svc.attach(pid=9999)
        chunk = svc.read_chunk()
    assert b"some output" in chunk
