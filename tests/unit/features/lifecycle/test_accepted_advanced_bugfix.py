"""AC-8 (v0.1.57 FR5) — the accept computation is dual-signal at BOTH engine seams.

Regression for ``pipeline-accepted-true-on-illegal-transition``: a step whose worker
SUCCEEDS with valid evidence but whose phase transition is ILLEGAL must report
``accepted=False`` (the phase never advanced), even though the run carries no blocked
state. Pre-fix both seams computed ``accepted = run.blocked is None`` — ``True`` on an
illegal transition (the run is returned unchanged, ``blocked is None``). The fix routes
both seams through :attr:`TransitionDecision.advanced`
(``accepted and run.blocked is None``) — the state machine's own dual-signal contract.

v0.1.56 FR4 removed the review→IMPLEMENTATION backtrack edges, so a review-phase step
targeting IMPLEMENTATION is now a genuine illegal transition — the reachable trigger.
"""

from __future__ import annotations

from dataclasses import dataclass

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


def test_pipeline_illegal_transition_is_not_accepted() -> None:
    """AC-8 pipeline seam: a SUCCEEDED worker on an ILLEGAL transition is NOT accepted.

    RED-first: pre-fix ``accepted = run.blocked is None`` returns ``True`` here (the run is
    returned unchanged with ``blocked is None``), so the step is wrongly marked accepted and
    the pipeline completes. Post-fix ``accepted = decision.advanced`` is ``False``.
    """
    store = _MemoryRunStore()
    pipe = _pipeline(store, _success())
    # QA_REVIEW -> IMPLEMENTATION is illegal post-v0.1.56 FR4; is_review=False so the create
    # gate passes on the valid evidence, isolating the illegal-transition path.
    steps = (
        _step(
            from_phase=LifecyclePhase.QA_REVIEW,
            target_phase=LifecyclePhase.IMPLEMENTATION,
            is_review=False,
        ),
    )

    result = pipe.run("run-illegal", steps)

    assert result.steps[0].accepted is False
    # The run was NOT advanced and carries NO blocked state — the exact dual-signal the
    # single ``run.blocked is None`` predicate missed.
    assert result.steps[0].blocked is None
    assert result.completed is False
    assert result.final_phase is LifecyclePhase.QA_REVIEW


def test_pipeline_legal_blocked_review_is_not_accepted() -> None:
    """AC-8 pipeline seam (regression guard): a legally-BLOCKED review is not accepted."""
    store = _MemoryRunStore()
    pipe = _pipeline(store, _success(verdict="REJECTED"))
    steps = (
        _step(
            from_phase=LifecyclePhase.QA_REVIEW,
            target_phase=LifecyclePhase.SECURITY_REVIEW,
            is_review=True,
        ),
    )

    result = pipe.run("run-blocked", steps)

    assert result.steps[0].accepted is False
    assert result.steps[0].blocked is not None
    assert result.final_phase is LifecyclePhase.BLOCKED


def test_pipeline_legal_success_is_accepted() -> None:
    """AC-8 pipeline seam (regression guard): a legal APPROVED transition IS accepted."""
    store = _MemoryRunStore()
    pipe = _pipeline(store, _success())
    steps = (
        _step(
            from_phase=LifecyclePhase.QA_REVIEW,
            target_phase=LifecyclePhase.SECURITY_REVIEW,
            is_review=True,
        ),
    )

    result = pipe.run("run-ok", steps)

    assert result.steps[0].accepted is True
    assert result.steps[0].blocked is None
    assert result.completed is True
    assert result.final_phase is LifecyclePhase.SECURITY_REVIEW


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


def test_phase_workflow_illegal_transition_is_not_accepted() -> None:
    """AC-8 phase_workflow twin: the identical dual-signal fix holds at this seam.

    RED-first: pre-fix ``accepted=decision.run.blocked is None`` returns ``True`` on the
    illegal QA_REVIEW -> IMPLEMENTATION transition. Post-fix ``accepted=decision.advanced``
    is ``False``.
    """
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(runtime=FakeAgentRuntime(result=_success()), run_store=store)

    # target IMPLEMENTATION is not a review phase -> create-step gate passes on the valid
    # evidence; the QA_REVIEW -> IMPLEMENTATION transition itself is illegal.
    result = workflow.run(
        run_id="pw-illegal",
        command="review-qa",
        from_phase=LifecyclePhase.QA_REVIEW,
        target_phase=LifecyclePhase.IMPLEMENTATION,
        scope=_scope(),
    )

    assert result.accepted is False
    assert result.blocked is None
    assert result.phase is LifecyclePhase.QA_REVIEW


def test_phase_workflow_legal_blocked_review_is_not_accepted() -> None:
    """AC-8 phase_workflow twin (regression guard): a legally-BLOCKED review is not accepted."""
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(
        runtime=FakeAgentRuntime(result=_success(verdict="REJECTED")), run_store=store
    )

    result = workflow.run(
        run_id="pw-blocked",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=_scope(role="qa-engineer"),
    )

    assert result.accepted is False
    assert result.blocked is not None


def test_phase_workflow_legal_success_is_accepted() -> None:
    """AC-8 phase_workflow twin (regression guard): a legal APPROVED transition IS accepted."""
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(runtime=FakeAgentRuntime(result=_success()), run_store=store)

    result = workflow.run(
        run_id="pw-ok",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=_scope(role="qa-engineer"),
    )

    assert result.accepted is True
    assert result.blocked is None
    assert result.phase is LifecyclePhase.QA_REVIEW
