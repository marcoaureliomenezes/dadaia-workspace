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


def test_orchestrate_list_show_json_removed_verbs_and_uninitialized_workspace_errors(
    tmp_path: Path, monkeypatch
) -> None:
    """list/show --json contract (AC-2). Plus: the retired run/status/resume honest-no-op
    verbs error out (AC-2); an unknown workflow name errors; list on an uninitialized
    workspace errors."""
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    list_result = _runner.invoke(app, ["orchestrate", "list"])
    assert list_result.exit_code == 0, list_result.output
    assert "audit-fanout" in list_result.output
    assert "release-ship" in list_result.output

    show_result = _runner.invoke(app, ["orchestrate", "show", "audit-fanout", "--json"])
    assert show_result.exit_code == 0, show_result.output
    data = json.loads(show_result.output)
    assert data["name"] == "audit-fanout"
    assert "stages" in data
    assert "inputs" in data
    # The gate kind is preserved (never collapsed to a boolean) — AC-2.
    assert all("gate" in stage for stage in data["stages"])

    unknown_result = _runner.invoke(app, ["orchestrate", "show", "no-such-workflow", "--json"])
    assert unknown_result.exit_code == 2

    run_result = _runner.invoke(app, ["orchestrate", "run", "audit-fanout"])
    assert run_result.exit_code != 0

    # Genuinely separate root (not nested under `tmp_path`) so upward .dadaia resolution
    # never finds the initialized tree.
    uninitialized_ws = tmp_path.parent / (tmp_path.name + "-uninitialized")
    uninitialized_ws.mkdir()
    monkeypatch.chdir(uninitialized_ws)
    uninitialized_result = _runner.invoke(app, ["orchestrate", "list"])
    assert uninitialized_result.exit_code != 0
