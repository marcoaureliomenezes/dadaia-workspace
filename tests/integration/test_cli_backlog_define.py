"""T-26-07 — ``dadaia lifecycle backlog define`` drives the REAL workflow.

Acceptance §3.7.6: ``--harness fake`` drives :class:`BacklogDefinitionWorkflow` (not the
``_deferred`` stub). The LAW1/D-3/--model rejection dupes are deleted — owned by the
policy matrix (``test_lifecycle_policy_cli.py``) and the AC-9 matrix
(``test_model_flag_removed_ac9.py``).
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
    monkeypatch.setenv("DADAIA_CONTEXT", "dadaia-workspace")  # explicit rung
    return tmp_path


def test_fake_harness_drives_the_real_workflow(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--release-id",
            "v0.1.26",
            "--harness",
            "fake",
            "--json",
        ],
    )
    # The author-first sequence runs for real: the fake worker writes NO backlog item,
    # so the REAL post-authoring review gate honestly blocks (proof the gate validates
    # disk state, not a threaded demand). Exit code 3 = BLOCKED, never a crash.
    assert result.exit_code == 3, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "BLOCKED"
    assert payload["completed"] is False
    labels = [step["label"] for step in payload["steps"]]
    assert labels == [
        "intake_grill",
        "backlog_author",
        "backlog_review_gate",
    ]
    # The grill is opt-in and skipped by default — zero model calls spent on it.
    intake = next(s for s in payload["steps"] if s["label"] == "intake_grill")
    assert intake["skipped"] is True
    author = next(s for s in payload["steps"] if s["label"] == "backlog_author")
    assert author["fragment_id"] == "backlog_definition.backlog_authoring"
    assert payload["blocked"]["blocked_at_step"] == "backlog_review_gate"
    assert "no new/changed item" in payload["blocked"]["reason"]
