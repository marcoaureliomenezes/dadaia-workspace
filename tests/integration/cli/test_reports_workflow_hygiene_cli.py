"""Executed CLI coverage for lifecycle hygiene as a reports utility."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager


def test_reports_hygiene_status_and_clean_are_live_remediation_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    old = tmp_path / ".dadaia" / "tmp" / "expired.txt"
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_text("expired", encoding="utf-8")
    stale = time.time() - (3 * 24 * 60 * 60)
    os.utime(old, (stale, stale))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    status = runner.invoke(app, ["reports", "workflow-hygiene-status", "--json"])
    assert status.exit_code == 0, status.output
    assert json.loads(status.stdout)["cleanup_candidate_count"] >= 1

    workflow_status = runner.invoke(app, ["reports", "workflow-status", "--json"])
    assert workflow_status.exit_code == 0, workflow_status.output
    assert json.loads(workflow_status.stdout)["status"] == "OK"

    dry_run = runner.invoke(app, ["reports", "workflow-hygiene-clean", "--dry-run", "--json"])
    assert dry_run.exit_code == 0, dry_run.output
    assert json.loads(dry_run.stdout)["candidate_count"] >= 1
    assert old.is_file()

    applied = runner.invoke(app, ["reports", "workflow-hygiene-clean", "--apply", "--json"])
    assert applied.exit_code == 0, applied.output
    assert json.loads(applied.stdout)["deleted_count"] >= 1
    assert not old.exists()


def test_reports_workflow_profiles_lists_and_filters_governed_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(app, ["reports", "workflow-profiles", "--harness", "pi", "--json"])

    assert result.exit_code == 0, result.output
    profiles = json.loads(result.stdout)["profiles"]
    assert profiles
    assert {profile["harness"] for profile in profiles} == {"pi"}
    ids = {profile["id"] for profile in profiles}
    assert "pi-openrouter-gpt-high" not in ids
    assert "pi-openrouter-gpt-oss-free-low" not in ids
    assert "pi-implementation-standard" in ids
