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


def test_state_dir_and_db_file_routing_matrix(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # (a) state-dir restriction routes through the injected setter.
    setter_a = _RecordingSetter()
    state_dir_a = tmp_path / "a" / "state"
    _make_service(state_dir=state_dir_a, workspace_root=tmp_path / "a", permission_setter=setter_a)
    assert setter_a.dir_calls == [(state_dir_a, 0o700)]
    assert setter_a.file_calls == []

    # (b) a PlatformSecurityError from the setter degrades with an INFO log, never raises.
    with caplog.at_level(logging.INFO, logger=service_mod.logger.name):
        _make_service(
            state_dir=tmp_path / "b" / "state",
            workspace_root=tmp_path / "b",
            permission_setter=_RaisingSetter(),
        )
    messages = [r.getMessage() for r in caplog.records]
    assert any("degraded mode" in m and "directory" in m for m in messages), messages

    # (c) no setter injected + POSIX present -> falls back to direct os.chmod.
    monkeypatch.setattr(service_mod, "PLATFORM", Capabilities.detect("linux"))
    chmod_calls_c: list[tuple[Any, int]] = []
    monkeypatch.setattr(os, "chmod", lambda p, m: chmod_calls_c.append((p, m)))
    state_dir_c = tmp_path / "c" / "state"
    _make_service(state_dir=state_dir_c, workspace_root=tmp_path / "c", permission_setter=None)
    assert chmod_calls_c == [(state_dir_c, 0o700)]

    # (d) no setter injected + POSIX absent (Windows-shaped) -> chmod SKIPPED (CWE-732).
    monkeypatch.setattr(service_mod, "PLATFORM", Capabilities.detect("win32"))
    chmod_calls_d: list[tuple[Any, int]] = []
    monkeypatch.setattr(os, "chmod", lambda p, m: chmod_calls_d.append((p, m)))
    _make_service(
        state_dir=tmp_path / "d" / "state", workspace_root=tmp_path / "d", permission_setter=None
    )
    assert chmod_calls_d == []

    # (e) db-file path routes file restriction through the setter (not dir restriction).
    setter_e = _RecordingSetter()
    svc_e = _make_service(
        state_dir=tmp_path / "e" / "state",
        workspace_root=tmp_path / "e",
        permission_setter=setter_e,
    )
    setter_e.dir_calls.clear()  # discard the construction-time state-dir call
    db_file_e = tmp_path / "e" / "telemetry.db"
    svc_e._restrict_owner_only(db_file_e, is_dir=False)  # noqa: SLF001
    assert setter_e.file_calls == [(db_file_e, 0o600)]
    assert setter_e.dir_calls == []

    # (f) db-file path with no setter + POSIX absent -> chmod skipped too.
    svc_f = _make_service(
        state_dir=tmp_path / "f" / "state", workspace_root=tmp_path / "f", permission_setter=None
    )
    monkeypatch.setattr(service_mod, "PLATFORM", Capabilities.detect("win32"))
    chmod_calls_f: list[tuple[Any, int]] = []
    monkeypatch.setattr(os, "chmod", lambda p, m: chmod_calls_f.append((p, m)))
    svc_f._restrict_owner_only(tmp_path / "f" / "telemetry.db", is_dir=False)  # noqa: SLF001
    assert chmod_calls_f == []
