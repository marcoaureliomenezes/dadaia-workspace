"""Transactional post-install reconciliation service contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core import platform
from dadaia_workspace.core.cli_line import cli_words
from dadaia_workspace.core.models.doctor_report import (
    DoctorLine,
    DoctorReport,
    DoctorStatus,
)
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.features.migrate.state_v2 import execute_migration, plan_migration
from dadaia_workspace.features.reconcile import ReconcileResult, reconcile_workspace
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.stores import context_store
from tests.helpers.oslib import effective_uid, make_executable, write_text


class _Doctor:
    def __init__(self, issues: list[object] | None = None) -> None:
        self._issues = issues or []

    def check(self) -> list[object]:
        return self._issues


class _Public:
    def __init__(self, *, fail_install: bool = False) -> None:
        self.fail_install = fail_install

    def stage(self, workspace_root: Path) -> list[str]:
        return ["staged"]

    def install(self, workspace_root: Path, **kwargs: object) -> list[str]:
        if self.fail_install:
            raise RuntimeError("injected install failure")
        return ["installed"]

    def doctor(self, workspace_root: Path) -> DoctorReport:
        return DoctorReport(lines=(DoctorLine(DoctorStatus.OK, "projections"),))


def _v1_workspace(root: Path) -> Path:
    states = root / ".dadaia" / "states"
    states.mkdir(parents=True)
    write_text(states / "spec_contexts.json", json.dumps({"schema_version": "1", "contexts": []}))
    return root


def _reconcile(
    workspace: Path,
    *,
    expected_version: str,
    public_service: object,
    doctor_service: object,
    actual_version: str | None = None,
) -> ReconcileResult:
    return reconcile_workspace(
        workspace,
        context_store=JsonContextStore(workspace / ".dadaia" / "states"),
        version=lambda: "1.2.3",
        migration_plan=plan_migration,
        migrate=execute_migration,
        expected_version=expected_version,
        public_service=public_service,
        doctor_service=doctor_service,
        actual_version=actual_version,
    )


def test_version_mismatch_is_read_only(tmp_path: Path) -> None:
    workspace = _v1_workspace(tmp_path)
    before = (workspace / ".dadaia" / "states" / "spec_contexts.json").read_bytes()
    result = _reconcile(
        workspace,
        expected_version="9.9.9",
        actual_version="1.0.0",
        public_service=_Public(),
        doctor_service=_Doctor(),
    )
    assert result.ok is False
    assert result.rollback_required is False
    assert result.fix.startswith(
        "Agent action: install the exact provider version 9.9.9, then run "
    )
    assert (workspace / ".dadaia" / "states" / "spec_contexts.json").read_bytes() == before


def test_failure_restores_migrated_state_and_requires_projection_rollback(tmp_path: Path) -> None:
    workspace = _v1_workspace(tmp_path)
    state_path = workspace / ".dadaia" / "states" / "spec_contexts.json"
    before = state_path.read_bytes()
    result = _reconcile(
        workspace,
        expected_version="1.2.3",
        actual_version="1.2.3",
        public_service=_Public(fail_install=True),
        doctor_service=_Doctor(),
    )
    assert result.ok is False
    assert result.rollback_required is True
    assert "injected install failure" in (result.error or "")
    assert result.fix == (
        "Agent action: reinstall the previous exact provider version, then run "
        + platform.inline(*cli_words(None, "public", "install"))
    )
    assert state_path.read_bytes() == before


def test_failure_restores_the_primary_context_file_the_migration_deleted(tmp_path: Path) -> None:
    workspace = _v1_workspace(tmp_path)
    primary = workspace / ".dadaia" / "states" / "primary_context.json"
    primary.write_bytes(b'{"name": "app"}')
    _reconcile(
        workspace,
        expected_version="1.2.3",
        actual_version="1.2.3",
        public_service=_Public(fail_install=True),
        doctor_service=_Doctor(),
    )
    assert primary.read_bytes() == b'{"name": "app"}'
    assert not (workspace / ".dadaia" / "tmp").exists()


def test_reconcile_ignores_operator_slop_and_names_context_invariants(tmp_path: Path) -> None:
    """With `.dadaia/nonsense/` and a root
    `notes.txt` seeded, reconcile succeeds (operator slop never blocks an upgrade) and its
    doctor step is reported as 'context-invariants' — run against the real doctor service."""
    workspace = _v1_workspace(tmp_path)
    venv_bin = workspace / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True)
    write_text(venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}", "")
    make_executable(venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}")
    (workspace / ".dadaia" / "nonsense").mkdir()
    write_text(workspace / "notes.txt", "operator notes")
    doctor = DoctorService(
        context_store(workspace / ".dadaia" / "states"), GitSubprocessClient(), workspace
    )

    result = _reconcile(
        workspace,
        expected_version="1.2.3",
        actual_version="1.2.3",
        public_service=_Public(),
        doctor_service=doctor,
    )

    assert result.ok is True, result.error
    assert result.steps == (
        "provider-version",
        "state-schema-v2",
        "public-stage",
        "public-install",
        "public-doctor",
        "context-invariants",
        "capability-canary",
    )


def test_the_ownership_repair_quotes_a_path_holding_a_blank(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    uid = effective_uid()
    if uid is None:
        pytest.skip("this host has no ownership semantics")
    root = tmp_path / "a b"
    (root / ".dadaia" / "agentic").mkdir(parents=True)
    monkeypatch.setattr(platform, "file_owner", lambda _path: (uid + 1, "other"))

    result = _reconcile(
        root,
        expected_version="1.2.3",
        actual_version="1.2.3",
        public_service=object(),
        doctor_service=object(),
    )

    repair = platform.inline("sudo", "chown", "-R", str(uid), str(root / ".dadaia"))
    assert "Repair with" not in (result.error or "")
    assert result.fix == f"Agent action: run {repair}"
    assert str(root / ".dadaia") in repair and f"'{root / '.dadaia'}'" in repair
