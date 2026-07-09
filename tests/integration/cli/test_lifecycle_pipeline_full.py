"""End-to-end proofs of the lifecycle pipeline engine reaching terminal phases.

These complement ``test_lifecycle_pipeline_cli.py`` (which proves the run *blocks* at
the first gate on a no-op FAKE worker). Here we feed each gate a green/passing
verdict+handoff so the run actually *advances*:

* T-23-02 — the full implementation ladder (implement → qa → security → code) runs to
  completion and lands in terminal phase ``CLOSURE`` (the first e2e to get there).
* FR4 (v0.1.56) — the three review→implementation backtrack edges are REMOVED. A review
  step whose ``target_phase`` is ``IMPLEMENTATION`` is now an illegal transition the
  state machine rejects, so the run never returns to ``IMPLEMENTATION`` — it stays at its
  review phase. (These two tests were T-23-03, which asserted the now-removed backtrack;
  they are inverted for FR4 to prove the edges are gone. The retained operator-driven
  rework path is ``BLOCKED -> IMPLEMENTATION`` resume.)

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
    is_legal_transition,
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
            "--skip-preflight",
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


def test_pipeline_qa_review_cannot_backtrack_to_implementation_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR4 (v0.1.56) — the ``qa_review -> implementation`` backtrack edge is REMOVED.

    Was T-23-03 (which asserted the backtrack IS taken); inverted here to prove it is
    gone. A QA-review step that *targets* IMPLEMENTATION is now an illegal transition:
    the state machine rejects it, so after the implement step (IMPLEMENTATION ->
    QA_REVIEW) the rework step does NOT route the run back to IMPLEMENTATION — the run
    stays in QA_REVIEW. The retained operator-driven rework path is
    ``BLOCKED -> IMPLEMENTATION`` (resume), never a direct review backtrack. The CLI's
    ``implementation_ladder`` never builds such a review→implementation step in
    production; this e2e drives the same engine with a custom rework ladder to prove the
    engine rejects it.
    """
    # The removed edge: a non-blocked review phase can no longer return to IMPLEMENTATION.
    assert not is_legal_transition(LifecyclePhase.QA_REVIEW, LifecyclePhase.IMPLEMENTATION)

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
    # A rework step that targets IMPLEMENTATION from QA_REVIEW — the transition the table
    # no longer permits.
    qa_backtrack: PipelineStep = replace(
        qa_step,
        label="review_qa_rework",
        target_phase=LifecyclePhase.IMPLEMENTATION,
    )

    result = pipeline.run("pipe-no-backtrack", (implement_step, qa_backtrack))

    labels = [step.label for step in result.steps]
    assert labels == ["implement", "review_qa_rework"]
    # implement advanced IMPLEMENTATION -> QA_REVIEW ...
    assert result.steps[0].phase is LifecyclePhase.QA_REVIEW
    # ... but the rework step's now-illegal QA_REVIEW -> IMPLEMENTATION transition is
    # rejected by the state machine, so the run stays in QA_REVIEW and never reaches
    # IMPLEMENTATION.
    assert result.steps[1].phase is LifecyclePhase.QA_REVIEW
    assert result.final_phase is LifecyclePhase.QA_REVIEW
    assert result.final_phase is not LifecyclePhase.IMPLEMENTATION


def test_pipeline_security_and_code_review_cannot_backtrack_to_implementation_on_fake(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR4 (v0.1.56) — the ``security_review -> implementation`` and
    ``code_review -> implementation`` backtrack edges are REMOVED too.

    Was T-23-03 (which asserted these backtracks are taken); inverted here to prove they
    are gone. A rework step targeting IMPLEMENTATION from either review phase is an
    illegal transition the state machine rejects, so the run never returns to
    IMPLEMENTATION — it stays at its review phase. Each is driven independently from its
    source phase through a one-step rework ladder, so we prove all three review→
    implementation edges the table removed are rejected."""
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)

    workspace = _init_workspace(tmp_path)
    monkeypatch.chdir(workspace)

    for source_idx, label, review_phase in (
        (2, "review_security", LifecyclePhase.SECURITY_REVIEW),
        (3, "review_code", LifecyclePhase.CODE_REVIEW),
    ):
        # The removed edge for this review phase.
        assert not is_legal_transition(review_phase, LifecyclePhase.IMPLEMENTATION), label

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
        result = pipeline.run(f"pipe-no-backtrack-{label}", (rework,))

        # The illegal review -> IMPLEMENTATION transition is rejected: the run stays at its
        # review phase and never reaches IMPLEMENTATION.
        assert result.final_phase is review_phase, label
        assert result.final_phase is not LifecyclePhase.IMPLEMENTATION, label
        assert result.steps[0].phase is review_phase, label
