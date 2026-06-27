"""Implement/review attempt loop with bounded retry (v0.1.30 Item 5 / T-30-D-06).

Pins A24:
- ``implement#2`` consumes the EXACT ``qa#1`` rejection by (run, producer step, attempt)
  — never ``qa#0`` / an unrelated run.
- the bounded retry count (default 2) BLOCKS for operator intervention when exceeded.

Hermetic: real ``JsonLifecycleRunStore`` + real ``FilesystemRuntimeFileAdapter`` under
``tmp_path``, a fake runtime whose verdict is scripted per review attempt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    LifecyclePhase,
)
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, PipelineStep
from dadaia_workspace.features.lifecycle.workflow_handoffs import WorkflowHandoffResolver
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter

_CONTEXT = "dadaia-workspace"
_RELEASE = "v0.1.30"


@dataclass
class _ScriptedReviewRuntime:
    """Implement always succeeds; review returns the scripted verdict per attempt."""

    kind: AgentRuntimeKind
    review_verdicts: list[str]
    _review_calls: int = 0

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        role = request.role
        if "qa" in role or "review" in role:
            idx = min(self._review_calls, len(self.review_verdicts) - 1)
            verdict = self.review_verdicts[idx]
            self._review_calls += 1
            return AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary=f"review verdict {verdict}",
                artifact_refs=(f".dadaia/handoff/{_CONTEXT}/qa.handoff.json",),
                structured_output={"verdict": verdict},
            )
        return AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="implementation done",
            artifact_refs=(f".dadaia/handoff/{_CONTEXT}/impl.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        )


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    return tmp_path


def _steps() -> tuple[PipelineStep, PipelineStep]:
    implement = PipelineStep(
        label="implement",
        role="software-engineer",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        runtime_kind=AgentRuntimeKind.FAKE,
    )
    review = PipelineStep(
        label="qa",
        role="qa-engineer",
        from_phase=LifecyclePhase.QA_REVIEW,
        target_phase=LifecyclePhase.IMPLEMENTATION,
        runtime_kind=AgentRuntimeKind.FAKE,
    )
    return implement, review


def _pipeline(tmp_path: Path, verdicts: list[str], *, max_retries: int = 2) -> LifecyclePipeline:
    runtime = _ScriptedReviewRuntime(AgentRuntimeKind.FAKE, verdicts)
    resolver = WorkflowHandoffResolver(
        run_store=JsonLifecycleRunStore(tmp_path),
        payload_writer=FilesystemRuntimeFileAdapter(tmp_path),
        clock=lambda: "2026-06-27T12:00:00Z",
    )
    return LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: runtime,  # type: ignore[arg-type]
        handoff_resolver=resolver,
        max_review_retries=max_retries,
    )


# --- A24: implement#2 consumes the exact qa#1 rejection ---------------------------


def test_implement_attempt_2_consumes_exact_qa_attempt_1(tmp_path: Path) -> None:
    _workspace(tmp_path)
    # round 0 REJECTED, round 1 REJECTED, round 2 APPROVED → 3 attempts, success in bound.
    pipeline = _pipeline(tmp_path, ["REJECTED", "REJECTED", "APPROVED"], max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-1", implement_step=_steps()[0], review_step=_steps()[1]
    )

    assert result.completed is True
    assert result.attempts == 3

    run = JsonLifecycleRunStore(tmp_path).load("loop-1")
    assert run is not None
    # implement#2 recorded a consumption of qa#1 — the EXACT prior-round rejection.
    qa1 = run.workflow_steps.find("qa", 1)
    assert qa1 is not None
    consumers = {(c.consumer_step, c.consumer_attempt) for c in qa1.consumptions}
    assert ("implement", 2) in consumers
    # And it did NOT consume qa#0 as the round-2 input (qa#0 was consumed by implement#1).
    qa0 = run.workflow_steps.find("qa", 0)
    assert qa0 is not None
    qa0_consumers = {(c.consumer_step, c.consumer_attempt) for c in qa0.consumptions}
    assert ("implement", 1) in qa0_consumers
    assert ("implement", 2) not in qa0_consumers


# --- A24: bounded retry exceeded → BLOCK ------------------------------------------


def test_loop_blocks_after_bounded_retries_exceeded(tmp_path: Path) -> None:
    _workspace(tmp_path)
    # always REJECTED → never approves; with max_retries=2 there are 3 attempts then BLOCK.
    pipeline = _pipeline(tmp_path, ["REJECTED"], max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-block", implement_step=_steps()[0], review_step=_steps()[1]
    )

    assert result.completed is False
    assert result.attempts == 3
    assert result.blocked is not None
    assert "bounded retry" in result.blocked.reason

    run = JsonLifecycleRunStore(tmp_path).load("loop-block")
    assert run is not None
    assert run.phase is LifecyclePhase.BLOCKED


def test_loop_completes_on_first_approval(tmp_path: Path) -> None:
    _workspace(tmp_path)
    pipeline = _pipeline(tmp_path, ["APPROVED"], max_retries=2)

    result = pipeline.run_implement_review_loop(
        "loop-fast", implement_step=_steps()[0], review_step=_steps()[1]
    )

    assert result.completed is True
    assert result.attempts == 1
    run = JsonLifecycleRunStore(tmp_path).load("loop-fast")
    assert run is not None
    # Exactly one implement + one qa payload.
    assert run.workflow_steps.find("implement", 0) is not None
    assert run.workflow_steps.find("qa", 0) is not None
    assert run.workflow_steps.find("implement", 1) is None


def test_loop_requires_resolver(tmp_path: Path) -> None:
    _workspace(tmp_path)
    pipeline = LifecyclePipeline(
        context=_CONTEXT,
        release_id=_RELEASE,
        run_store=JsonLifecycleRunStore(tmp_path),
        runtime_factory=lambda kind: _ScriptedReviewRuntime(kind, ["APPROVED"]),  # type: ignore[arg-type]
    )
    import pytest

    with pytest.raises(ValueError):
        pipeline.run_implement_review_loop(
            "loop-x", implement_step=_steps()[0], review_step=_steps()[1]
        )
