"""T-26-07 — ``dadaia lifecycle backlog define`` drives the REAL workflow.

Acceptance §3.7.6:
- ``--harness fake`` drives :class:`BacklogDefinitionWorkflow` (not the ``_deferred`` stub);
- ``--harness claude`` is rejected (LAW 1);
- a bad ``--model`` is rejected (LAW 2).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_BOX_CHARS = "│╭╮╰╯─"


def _clean(output: str) -> str:
    """Normalize Typer/Rich error output for substring checks.

    Typer renders ``BadParameter`` messages in a Rich error box: ANSI colour codes,
    box-drawing borders, and line-wrapping at the (environment-dependent) terminal
    width. A human message like ``takes no --model`` can therefore be split across a
    wrap + box border in CI while staying on one line locally. Strip ANSI + box glyphs
    and collapse whitespace so the assertion is width-independent.
    """
    text = _ANSI_RE.sub("", output)
    text = "".join(" " if ch in _BOX_CHARS else ch for ch in text)
    return re.sub(r"\s+", " ", text)


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
    cleaned = _clean(result.output)
    assert "Layer-2 workflow harness" in cleaned or "LAW 1" in cleaned


def test_raw_step_model_rejected_d3(workspace: Path) -> None:
    """v0.1.56 FR1 (rewritten from the inverted LAW-2 raw-model rejection):

    a raw ``--step-model label=<id>:<effort>`` is rejected as a D-3 profile-id violation —
    profile ids only, resolved through the shared resolver.
    """
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
            "--step-model",
            "intake_grill=gpt-5.5:high",
        ],
    )
    assert result.exit_code != 0
    assert "profile id" in _clean(result.output)


def test_model_flag_is_nonfatal_deprecation_warning(workspace: Path) -> None:
    """v0.1.56 FR1 ruling (rewritten from the inverted LAW-2 no-model rejection):

    ``--model`` is a NON-FATAL deprecation warning — the verb emits a stderr line naming
    ``--step-model`` and proceeds under the resolved policy (``--harness fake`` completes).
    Click 8.3 keeps stderr separate from stdout by default, so ``result.stderr`` isolates the
    warning while ``result.stdout`` stays parseable JSON (R-QA-1).
    """
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
            "--json",
        ],
    )
    assert result.exit_code == 0, result.stderr
    assert "--model is deprecated" in result.stderr
    assert "--step-model" in result.stderr
    # R-QA-1: the warning stays OUT of stdout so the --json payload stays parseable.
    payload = json.loads(result.stdout)
    assert payload["completed"] is True
