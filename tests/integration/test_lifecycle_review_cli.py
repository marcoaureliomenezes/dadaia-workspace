"""Integration proof: `dadaia lifecycle review qa` actually drives the engine.

Before WS-1 the verb returned `unavailable_workflow`. Now it builds the selected
harness via the runtime factory, runs the real gate, and persists a run record. With
the default FAKE harness (no APPROVED verdict) the real gate BLOCKS — which proves the
engine path executed end-to-end rather than the old stub.
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


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def test_review_qa_runs_engine_and_blocks_on_missing_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "review",
            "qa",
            "--release-id",
            "multiharness-engine-v0116",
            "--run-id",
            "review-qa-it",
            "--harness",
            "fake",
            "--json",
        ],
    )

    # Real gate blocks (exit 3) — not the old "unavailable_workflow".
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["runtime"] == "fake"
    assert payload["accepted"] is False
    assert "APPROVED verdict" in payload["blocked"]["reason"]
