"""End-to-end proofs of the lifecycle pipeline engine reaching terminal phases.

These complement ``test_lifecycle_pipeline_cli.py`` (which proves the run *blocks* at
the first gate on a no-op FAKE worker). Here we feed each gate a green/passing
verdict+handoff so the run actually *advances*:

* T-23-02 — the full implementation ladder (implement → qa → security → code) runs to
  completion and lands in terminal phase ``CLOSURE`` (the first e2e to get there).
* T-23-03 — a review step whose ``target_phase`` is ``IMPLEMENTATION`` drives the
  genuine transition-table backtrack (``qa_review -> implementation``) end-to-end, so
  the run lands back in ``IMPLEMENTATION`` after a rejecting/rework gate.

Both drive the *real* engine — ``container.build_lifecycle_pipeline`` →
``LifecyclePipeline`` → ``LifecycleAgentRunner`` → ``LifecycleStateMachine`` — and only
swap the FAKE adapter for one carrying an injected passing result. No production code is
patched; the FAKE runtime already accepts an injected ``result=`` (its documented test
seam). T-23-02 also exercises the CLI surface end-to-end via ``lifecycle pipeline``.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace import container
from dadaia_workspace.cli.main import app
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.lifecycle.pipeline import (
    PipelineStep,
    implementation_ladder,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

_runner = CliRunner()

_CONTEXT = "dadaia-workspace"


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _passing_result(label: str) -> AgentRunResult:
    """A green worker result the gate accepts: SUCCEEDED + APPROVED verdict + an
    in-scope handoff artifact_ref (under ``.dadaia/handoff/<context>/**``)."""
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary=f"fake runtime: {label} APPROVED",
        artifact_refs=(f".dadaia/handoff/{_CONTEXT}/{label}.handoff.json",),
        structured_output={"verdict": "APPROVED", "task_group": "rc-1"},
    )


def _inject_passing_fake(
    monkeypatch: pytest.MonkeyPatch,
    *,
    result_for: dict[str, AgentRunResult] | None = None,
    default: AgentRunResult | None = None,
) -> None:
    """Make the FAKE harness emit a passing result.

    Replaces ``container.build_agent_runtime`` so that ``AgentRuntimeKind.FAKE`` resolves
    to a ``FakeAgentRuntime`` carrying an injected passing ``result``. The result is
    chosen per call from ``result_for`` keyed on a monotonically advancing step index,
    falling back to ``default``. Every other harness kind is left to the real factory.
    """
    real_build = container.build_agent_runtime
    calls = {"n": 0}
    per_step = result_for or {}

    def fake_build(
        kind: AgentRuntimeKind, *, cwd: Path | None = None, model: object = None
    ) -> AgentRuntimePort:
        if kind is AgentRuntimeKind.FAKE:
            idx = calls["n"]
            calls["n"] = idx + 1
            chosen = per_step.get(str(idx), default)
            return FakeAgentRuntime(result=chosen)
        return real_build(kind, cwd=cwd)

    monkeypatch.setattr(container, "build_agent_runtime", fake_build)


def test_pipeline_runs_to_closure_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-23-02 — happy path: feeding every gate (qa, security, code) a green
    verdict+handoff advances the run through every phase and reaches terminal
    ``CLOSURE`` via the real CLI ``lifecycle pipeline`` surface."""
    # One passing result per ladder step (implement, review_qa, review_security,
    # review_code). The pipeline builds a fresh FAKE adapter per step, so index order
    # equals step order.
    _inject_passing_fake(
        monkeypatch,
        result_for={
            "0": _passing_result("implement"),
            "1": _passing_result("review_qa"),
            "2": _passing_result("review_security"),
            "3": _passing_result("review_code"),
        },
    )

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
            "pipe-full",
            "--harness",
            "fake",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "OK"
    assert payload["completed"] is True
    # Terminal phase is CLOSURE — the run advanced through every gate.
    assert payload["final_phase"] == LifecyclePhase.CLOSURE.value
    assert payload["blocked"] is None
    # Every step ran on the fake harness and was accepted, in ladder order.
    labels = [step["label"] for step in payload["steps"]]
    assert labels == ["implement", "review_qa", "review_security", "review_code"]
    assert all(step["accepted"] is True for step in payload["steps"])
    assert all(step["runtime"] == "fake" for step in payload["steps"])
    # The last accepted step landed the run in CLOSURE.
    assert payload["steps"][-1]["phase"] == LifecyclePhase.CLOSURE.value


def test_pipeline_qa_review_backtracks_to_implementation_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-23-03 — backtrack: a QA-review step whose ``target_phase`` is
    ``IMPLEMENTATION`` drives the real ``qa_review -> implementation`` transition-table
    backtrack end-to-end. After the implement step (IMPLEMENTATION -> QA_REVIEW) the
    rework gate routes the run back to IMPLEMENTATION.

    Note (production limitation): ``LifecycleAgentRunner`` maps a *non-APPROVED* worker
    result (including an explicit ``REJECTED`` verdict) to ``BLOCKED`` — it never itself
    routes a rejected review to ``IMPLEMENTATION``. The transition-table backtrack
    (``qa_review -> implementation``) is real but is expressed by a step that *targets*
    IMPLEMENTATION; the CLI's ``implementation_ladder`` never builds such a step, so this
    e2e drives the same engine with a custom rework ladder. The worker emits an APPROVED
    rework handoff so the backtrack transition is taken (the engine gates the
    *transition*, the rework decision is the step's ``target_phase``).
    """
    _inject_passing_fake(
        monkeypatch,
        result_for={
            "0": _passing_result("implement"),
            "1": _passing_result("review_qa_rework"),
        },
    )

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    pipeline = container.build_lifecycle_pipeline(
        workspace,
        context=_CONTEXT,
        release_id="multiharness-engine-v0116",
    )

    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    implement_step = ladder[0]
    qa_step = ladder[1]
    # Rework the QA gate so it backtracks to IMPLEMENTATION instead of advancing to
    # SECURITY_REVIEW (the transition table permits qa_review -> implementation).
    qa_backtrack: PipelineStep = replace(
        qa_step,
        label="review_qa_rework",
        target_phase=LifecyclePhase.IMPLEMENTATION,
    )

    result = pipeline.run("pipe-backtrack", (implement_step, qa_backtrack))

    assert result.completed is True
    # The run lands back in IMPLEMENTATION after the rejecting/rework QA gate.
    assert result.final_phase is LifecyclePhase.IMPLEMENTATION
    assert result.blocked is None
    labels = [step.label for step in result.steps]
    assert labels == ["implement", "review_qa_rework"]
    # implement advanced IMPLEMENTATION -> QA_REVIEW ...
    assert result.steps[0].phase is LifecyclePhase.QA_REVIEW
    # ... then the rework gate backtracked QA_REVIEW -> IMPLEMENTATION.
    assert result.steps[1].phase is LifecyclePhase.IMPLEMENTATION
    assert all(step.accepted for step in result.steps)


def test_pipeline_security_and_code_review_backtrack_to_implementation_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-23-03 — the security-review and code-review gates also backtrack to
    IMPLEMENTATION (the transition table permits ``security_review -> implementation``
    and ``code_review -> implementation``). Each is driven independently from its
    source phase through a one-step rework ladder, so we prove all three review
    backtracks the table allows."""
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    for source_idx, label in ((2, "review_security"), (3, "review_code")):
        review_step = ladder[source_idx]
        rework: PipelineStep = replace(
            review_step,
            label=f"{label}_rework",
            target_phase=LifecyclePhase.IMPLEMENTATION,
        )
        # Each sub-run is a single rework step starting at the review's source phase.
        _inject_passing_fake(monkeypatch, default=_passing_result(rework.label))
        pipeline = container.build_lifecycle_pipeline(
            workspace,
            context=_CONTEXT,
            release_id="multiharness-engine-v0116",
        )
        result = pipeline.run(f"pipe-backtrack-{label}", (rework,))

        assert result.completed is True, label
        assert result.final_phase is LifecyclePhase.IMPLEMENTATION, label
        assert result.blocked is None, label
        assert result.steps[0].phase is LifecyclePhase.IMPLEMENTATION, label
        assert result.steps[0].accepted is True, label
