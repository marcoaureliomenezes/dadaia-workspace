"""Integration tests for ``dadaia migrate`` (state-file migration) CLI command.

Merged per plan-integration.md (6 -> 1): one fn on one v1 workspace: --dry-run
unchanged -> --yes -> v2 schema + required dirs created + primary_context.json gone ->
rerun noop. tree-v2-still-works-as-subcommand is dropped (covered by
test_cli_migrate.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _v1_data() -> dict:  # type: ignore[type-arg]
    return {
        "schema_version": "1",
        "contexts": [
            {
                "name": "my-ctx",
                "state": "ativo",
                "repo_slug": "my-ctx",
                "repo_url": "https://github.com/org/my-ctx",
                "is_primary": True,
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": "2026-05-01T00:00:00Z",
            }
        ],
    }


@pytest.fixture()
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture()
def v1_workspace(workspace: Path) -> Path:
    """Overwrite spec_contexts.json with v1 data."""
    states = workspace / ".dadaia" / "states"
    (states / "spec_contexts.json").write_text(json.dumps(_v1_data()))
    (states / "primary_context.json").write_text(
        json.dumps({"name": "my-ctx", "repo_slug": "my-ctx", "specs_dir": "/x"})
    )
    return workspace


def test_migrate_dry_run_unchanged_then_yes_v2_dirs_and_primary_gone_then_noop(
    v1_workspace: Path,
) -> None:
    states = v1_workspace / ".dadaia" / "states"
    primary = states / "primary_context.json"

    before = (states / "spec_contexts.json").read_text()
    dry_run_result = _runner.invoke(app, ["migrate", "--dry-run"])
    assert dry_run_result.exit_code == 0, dry_run_result.output
    after_dry_run = (states / "spec_contexts.json").read_text()
    assert before == after_dry_run
    assert (
        "ativo" in dry_run_result.output
        or "alive" in dry_run_result.output
        or "1" in dry_run_result.output
    )
    assert primary.exists()

    result = _runner.invoke(app, ["migrate", "--yes"])
    assert result.exit_code == 0, result.output

    data = json.loads((states / "spec_contexts.json").read_text())
    assert data["schema_version"] == "2"
    row = data["contexts"][0]
    assert row["state"] == "alive"
    assert "is_primary" not in row
    assert "activated_at" not in row

    # Only caller-scoped session storage is created. Lock directories are retired.
    assert (v1_workspace / ".dadaia" / "sessions").is_dir()
    assert not (v1_workspace / ".dadaia" / "locks").exists()
    assert not (v1_workspace / ".dadaia" / "states" / "ctx_locks").exists()

    # AC-T10c-5: primary_context.json must not exist after migration.
    assert not primary.exists()

    # AC-T10c-3: idempotent on the now-v2 workspace.
    rerun_result = _runner.invoke(app, ["migrate", "--yes"])
    assert rerun_result.exit_code == 0, rerun_result.output
    assert (
        "schema_version 2" in rerun_result.output
        or "nothing to do" in rerun_result.output.lower()
        or "already" in rerun_result.output.lower()
    )
