"""Unit tests for ShutdownHandler adapters (T-018-11).

Both POSIX and Windows adapters are tested here via monkeypatched signal.signal.
Tests pass on all platforms.

Signal-install tests must not be run from a non-main thread — pytest typically
runs tests on the main thread, so this constraint is satisfied.

Scenarios:
  1. PosixSignalShutdownHandler installs both SIGINT and SIGTERM handlers.
  2. WindowsSignalShutdownHandler installs SIGINT handler only (no SIGTERM).
  3. WindowsSignalShutdownHandler emits an INFO log about SIGTERM being skipped.
  4. WindowsSignalShutdownHandler NEVER calls signal.signal with SIGTERM.
  5. Both adapters call server.shutdown() from a daemon thread when handler fires.
  6. container.build_shutdown_handler() returns POSIX handler on linux/darwin.
  7. container.build_shutdown_handler() returns Windows handler on win32.
"""

from __future__ import annotations

import signal
import sys
from http.server import ThreadingHTTPServer
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from dadaia_workspace.infrastructure.signal_shutdown_posix import PosixSignalShutdownHandler
from dadaia_workspace.infrastructure.signal_shutdown_windows import WindowsSignalShutdownHandler

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_server() -> MagicMock:
    """Return a MagicMock with a .shutdown() method."""
    srv = MagicMock(spec=ThreadingHTTPServer)
    srv.shutdown = MagicMock()
    return srv


# ---------------------------------------------------------------------------
# 1. PosixSignalShutdownHandler registers SIGINT + SIGTERM
# ---------------------------------------------------------------------------


def test_posix_handler_installs_sigint_and_sigterm() -> None:
    """PosixSignalShutdownHandler must register handlers for both SIGINT and SIGTERM."""
    installed: list[int] = []

    def _fake_signal(sig: int, handler: Any) -> Any:
        installed.append(sig)
        return signal.SIG_DFL

    with patch("signal.signal", side_effect=_fake_signal):
        PosixSignalShutdownHandler().install(_mock_server())

    assert signal.SIGINT in installed, "SIGINT must be registered"
    assert signal.SIGTERM in installed, "SIGTERM must be registered"


# ---------------------------------------------------------------------------
# 2. WindowsSignalShutdownHandler registers SIGINT only (no SIGTERM)
# ---------------------------------------------------------------------------


def test_windows_handler_installs_sigint_only() -> None:
    """WindowsSignalShutdownHandler must NOT register SIGTERM."""
    installed: list[int] = []

    def _fake_signal(sig: int, handler: Any) -> Any:
        installed.append(sig)
        return signal.SIG_DFL

    with patch("signal.signal", side_effect=_fake_signal):
        WindowsSignalShutdownHandler().install(_mock_server())

    assert signal.SIGINT in installed, "SIGINT must be registered on Windows adapter"
    assert signal.SIGTERM not in installed, (
        "SIGTERM must NOT be registered — signal.signal(SIGTERM,...) raises OSError on Windows"
    )


# ---------------------------------------------------------------------------
# 3. WindowsSignalShutdownHandler emits INFO log about SIGTERM being skipped
# ---------------------------------------------------------------------------


def test_windows_handler_logs_sigterm_skipped(caplog: pytest.LogCaptureFixture) -> None:
    """An INFO message must be logged when SIGTERM is skipped."""
    import logging

    def _fake_signal(sig: int, handler: Any) -> Any:
        return signal.SIG_DFL

    with patch("signal.signal", side_effect=_fake_signal), caplog.at_level(logging.INFO):
        WindowsSignalShutdownHandler().install(_mock_server())

    assert any(
        "SIGTERM" in rec.message and "skipped" in rec.message.lower() for rec in caplog.records
    ), "Expected INFO log mentioning SIGTERM and skipped"


# ---------------------------------------------------------------------------
# 4. WindowsSignalShutdownHandler never calls signal.signal with SIGTERM
# ---------------------------------------------------------------------------


def test_windows_handler_never_calls_signal_with_sigterm() -> None:
    """Explicit assertion that signal.signal is never called with SIGTERM arg."""
    calls: list[tuple[int, Any]] = []

    def _spy(sig: int, handler: Any) -> Any:
        calls.append((sig, handler))
        return signal.SIG_DFL

    with patch("signal.signal", side_effect=_spy):
        WindowsSignalShutdownHandler().install(_mock_server())

    for sig, _ in calls:
        assert sig != signal.SIGTERM, (
            f"signal.signal was called with SIGTERM={signal.SIGTERM}, "
            "which raises OSError on Windows"
        )


# ---------------------------------------------------------------------------
# 5. Handler fires → server.shutdown() called from a daemon thread
# ---------------------------------------------------------------------------


def _extract_handler(sig_target: int) -> Any:
    """Install a real-ish handler and capture it via a spy."""
    captured: dict[int, Any] = {}

    def _spy(sig: int, handler: Any) -> Any:
        captured[sig] = handler
        return signal.SIG_DFL

    with patch("signal.signal", side_effect=_spy):
        PosixSignalShutdownHandler().install(_mock_server())

    return captured.get(sig_target)


def test_posix_handler_calls_shutdown_in_thread_on_sigint() -> None:
    """When the SIGINT handler fires, server.shutdown() must be called from a
    daemon thread (not from the signal frame itself).
    """
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

    # Give the daemon thread a moment to call server.shutdown().
    server.shutdown._mock_wait_called = True  # type: ignore[attr-defined]
    # Poll for up to 1 s.
    for _ in range(20):
        if server.shutdown.called:
            break
        import time

        time.sleep(0.05)

    assert server.shutdown.called, "server.shutdown() must be called after SIGINT"


# ---------------------------------------------------------------------------
# 6 & 7. container.build_shutdown_handler() selects the right adapter
# ---------------------------------------------------------------------------


def test_container_returns_posix_handler_on_linux() -> None:
    """build_shutdown_handler() must return PosixSignalShutdownHandler on linux."""
    with patch.object(sys, "platform", "linux"):
        import importlib

        import dadaia_workspace.container as _c

        importlib.reload(_c)
        handler = _c.build_shutdown_handler()

    assert isinstance(handler, PosixSignalShutdownHandler), (
        f"Expected PosixSignalShutdownHandler on linux, got {type(handler)}"
    )


def test_container_returns_posix_handler_on_darwin() -> None:
    """build_shutdown_handler() must return PosixSignalShutdownHandler on darwin."""
    with patch.object(sys, "platform", "darwin"):
        import importlib

        import dadaia_workspace.container as _c

        importlib.reload(_c)
        handler = _c.build_shutdown_handler()

    assert isinstance(handler, PosixSignalShutdownHandler), (
        f"Expected PosixSignalShutdownHandler on darwin, got {type(handler)}"
    )


def test_container_returns_windows_handler_on_win32() -> None:
    """build_shutdown_handler() must return WindowsSignalShutdownHandler on win32."""
    with patch.object(sys, "platform", "win32"):
        import importlib

        import dadaia_workspace.container as _c

        importlib.reload(_c)
        handler = _c.build_shutdown_handler()

    assert isinstance(handler, WindowsSignalShutdownHandler), (
        f"Expected WindowsSignalShutdownHandler on win32, got {type(handler)}"
    )


# ---------------------------------------------------------------------------
# Extra: panel/server.py contains only build_panel_http_server
# ---------------------------------------------------------------------------


def test_server_module_has_no_install_shutdown_handlers() -> None:
    """panel/server.py must not contain install_shutdown_handlers after T-018-11."""
    import ast
    from pathlib import Path

    src = (
        Path(__file__).parents[3] / "dadaia_workspace" / "features" / "panel" / "server.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    func_names = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    ]
    assert "install_shutdown_handlers" not in func_names, (
        "install_shutdown_handlers must be deleted from panel/server.py in T-018-11"
    )
    assert "serve_blocking" not in func_names, (
        "serve_blocking must be deleted from panel/server.py in T-018-11"
    )
    assert "build_panel_http_server" in func_names, (
        "build_panel_http_server must remain in panel/server.py"
    )
