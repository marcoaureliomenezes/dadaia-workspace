"""Unit tests for ShutdownHandler adapters (T-018-11).

Both POSIX and Windows adapters are tested here via monkeypatched signal.signal.
Tests pass on all platforms.

Signal-install tests must not be run from a non-main thread — pytest typically
runs tests on the main thread, so this constraint is satisfied.
"""

from __future__ import annotations

import signal
from http.server import ThreadingHTTPServer
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dadaia_workspace.infrastructure.signal_shutdown_posix import PosixSignalShutdownHandler
from dadaia_workspace.infrastructure.signal_shutdown_windows import WindowsSignalShutdownHandler


def _mock_server() -> MagicMock:
    """Return a MagicMock with a .shutdown() method."""
    srv = MagicMock(spec=ThreadingHTTPServer)
    srv.shutdown = MagicMock()
    return srv


def test_posix_handler_calls_shutdown_in_thread_on_sigint() -> None:
    """When the SIGINT handler fires, server.shutdown() must be called from a
    daemon thread (not from the signal frame itself)."""
    server = _mock_server()
    captured: dict[int, Any] = {}

    def _spy(sig: int, handler: Any) -> Any:
        captured[sig] = handler
        return signal.SIG_DFL

    with patch("signal.signal", side_effect=_spy):
        PosixSignalShutdownHandler().install(server)

    # Fire the SIGINT handler synchronously (simulated signal delivery).
    handler = captured[signal.SIGINT]
    assert handler is not None, "SIGINT handler must be captured"
    handler(signal.SIGINT, None)

    # Poll for up to 1 s for the daemon thread to call server.shutdown().
    for _ in range(20):
        if server.shutdown.called:
            break
        import time

        time.sleep(0.05)

    assert server.shutdown.called, "server.shutdown() must be called after SIGINT"


def test_posix_install_and_windows_signal_matrix() -> None:
    """PosixSignalShutdownHandler installs BOTH SIGINT and SIGTERM; the Windows
    adapter installs SIGINT only, NEVER calls signal.signal(SIGTERM, ...) (which
    raises OSError on Windows), and logs an INFO message explaining the skip."""
    import logging

    posix_installed: list[int] = []

    def _fake_signal_posix(sig: int, handler: Any) -> Any:
        posix_installed.append(sig)
        return signal.SIG_DFL

    with patch("signal.signal", side_effect=_fake_signal_posix):
        PosixSignalShutdownHandler().install(_mock_server())
    assert signal.SIGINT in posix_installed
    assert signal.SIGTERM in posix_installed

    windows_calls: list[tuple[int, Any]] = []
    caplog_records: list[logging.LogRecord] = []

    class _CollectingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            caplog_records.append(record)

    def _spy_windows(sig: int, handler: Any) -> Any:
        windows_calls.append((sig, handler))
        return signal.SIG_DFL

    logger = logging.getLogger("dadaia_workspace.infrastructure.signal_shutdown_windows")
    handler_obj = _CollectingHandler()
    logger.addHandler(handler_obj)
    logger.setLevel(logging.INFO)
    try:
        with patch("signal.signal", side_effect=_spy_windows):
            WindowsSignalShutdownHandler().install(_mock_server())
    finally:
        logger.removeHandler(handler_obj)

    windows_installed = [sig for sig, _ in windows_calls]
    assert signal.SIGINT in windows_installed
    assert signal.SIGTERM not in windows_installed, (
        "signal.signal must NEVER be called with SIGTERM on the Windows adapter — "
        "it raises OSError on real Windows"
    )
    assert any(
        "SIGTERM" in rec.message and "skipped" in rec.message.lower() for rec in caplog_records
    ), "Expected INFO log mentioning SIGTERM and skipped"


@pytest.mark.parametrize(
    ("platform_str", "expected"),
    [
        ("linux", PosixSignalShutdownHandler),
        ("darwin", PosixSignalShutdownHandler),
        ("win32", WindowsSignalShutdownHandler),
    ],
)
def test_container_selects_shutdown_handler_by_platform(platform_str: str, expected: type) -> None:
    """build_shutdown_handler() selects PosixSignalShutdownHandler on linux/darwin
    and WindowsSignalShutdownHandler on win32."""
    from dadaia_workspace.core.platform import Capabilities

    caps = Capabilities.detect(platform_str)
    with patch("dadaia_workspace.core.platform.PLATFORM", caps):
        import dadaia_workspace.container as _c

        handler = _c.build_shutdown_handler()

    assert isinstance(handler, expected)
