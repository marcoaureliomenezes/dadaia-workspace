"""Integration tests for guarded lifecycle skeleton commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _payload(output: str) -> dict[str, object]:
    payload = json.loads(output)
    assert isinstance(payload, dict)
    return payload


@pytest.mark.parametrize(
    ("command", "workflow"),
    (
        (["lifecycle", "backlog", "define"], "backlog definition"),
        (["lifecycle", "release", "define"], "release definition"),
        (["lifecycle", "implement"], "implementation"),
        (["lifecycle", "close"], "release closure"),
        # NOTE: review qa|security|code are no longer skeletons — they run the real
        # phase workflow (see tests/integration/test_lifecycle_review_cli.py).
    ),
)
def test_guarded_skeleton_commands_return_typed_blocked_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
    workflow: str,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, [*command, "--json"])

    assert result.exit_code == 3
    payload = _payload(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["message"] == f"{workflow} workflow is not implemented yet"
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)
    assert blocked["blocked_at_step"] == workflow
    assert blocked["resume_token"] == f"unavailable:{workflow}"


def test_resume_existing_run_returns_ok_next_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    JsonLifecycleRunStore(workspace).save(
        LifecycleRun(
            run_id="run-ok",
            context="dadaia-workspace",
            release_id="v0.1.15",
            command="implement",
            phase=LifecyclePhase.IMPLEMENTATION,
            status=LifecycleRunStatus.BLOCKED,
            current_step="preflight",
            expected_artifacts=(),
            idempotency_key="idem-run-ok",
        )
    )
    monkeypatch.chdir(workspace)

    result = _runner.invoke(app, ["lifecycle", "resume", "run-ok"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "OK resumed run-ok"
