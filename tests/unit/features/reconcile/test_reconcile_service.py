"""Transactional post-install reconciliation service contracts."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.doctor_report import (
    DoctorLine,
    DoctorReport,
    DoctorStatus,
)
from dadaia_workspace.features.reconcile import reconcile_workspace


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
    (states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "1", "contexts": []}), encoding="utf-8"
    )
    return root


def test_version_mismatch_is_read_only(tmp_path: Path) -> None:
    workspace = _v1_workspace(tmp_path)
    before = (workspace / ".dadaia" / "states" / "spec_contexts.json").read_bytes()
    result = reconcile_workspace(
        workspace,
        expected_version="9.9.9",
        actual_version="1.0.0",
        public_service=_Public(),
        doctor_service=_Doctor(),
    )
    assert result.ok is False
    assert result.rollback_required is False
    assert (workspace / ".dadaia" / "states" / "spec_contexts.json").read_bytes() == before


def test_failure_restores_migrated_state_and_requires_projection_rollback(tmp_path: Path) -> None:
    workspace = _v1_workspace(tmp_path)
    state_path = workspace / ".dadaia" / "states" / "spec_contexts.json"
    before = state_path.read_bytes()
    result = reconcile_workspace(
        workspace,
        expected_version="1.2.3",
        actual_version="1.2.3",
        public_service=_Public(fail_install=True),
        doctor_service=_Doctor(),
    )
    assert result.ok is False
    assert result.rollback_required is True
    assert "injected install failure" in (result.error or "")
    assert state_path.read_bytes() == before


def test_reconcile_quarantines_legacy_dadaia_dirs(tmp_path: Path, monkeypatch) -> None:
    """Bug ``reconcile-legacy-dadaia-dirs-unmigrated`` (consumer validation, 2026-07-15).

    A long-lived consumer workspace carries legacy ``.dadaia/bugs`` and ``.dadaia/src``
    (created by pre-0.2.x portability flows). Reconcile must QUARANTINE them (move under
    ``.dadaia/tmp/legacy-quarantine/`` — never delete) instead of failing the
    workspace-doctor step with ROOT-4, so a healthy upgraded workspace reconciles clean.
    Uses the REAL DoctorService so the executed path is the one that failed in the field.
    """
    from dadaia_workspace.features.spec_context.doctor import DoctorService
    from tests.fakes import FakeContextStore, FakeGitClient

    workspace = _v1_workspace(tmp_path)
    (workspace / "repos").mkdir()
    (workspace / "AGENTS.md").write_text("# agents", encoding="utf-8")
    from dadaia_workspace.core.platform import PLATFORM

    # VENV-1 skeleton — platform-correct layout ("bin" on POSIX, "Scripts" on Windows)
    venv_bin = workspace / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir
    venv_bin.mkdir(parents=True)
    entry = venv_bin / f"dadaia{PLATFORM.venv_exe_suffix}"
    entry.write_text("#!/bin/sh\n", encoding="utf-8")
    entry.chmod(0o755)
    (workspace / ".dadaia" / "bugs").mkdir()
    (workspace / ".dadaia" / "bugs" / "legacy-report.md").write_text("x", encoding="utf-8")
    (workspace / ".dadaia" / "src").mkdir()
    (workspace / ".dadaia" / "src" / "legacy.py").write_text("y", encoding="utf-8")
    monkeypatch.setattr(
        "dadaia_workspace.features.reconcile.service.build_capabilities",
        lambda: {
            "schema_version": "dadaia-capabilities-v1",
            "provider": {"distribution_version": "1.2.3"},
        },
    )
    doctor = DoctorService(FakeContextStore(), FakeGitClient(), workspace)
    result = reconcile_workspace(
        workspace,
        expected_version="1.2.3",
        actual_version="1.2.3",
        public_service=_Public(),
        doctor_service=doctor,
    )
    assert result.ok is True, f"reconcile must pass on legacy dirs, got error: {result.error}"
    assert "legacy-dir-quarantine" in result.steps
    assert not (workspace / ".dadaia" / "bugs").exists()
    assert not (workspace / ".dadaia" / "src").exists()
    preserved = list(
        (workspace / ".dadaia" / "tmp" / "legacy-quarantine").glob("*/bugs/legacy-report.md")
    )
    assert preserved, "legacy content must be preserved under quarantine, never deleted"


def test_success_runs_all_postconditions(tmp_path: Path, monkeypatch) -> None:
    workspace = _v1_workspace(tmp_path)
    monkeypatch.setattr(
        "dadaia_workspace.features.reconcile.service.build_capabilities",
        lambda: {
            "schema_version": "dadaia-capabilities-v1",
            "provider": {"distribution_version": "1.2.3"},
        },
    )
    result = reconcile_workspace(
        workspace,
        expected_version="1.2.3",
        actual_version="1.2.3",
        public_service=_Public(),
        doctor_service=_Doctor(),
    )
    assert result.ok is True
    assert result.steps == (
        "provider-version",
        "state-schema-v2",
        "legacy-dir-quarantine",
        "public-stage",
        "public-install",
        "public-doctor",
        "workspace-doctor",
        "capability-canary",
    )
