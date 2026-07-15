"""Transactional post-install reconciliation service contracts."""

from __future__ import annotations

import json
from pathlib import Path

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

    def doctor(self, workspace_root: Path) -> list[str]:
        return ["[ok] projections"]


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
        "public-stage",
        "public-install",
        "public-doctor",
        "workspace-doctor",
        "capability-canary",
    )
