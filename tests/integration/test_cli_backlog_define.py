"""T-26-07 — ``dadaia lifecycle backlog define`` drives the REAL workflow.

Acceptance §3.7.6: ``--harness fake`` drives :class:`BacklogDefinitionWorkflow` (not the
``_deferred`` stub). The LAW1/D-3/--model rejection dupes are deleted — owned by the
policy matrix (``test_lifecycle_policy_cli.py``) and the AC-9 matrix
(``test_model_flag_removed_ac9.py``).

Bug fake-backlog-definition-cannot-complete-user-flow: the driving fake now materializes
a REAL synthetic backlog item (valid ``intents[]`` binding a live cli anchor), so the
documented ``--harness fake`` path walks the WHOLE sequence to completion — the
post-authoring review gate validates a real on-disk item instead of always blocking.
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


def test_fake_harness_drives_the_real_workflow_to_completion(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--release-id",
            "v0.1.26",
            "--run-id",
            "it-backlog-1",
            "--harness",
            "fake",
            "--json",
        ],
    )
    # The author-first sequence runs for real: the driving fake authors a REAL synthetic
    # backlog item, the REAL post-authoring review gate validates it on disk (subject
    # binding + overlap classification), and the run COMPLETES. Exit 0, never a crash.
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "OK", payload
    assert payload["completed"] is True
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
    # The synthetic item is REAL disk state the gate validated.
    items = list((workspace / "specs" / "backlog").glob("*.md"))
    assert items, "driving fake must materialize a backlog item under specs/backlog/"


def test_fake_harness_rerun_edits_the_canary_item_and_completes(workspace: Path) -> None:
    """A second fake run must not block on 'no new/changed item' — it EDITs the canary."""
    for run_id in ("it-backlog-a", "it-backlog-b"):
        result = _runner.invoke(
            app,
            [
                "lifecycle",
                "backlog-definition",
                "--release-id",
                "v0.1.26",
                "--run-id",
                run_id,
                "--harness",
                "fake",
                "--json",
            ],
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["completed"] is True
    # Idempotent slug: re-runs edit ONE canary item, never accumulate near-duplicates
    # (which would trip the overlap classifier on the third run).
    items = list((workspace / "specs" / "backlog").glob("*.md"))
    assert len(items) == 1, sorted(p.name for p in items)
