"""AC-8 (v0.1.57 FR5) — the accept computation is dual-signal at BOTH engine seams.

CRITICAL: accepted/verdict gating. Regression for
``pipeline-accepted-true-on-illegal-transition``: a step whose worker SUCCEEDS with valid
evidence but whose phase transition is ILLEGAL must report ``accepted=False`` (the phase never
advanced), even though the run carries no blocked state. Pre-fix both seams computed
``accepted = run.blocked is None`` — ``True`` on an illegal transition (the run is returned
unchanged, ``blocked is None``). The fix routes both seams through
:attr:`TransitionDecision.advanced` (``accepted and run.blocked is None``) — the state
machine's own dual-signal contract. Both seams must survive (the bug was per-seam
recomputation); the root predicate itself is pinned separately in ``test_state_machine.py``.

v0.1.56 FR4 removed the review->IMPLEMENTATION backtrack edges, so a review-phase step
targeting IMPLEMENTATION is now a genuine illegal transition — the reachable trigger.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.phase_workflow import LifecyclePhaseWorkflow
from dadaia_workspace.features.lifecycle.pipeline import LifecyclePipeline, PipelineStep
from dadaia_workspace.features.lifecycle.prompt_builder import PromptScope
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime


class _MemoryRunStore:
    def __init__(self) -> None:
        self.saved: dict[str, LifecycleRun] = {}

    def save(self, run: LifecycleRun) -> None:
        self.saved[run.run_id] = run

    def load(self, run_id: str) -> LifecycleRun | None:
        return self.saved.get(run_id)

    def resume(self, run_id: str) -> LifecycleRun:
        run = self.saved.get(run_id)
        if run is None:
            raise LifecycleRunStoreError(message="missing", path=None)
        return run


@dataclass(frozen=True)
class _KindFake:
    kind: AgentRuntimeKind
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return self.kind

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return self.result


def _success(verdict: str = "APPROVED") -> AgentRunResult:
    """A worker result that PASSES the evidence gate (SUCCEEDED + in-scope artifact)."""
    return AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/x.handoff.json",),
        structured_output={"verdict": verdict},
    )


def _pipeline(store: _MemoryRunStore, result: AgentRunResult) -> LifecyclePipeline:
    return LifecyclePipeline(
        context="dadaia-workspace",
        release_id="v0.1.57",
        run_store=store,
        runtime_factory=lambda kind: _KindFake(kind, result),  # type: ignore[arg-type,return-value]
    )


def _step(
    *,
    from_phase: LifecyclePhase,
    target_phase: LifecyclePhase,
    is_review: bool,
) -> PipelineStep:
    return PipelineStep(
        label="step",
        role="software-engineer",
        from_phase=from_phase,
        target_phase=target_phase,
        runtime_kind=AgentRuntimeKind.FAKE,
        is_review=is_review,
    )


# --- pipeline seam (LifecyclePipeline.run) -----------------------------------

_PIPELINE_CASES = (
    # (case_id, from_phase, target_phase, is_review, verdict, expect_accepted,
    #  expect_blocked, expect_completed, expect_final_phase)
    (
        "illegal-not-accepted",
        LifecyclePhase.QA_REVIEW,
        LifecyclePhase.IMPLEMENTATION,
        False,
        "APPROVED",
        False,
        False,
        False,
        LifecyclePhase.QA_REVIEW,
    ),
    (
        "legal-blocked-review-not-accepted",
        LifecyclePhase.QA_REVIEW,
        LifecyclePhase.SECURITY_REVIEW,
        True,
        "REJECTED",
        False,
        True,
        None,
        LifecyclePhase.BLOCKED,
    ),
    (
        "legal-success-accepted",
        LifecyclePhase.QA_REVIEW,
        LifecyclePhase.SECURITY_REVIEW,
        True,
        "APPROVED",
        True,
        False,
        True,
        LifecyclePhase.SECURITY_REVIEW,
    ),
)


@pytest.mark.parametrize(
    "case_id,from_phase,target_phase,is_review,verdict,expect_accepted,expect_blocked,"
    "expect_completed,expect_final_phase",
    _PIPELINE_CASES,
    ids=[c[0] for c in _PIPELINE_CASES],
)
def test_pipeline_seam_accepted_matrix(
    case_id: str,
    from_phase: LifecyclePhase,
    target_phase: LifecyclePhase,
    is_review: bool,
    verdict: str,
    expect_accepted: bool,
    expect_blocked: bool,
    expect_completed: bool | None,
    expect_final_phase: LifecyclePhase,
) -> None:
    """RED-first (illegal case): pre-fix ``accepted = run.blocked is None`` returns True here
    (the run is returned unchanged, blocked is None), wrongly marking the step accepted.
    Post-fix ``accepted = decision.advanced`` is False."""
    store = _MemoryRunStore()
    pipe = _pipeline(store, _success(verdict=verdict))
    steps = (_step(from_phase=from_phase, target_phase=target_phase, is_review=is_review),)

    result = pipe.run(f"run-{case_id}", steps)

    assert result.steps[0].accepted is expect_accepted
    assert (result.steps[0].blocked is not None) is expect_blocked
    if expect_completed is not None:
        assert result.completed is expect_completed
    assert result.final_phase is expect_final_phase


# --- phase_workflow twin seam (LifecyclePhaseWorkflow.run) -------------------


def _scope(role: str = "software-engineer") -> PromptScope:
    return PromptScope(
        role=role,
        context="dadaia-workspace",
        release_id="v0.1.57",
        task_id="step",
        prompt="run the step",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


_PHASE_WORKFLOW_CASES = (
    # (case_id, from_phase, target_phase, role, verdict, expect_accepted, expect_blocked,
    #  expect_phase)
    (
        "illegal-not-accepted",
        LifecyclePhase.QA_REVIEW,
        LifecyclePhase.IMPLEMENTATION,
        "software-engineer",
        "APPROVED",
        False,
        False,
        LifecyclePhase.QA_REVIEW,
    ),
    (
        "legal-blocked-review-not-accepted",
        LifecyclePhase.IMPLEMENTATION,
        LifecyclePhase.QA_REVIEW,
        "qa-engineer",
        "REJECTED",
        False,
        True,
        None,
    ),
    (
        "legal-success-accepted",
        LifecyclePhase.IMPLEMENTATION,
        LifecyclePhase.QA_REVIEW,
        "qa-engineer",
        "APPROVED",
        True,
        False,
        LifecyclePhase.QA_REVIEW,
    ),
)


@pytest.mark.parametrize(
    "case_id,from_phase,target_phase,role,verdict,expect_accepted,expect_blocked,expect_phase",
    _PHASE_WORKFLOW_CASES,
    ids=[c[0] for c in _PHASE_WORKFLOW_CASES],
)
def test_phase_workflow_seam_accepted_matrix(
    case_id: str,
    from_phase: LifecyclePhase,
    target_phase: LifecyclePhase,
    role: str,
    verdict: str,
    expect_accepted: bool,
    expect_blocked: bool,
    expect_phase: LifecyclePhase | None,
) -> None:
    """RED-first (illegal case): pre-fix ``accepted=decision.run.blocked is None`` returns
    True on the illegal QA_REVIEW -> IMPLEMENTATION transition. Post-fix
    ``accepted=decision.advanced`` is False. The identical dual-signal fix holds at this
    seam as at the pipeline seam."""
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(
        runtime=FakeAgentRuntime(result=_success(verdict=verdict)), run_store=store
    )

    result = workflow.run(
        run_id=f"pw-{case_id}",
        command="review-qa",
        from_phase=from_phase,
        target_phase=target_phase,
        scope=_scope(role=role),
    )

    assert result.accepted is expect_accepted
    assert (result.blocked is not None) is expect_blocked
    if expect_phase is not None:
        assert result.phase is expect_phase
