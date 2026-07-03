"""dadaia orchestrate CLI — read-only ``list``/``show`` surface via the Typer runner.

Workflow execution lives in the lifecycle engine (``dadaia lifecycle``). In v0.1.53 the
retired ``features/orchestration`` package (whose ``run``/``status``/``resume`` verbs were
honest no-ops) was deleted; ``list``/``show`` are rewired onto a ``features/workflows``
accessor over the shared ``MarkdownWorkflowStore`` that preserves ``stage.gate.kind`` and
every ``WorkflowInput`` field, so the ``--json`` contract is byte-identical (AC-2).
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


def test_orchestrate_show_json_output(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "show", "audit-fanout", "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["name"] == "audit-fanout"
    assert "stages" in data
    assert "inputs" in data
    # The gate kind is preserved (never collapsed to a boolean) — AC-2.
    assert all("gate" in stage for stage in data["stages"])


def test_orchestrate_show_unknown_workflow_errors(tmp_path: Path, monkeypatch) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "show", "no-such-workflow", "--json"])
    assert result.exit_code == 2


def test_orchestrate_list_on_uninitialized_workspace_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "list"])
    assert result.exit_code != 0


def test_orchestrate_run_status_resume_removed_from_help(tmp_path: Path, monkeypatch) -> None:
    """The retired honest-no-op verbs are gone from the CLI surface (AC-2)."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "--help"])
    assert result.exit_code == 0, result.output
    assert "list" in result.output
    assert "show" in result.output
    assert "run" not in result.output
    assert "status" not in result.output
    assert "resume" not in result.output


def test_orchestrate_run_verb_is_gone(tmp_path: Path, monkeypatch) -> None:
    """Invoking the removed ``run`` verb fails (no such command)."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = _runner.invoke(app, ["orchestrate", "run", "audit-fanout"])
    assert result.exit_code != 0
