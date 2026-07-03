"""TelemetryService permission-hardening routing (v0.1.53 FR4, CWE-732 Tier-2).

The service hardens two paths to owner-only: the state directory (in ``__init__``) and the
SQLite DB file (each refresh). Both must route through the injected ``FilePermissionSetter``
(so a Windows host applies an ``icacls`` ACL instead of a silent-no-op ``os.chmod``), and
the direct-``os.chmod`` fallback must fire ONLY where POSIX chmod actually has effect
(``PLATFORM.has_posix_chmod``). These DI-fake tests exercise both the injected-setter path
(including the ``PlatformSecurityError`` -> INFO degrade) and the setter-less fallback on a
Windows-shaped platform capability.

The Windows capability is supplied by constructing a genuine ``Capabilities.detect("win32")``
snapshot and monkeypatching the module-level ``PLATFORM`` name — the ``Capabilities``
dataclass is frozen, so ``setattr`` on an instance is never used.
"""

from __future__ import annotations

import logging
import os
import pathlib
from typing import Any

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.exceptions import PlatformSecurityError  # noqa: E402
from dadaia_workspace.core.platform import Capabilities  # noqa: E402
from dadaia_workspace.features.telemetry import service as service_mod  # noqa: E402
from dadaia_workspace.features.telemetry.service import TelemetryService  # noqa: E402


class _RecordingSetter:
    """FilePermissionSetter fake that records every restriction call."""

    def __init__(self) -> None:
        self.dir_calls: list[tuple[pathlib.Path, int]] = []
        self.file_calls: list[tuple[pathlib.Path, int]] = []

    def restrict_dir_to_owner(self, path: pathlib.Path, mode: int = 0o700) -> None:
        self.dir_calls.append((path, mode))

    def restrict_to_owner(self, path: pathlib.Path, mode: int = 0o600) -> None:
        self.file_calls.append((path, mode))


class _RaisingSetter:
    """FilePermissionSetter fake that fails as a Tier-1 restriction would on Windows."""

    def restrict_dir_to_owner(self, path: pathlib.Path, mode: int = 0o700) -> None:
        raise PlatformSecurityError(
            "icacls unavailable", feature_name="telemetry-perms", platform="win32"
        )

    def restrict_to_owner(self, path: pathlib.Path, mode: int = 0o600) -> None:
        raise PlatformSecurityError(
            "icacls unavailable", feature_name="telemetry-perms", platform="win32"
        )


def _make_service(
    *,
    state_dir: pathlib.Path,
    workspace_root: pathlib.Path,
    permission_setter: Any | None = None,
) -> TelemetryService:
    """Construct a TelemetryService with trivial DI parts (no refresh machinery needed)."""
    return TelemetryService(
        dao_factory=lambda: None,
        aggregator=object(),
        reader_factory=lambda: (),
        pricing_module=object(),
        workspace_root=workspace_root,
        state_dir=state_dir,
        spec_context_service=None,
        permission_setter=permission_setter,
        _getuid_fn=lambda: 1000,
    )


def test_state_dir_restriction_routes_through_injected_setter(tmp_path: pathlib.Path) -> None:
    setter = _RecordingSetter()
    state_dir = tmp_path / "state"
    _make_service(state_dir=state_dir, workspace_root=tmp_path, permission_setter=setter)

    assert setter.dir_calls == [(state_dir, 0o700)]
    assert setter.file_calls == []


def test_setter_platform_security_error_degrades_with_info(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger=service_mod.logger.name):
        # Construction must NOT raise even though the setter fails (Tier-2 degrade).
        _make_service(
            state_dir=tmp_path / "state",
            workspace_root=tmp_path,
            permission_setter=_RaisingSetter(),
        )
    messages = [r.getMessage() for r in caplog.records]
    assert any("degraded mode" in m and "directory" in m for m in messages), messages


def test_no_setter_posix_present_uses_direct_chmod(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(service_mod, "PLATFORM", Capabilities.detect("linux"))
    chmod_calls: list[tuple[Any, int]] = []
    monkeypatch.setattr(os, "chmod", lambda p, m: chmod_calls.append((p, m)))

    state_dir = tmp_path / "state"
    _make_service(state_dir=state_dir, workspace_root=tmp_path, permission_setter=None)

    assert chmod_calls == [(state_dir, 0o700)]


def test_no_setter_posix_absent_skips_direct_chmod(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Windows-shaped capability: has_posix_chmod is False, so os.chmod (a silent no-op on
    # Windows) must be SKIPPED rather than giving false confidence (CWE-732).
    monkeypatch.setattr(service_mod, "PLATFORM", Capabilities.detect("win32"))
    chmod_calls: list[tuple[Any, int]] = []
    monkeypatch.setattr(os, "chmod", lambda p, m: chmod_calls.append((p, m)))

    _make_service(state_dir=tmp_path / "state", workspace_root=tmp_path, permission_setter=None)

    assert chmod_calls == []


def test_db_file_path_routes_file_restriction_through_setter(tmp_path: pathlib.Path) -> None:
    setter = _RecordingSetter()
    svc = _make_service(
        state_dir=tmp_path / "state", workspace_root=tmp_path, permission_setter=setter
    )
    setter.dir_calls.clear()  # discard the construction-time state-dir call

    db_file = tmp_path / "telemetry.db"
    svc._restrict_owner_only(db_file, is_dir=False)

    assert setter.file_calls == [(db_file, 0o600)]
    assert setter.dir_calls == []


def test_db_file_path_posix_absent_skips_chmod(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    svc = _make_service(
        state_dir=tmp_path / "state", workspace_root=tmp_path, permission_setter=None
    )
    monkeypatch.setattr(service_mod, "PLATFORM", Capabilities.detect("win32"))
    chmod_calls: list[tuple[Any, int]] = []
    monkeypatch.setattr(os, "chmod", lambda p, m: chmod_calls.append((p, m)))

    svc._restrict_owner_only(tmp_path / "telemetry.db", is_dir=False)

    assert chmod_calls == []
