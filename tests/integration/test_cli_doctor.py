"""dadaia doctor CLI — happy path + degraded states (v2 model: ALIVE/DEAD)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_doctor_runs_on_clean_workspace(workspace: Path) -> None:
    result = _runner.invoke(app, ["doctor"])
    assert result.exit_code in (0, 1)  # ok or some invariant flag, but not crash


def test_doctor_detects_dead_context_with_stale_repo(workspace: Path) -> None:
    """Dead context should not have a repo dir (INV-5)."""
    states = workspace / ".dadaia" / "states"
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": "stale-ctx",
                "state": "dead",
                "repo_slug": "stale-ctx",
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": None,
                "dead_since": "2026-05-01T00:00:00Z",
                "current_branch": None,
            }
        ],
    }
    (states / "spec_contexts.json").write_text(json.dumps(ctx_data))
    # Create the stale repo dir
    (workspace / "repos" / "stale-ctx").mkdir(parents=True)
    result = _runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "stale-ctx" in result.output or "INV-5" in result.output


def test_doctor_fix_removes_stale_repo_for_dead_context(workspace: Path) -> None:
    """Fix should remove the stale repo dir for a DEAD context."""
    states = workspace / ".dadaia" / "states"
    ctx_data = {
        "schema_version": "2",
        "contexts": [
            {
                "name": "stale-ctx",
                "state": "dead",
                "repo_slug": "stale-ctx",
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": None,
                "dead_since": "2026-05-01T00:00:00Z",
                "current_branch": None,
            }
        ],
    }
    (states / "spec_contexts.json").write_text(json.dumps(ctx_data))
    stale_repo = workspace / "repos" / "stale-ctx"
    stale_repo.mkdir(parents=True)
    result = _runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0, result.output
    assert not stale_repo.exists()
