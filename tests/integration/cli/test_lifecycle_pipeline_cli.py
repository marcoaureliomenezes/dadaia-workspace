"""Integration proof: `dadaia lifecycle pipeline` runs the multi-step engine end-to-end."""

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


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def test_pipeline_runs_engine_and_blocks_at_first_step_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "pipeline",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "pipe-it",
            "--harness",
            "fake",
            "--step-harness",
            "review_qa=codex",
            "--json",
        ],
    )

    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    # First step ran the engine on the fake harness and blocked on the missing verdict.
    assert payload["steps"][0]["label"] == "implement"
    assert payload["steps"][0]["runtime"] == "fake"
    assert payload["steps"][0]["accepted"] is False
    # The per-step override was accepted by the CLI (parsing path exercised).
    assert payload["blocked"]["reason"]
