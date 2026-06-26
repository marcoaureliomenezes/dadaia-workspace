"""T-26-07 — ``dadaia lifecycle backlog define`` drives the REAL workflow.

Acceptance §3.7.6:
- ``--harness fake`` drives :class:`BacklogDefinitionWorkflow` (not the ``_deferred`` stub);
- ``--harness claude`` is rejected (LAW 1);
- a bad ``--model`` is rejected (LAW 2).
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


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_fake_harness_drives_the_real_workflow(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog",
            "define",
            "--release-id",
            "v0.1.26",
            "--harness",
            "fake",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "OK"
    assert payload["completed"] is True
    assert payload["final_phase"] == "release_definition"
    labels = [step["label"] for step in payload["steps"]]
    # The §4 seven-step sequence runs in order — proof it is the real workflow, not _deferred.
    assert labels == [
        "intake_grill",
        "subject_bind",
        "existing_backlog_review",
        "reconcile_decision",
        "conflict_resolution_grill",
        "backlog_author",
        "backlog_review_gate",
    ]
    # Model steps carry their fragment id (no generic "Run the step" stub).
    intake = next(s for s in payload["steps"] if s["label"] == "intake_grill")
    assert intake["fragment_id"] == "backlog_definition.intake_grill"
    # The conditional grill is skipped on a clean demand.
    grill = next(s for s in payload["steps"] if s["label"] == "conflict_resolution_grill")
    assert grill["skipped"] is True


def test_claude_harness_rejected_law1(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        ["lifecycle", "backlog", "define", "--release-id", "v0.1.26", "--harness", "claude"],
    )
    assert result.exit_code != 0
    assert "Layer-2 workflow harness" in result.output or "LAW 1" in result.output


def test_bad_model_rejected_law2(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog",
            "define",
            "--release-id",
            "v0.1.26",
            "--harness",
            "codex",
            "--model",
            "not-a-real-model:nonsense",
        ],
    )
    assert result.exit_code != 0


def test_fake_harness_takes_no_model_law2(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog",
            "define",
            "--release-id",
            "v0.1.26",
            "--harness",
            "fake",
            "--model",
            "anything:high",
        ],
    )
    assert result.exit_code != 0
    assert "no --model" in result.output
