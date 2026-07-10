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


def test_doctor_detects_and_fixes_dead_context_stale_repo_clean_run_non_crash(
    workspace: Path,
) -> None:
    """INV-5: a DEAD context's stale repo dir is detected (non-crashing clean run
    folded in), then --fix removes it."""
    result = _runner.invoke(app, ["doctor"])
    assert result.exit_code in (0, 1)  # ok or some invariant flag, but not crash

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

    detect_result = _runner.invoke(app, ["doctor"])
    assert detect_result.exit_code == 0, detect_result.output
    assert "stale-ctx" in detect_result.output or "INV-5" in detect_result.output

    fix_result = _runner.invoke(app, ["doctor", "--fix"])
    assert fix_result.exit_code == 0, fix_result.output
    assert not stale_repo.exists()
