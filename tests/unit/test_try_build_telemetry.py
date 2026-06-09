"""Unit tests for _try_build_telemetry() in dadaia_workspace/cli/commands/panel.py.

Verifies that each expected exception type is caught, a warning is logged,
and None is returned — without propagating the exception.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pytest

from dadaia_workspace.cli.commands.panel import _try_build_telemetry


def _patch_imports_ok(monkeypatch: pytest.MonkeyPatch, raise_exc: Exception) -> None:
    """Patch the interior of _try_build_telemetry to raise *raise_exc* after imports."""
    monkeypatch.setattr(
        "dadaia_workspace.cli.commands.panel.container.build_spec_context_service",
        lambda *_: (_ for _ in ()).throw(raise_exc),
    )


def _make_platform_security_error() -> Exception:
    from dadaia_workspace.core.exceptions import PlatformSecurityError

    return PlatformSecurityError(
        "simulated icacls failure",
        feature_name="test-feature",
        platform="test",
    )


@pytest.mark.parametrize(
    "exc,fragment",
    [
        (ImportError("no module telemetry"), "missing dependency"),
        (PermissionError("access denied"), "permission denied"),
        (OSError("disk error"), "OS error"),
        (sqlite3.OperationalError("db locked"), "SQLite"),
        (_make_platform_security_error(), "platform security"),
    ],
)
def test_try_build_telemetry_returns_none_on_expected_exceptions(
    exc: Exception,
    fragment: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Each expected exception type yields None + a warning log."""
    _patch_imports_ok(monkeypatch, exc)

    with caplog.at_level(logging.WARNING, logger="dadaia_workspace.cli.commands.panel"):
        result = _try_build_telemetry(tmp_path)

    assert result is None
    assert any(fragment in record.message for record in caplog.records), (
        f"Expected warning fragment '{fragment}' not found in: {[r.message for r in caplog.records]}"
    )
