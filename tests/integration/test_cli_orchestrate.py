"""dadaia orchestrate CLI — read-only surface + honest no-op run/resume via Typer runner.

Workflow execution moved to the lifecycle engine (WS-3); ``orchestrate run``/``resume``
no longer dispatch and create no run state — they print the "moved to lifecycle" notice
and exit 0 so the panel workflow launcher (which spawns
``python -m dadaia_workspace orchestrate <workflow>``) terminates cleanly.
"""

import json
from pathlib import Path

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(workspace)
    FileSystemPublicAssetManager().stage(workspace)


def test_orchestrate_list_returns_seed_workflows(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "list"])
    assert result.exit_code == 0, result.output
    assert "audit-fanout" in result.output
    assert "release-ship" in result.output


def test_orchestrate_run_is_honest_noop_and_exits_clean(tmp_path: Path, monkeypatch) -> None:
    """`orchestrate run` dispatches nothing, emits the moved-to-lifecycle notice, exits 0.

    No context is needed and no run state is created — this guarantees the panel
    workflow launcher (which spawns `orchestrate <workflow>`) always exits cleanly.
    """
    _init_workspace(tmp_path)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "run", "audit-fanout"])
    assert result.exit_code == 0, result.output
    assert "lifecycle" in result.output
    assert "started" not in result.output
    assert not (tmp_path / ".dadaia" / "runs").exists()


def test_orchestrate_run_unknown_workflow_errors(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "run", "no-such-workflow"])
    assert result.exit_code != 0


def test_orchestrate_resume_is_honest_noop_and_exits_clean(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "resume", "any-run-id"])
    assert result.exit_code == 0, result.output
    assert "lifecycle" in result.output


def test_orchestrate_dry_run_validates_only(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "run", "audit-fanout", "--dry-run"])
    assert result.exit_code == 0
    assert "dry-run" in result.output
    assert not (tmp_path / ".dadaia" / "runs").exists()


def test_orchestrate_show_json_output(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "show", "audit-fanout", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["name"] == "audit-fanout"
    assert "stages" in data
    assert "inputs" in data


def test_orchestrate_list_on_uninitialized_workspace_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "list"])
    assert result.exit_code != 0


def test_orchestrate_status_no_runs_json(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data == []
