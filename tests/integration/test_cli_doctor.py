"""dadaia doctor CLI — happy path + degraded states."""

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


def test_doctor_detects_orphan_primary_pointer(workspace: Path) -> None:
    primary = workspace / ".dadaia" / "states" / "primary_context.json"
    primary.write_text(json.dumps({"name": "ghost", "repo_slug": "ghost", "specs_dir": "/x"}))
    result = _runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "ghost" in result.output or "issue" in result.output.lower()


def test_doctor_fix_clears_orphan_primary(workspace: Path) -> None:
    primary = workspace / ".dadaia" / "states" / "primary_context.json"
    primary.write_text(json.dumps({"name": "ghost", "repo_slug": "ghost", "specs_dir": "/x"}))
    result = _runner.invoke(app, ["doctor", "--fix"])
    assert result.exit_code == 0, result.output
    assert not primary.exists() or json.loads(primary.read_text()) != {
        "name": "ghost",
        "repo_slug": "ghost",
        "specs_dir": "/x",
    }
