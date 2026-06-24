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
    "command",
    (
        ["lifecycle", "backlog", "define"],
        ["lifecycle", "release", "define"],
        ["lifecycle", "implement"],
        ["lifecycle", "close"],
        ["lifecycle", "review", "qa"],
        ["lifecycle", "review", "security"],
        ["lifecycle", "review", "code"],
    ),
)
def test_every_phase_verb_runs_the_engine_and_blocks_on_fake_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: list[str],
) -> None:
    """Every single-step lifecycle verb now drives the engine (no `unavailable_workflow`).

    With the FAKE harness the worker emits no APPROVED verdict, so the real typed gate
    blocks — proving the engine path executed end-to-end on a selectable harness.
    """
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [*command, "--release-id", "multiharness-engine-v0116", "--harness", "fake", "--json"],
    )

    assert result.exit_code == 3, result.output
    payload = _payload(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["runtime"] == "fake"
    assert payload["accepted"] is False
    blocked = payload["blocked"]
    assert isinstance(blocked, dict)
    assert "APPROVED verdict" in blocked["reason"]


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
