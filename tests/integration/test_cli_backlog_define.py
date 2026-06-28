"""T-26-07 — ``dadaia lifecycle backlog define`` drives the REAL workflow.

Acceptance §3.7.6:
- ``--harness fake`` drives :class:`BacklogDefinitionWorkflow` (not the ``_deferred`` stub);
- ``--harness claude`` is rejected (LAW 1);
- a bad ``--model`` is rejected (LAW 2).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dadaia_workspace.container as container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.harness_models import HarnessModelOption
from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
)
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


@dataclass
class _KindReportingFake:
    kind: AgentRuntimeKind

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:  # noqa: ARG002
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="fake backlog-definition worker: APPROVED",
            artifact_refs=(
                ".dadaia/handoff/dadaia-workspace/backlog-definition-step.handoff.json",
            ),
            structured_output={"verdict": "APPROVED", "proposed_intents": "[]"},
        )


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(
        json.dumps({"version": "1", "contexts": []}), encoding="utf-8"
    )
    (tmp_path / "repos").mkdir(exist_ok=True)
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


def test_codex_harness_resolves_real_workflow_without_spawning_codex(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real CLI path can select Codex + a discrete model for backlog-definition.

    The runtime factory is replaced after the CLI has resolved LAW-1/LAW-2 inputs and while
    the real workflow still runs. That keeps the proof hermetic: no live Codex process or
    credits, but the command, model resolution, step sequence, and Python gates are real.
    """
    captured_models: dict[AgentRuntimeKind, HarnessModelOption] = {}
    seen_kinds: list[AgentRuntimeKind] = []

    def fake_factory(
        *,
        context: str,  # noqa: ARG001
        run_cwd: Path,  # noqa: ARG001
        model_by_kind: dict[AgentRuntimeKind, HarnessModelOption],
    ) -> object:
        captured_models.update(model_by_kind)

        def factory(kind: AgentRuntimeKind) -> _KindReportingFake:
            seen_kinds.append(kind)
            return _KindReportingFake(kind)

        return factory

    monkeypatch.setattr(container, "_backlog_definition_runtime_factory", fake_factory)

    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog",
            "define",
            "--release-id",
            "v0.1.33",
            "--harness",
            "codex",
            "--model",
            "gpt-5.5:high",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "OK"
    assert payload["completed"] is True

    model = captured_models[AgentRuntimeKind.CODEX_EXEC]
    assert model.model_id == "gpt-5.5"
    assert model.effort == "high"
    assert AgentRuntimeKind.CODEX_EXEC in seen_kinds

    steps = {step["label"]: step for step in payload["steps"]}
    assert steps["intake_grill"]["runtime"] == AgentRuntimeKind.CODEX_EXEC.value
    assert steps["backlog_author"]["runtime"] == AgentRuntimeKind.CODEX_EXEC.value
    assert steps["intake_grill"]["accepted"] is True
    assert steps["backlog_author"]["accepted"] is True


def test_claude_harness_rejected_law1(workspace: Path) -> None:
    result = _runner.invoke(
        app,
        ["lifecycle", "backlog", "define", "--release-id", "v0.1.26", "--harness", "claude"],
    )
    assert result.exit_code != 0
    cleaned = _clean(result.output)
    assert "Layer-2 workflow harness" in cleaned or "LAW 1" in cleaned


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
    assert "no --model" in _clean(result.output)
