"""dadaia orchestrate CLI — happy path + error paths via Typer test runner."""

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


def _set_primary(workspace: Path, name: str = "test-ctx") -> None:
    states = workspace / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "primary_context.json").write_text(
        json.dumps({"name": name, "repo_slug": name, "specs_dir": str(workspace / "specs")})
    )


def test_orchestrate_list_returns_seed_workflows(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "list"])
    assert result.exit_code == 0, result.output
    assert "spec-refinement" in result.output
    assert "hotfix-release" in result.output


def test_orchestrate_run_rejects_without_context(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    result = _runner.invoke(
        app,
        ["orchestrate", "run", "spec-refinement", "--runtime", "cli"],
    )
    assert result.exit_code != 0


def test_orchestrate_run_happy_path(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _set_primary(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(
        app,
        [
            "orchestrate",
            "run",
            "spec-refinement",
            "--runtime",
            "cli",
            "--input",
            "context=test-ctx",
            "--input",
            "topic=demo",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "started" in result.output
    runs_dir = tmp_path / ".dadaia" / "runs"
    assert runs_dir.exists()
    assert any(runs_dir.iterdir())


def test_orchestrate_dry_run_does_not_create_state(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _set_primary(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(
        app,
        [
            "orchestrate",
            "run",
            "spec-refinement",
            "--runtime",
            "cli",
            "--input",
            "context=test-ctx",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "dry-run" in result.output
    assert not (tmp_path / ".dadaia" / "runs").exists()


def test_input_kv_parsing_error(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _set_primary(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(
        app,
        [
            "orchestrate",
            "run",
            "spec-refinement",
            "--runtime",
            "cli",
            "--input",
            "no-equals-sign",
        ],
    )
    assert result.exit_code != 0


def test_orchestrate_show_json_output(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "show", "spec-refinement", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["name"] == "spec-refinement"
    assert "stages" in data
    assert "inputs" in data


def test_orchestrate_list_on_uninitialized_workspace_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "list"])
    assert result.exit_code != 0


def test_orchestrate_status_all_json_output(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    _set_primary(tmp_path)
    monkeypatch.chdir(tmp_path)
    # Start a run first
    _runner.invoke(
        app,
        [
            "orchestrate",
            "run",
            "spec-refinement",
            "--runtime",
            "cli",
            "--input",
            "context=test-ctx",
            "--input",
            "topic=demo",
        ],
    )
    result = _runner.invoke(app, ["orchestrate", "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "run_id" in data[0]


def test_orchestrate_status_no_runs_json(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "status", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data == []
