"""WS-1 — LifecyclePhaseWorkflow drives one step end-to-end on a selectable harness.

CRITICAL: review-only gating at the single-step seam (review REJECTED blocks; create passes
verdict-less).
"""

from __future__ import annotations

from dadaia_workspace.container import build_agent_runtime
from dadaia_workspace.core.models.lifecycle import (
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStoreError
from dadaia_workspace.features.lifecycle.phase_workflow import LifecyclePhaseWorkflow
from dadaia_workspace.features.lifecycle.prompt_builder import PromptScope
from dadaia_workspace.infrastructure.fake_runtime import FakeAgentRuntime


class _MemoryRunStore:
    """In-memory LifecycleRunStore for hermetic tests."""

    def __init__(self) -> None:
        self.saved: dict[str, LifecycleRun] = {}

    def save(self, run: LifecycleRun) -> None:
        self.saved[run.run_id] = run

    def load(self, run_id: str) -> LifecycleRun | None:
        return self.saved.get(run_id)

    def resume(self, run_id: str) -> LifecycleRun:
        run = self.saved.get(run_id)
        if run is None:
            raise LifecycleRunStoreError(message="no such run", path=None)
        return run


def _scope(
    *,
    role: str = "qa-engineer",
    task_id: str = "review-qa",
    prompt: str = "run the qa gate",
) -> PromptScope:
    return PromptScope(
        role=role,
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        task_id=task_id,
        prompt=prompt,
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def test_phase_workflow_accepts_approved_blocks_no_verdict_passes_create_verdictless() -> None:
    """Three facets of one seam, parametrized: an APPROVED review-phase step accepts +
    persists at the accepted phase; a factory-FAKE run with no verdict field BLOCKs (and is
    still persisted for resume/audit); a create-phase step with a valid payload passes
    regardless of the (absent) verdict."""
    approved = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="qa approved",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        structured_output={"verdict": "APPROVED", "task_group": "review-qa"},
    )
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(runtime=FakeAgentRuntime(result=approved), run_store=store)

    result = workflow.run(
        run_id="run-qa-1",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=_scope(),
    )

    assert result.accepted is True
    assert result.phase is LifecyclePhase.QA_REVIEW
    assert result.runtime_kind is AgentRuntimeKind.FAKE
    assert result.blocked is None
    assert store.saved["run-qa-1"].phase is LifecyclePhase.QA_REVIEW

    store2 = _MemoryRunStore()
    workflow2 = LifecyclePhaseWorkflow(
        runtime=build_agent_runtime(AgentRuntimeKind.FAKE),
        run_store=store2,
    )
    result2 = workflow2.run(
        run_id="run-qa-2",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=_scope(),
    )
    assert result2.accepted is False
    assert result2.blocked is not None
    assert "APPROVED verdict" in result2.blocked.reason
    assert "run-qa-2" in store2.saved

    # v0.1.31 / T-31-A-06: a create-phase step is NOT verdict-gated — a valid payload
    # (artifact_refs) + in-scope paths passes regardless of the (absent) verdict.
    no_verdict = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="implementation produced evidence",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/impl.handoff.json",),
        structured_output={"task_group": "implement"},
    )
    store3 = _MemoryRunStore()
    workflow3 = LifecyclePhaseWorkflow(
        runtime=FakeAgentRuntime(result=no_verdict), run_store=store3
    )
    result3 = workflow3.run(
        run_id="run-impl-create",
        command="implement",
        from_phase=LifecyclePhase.RELEASE_DEFINITION,
        target_phase=LifecyclePhase.IMPLEMENTATION,
        scope=_scope(role="software-engineer", task_id="implement", prompt="implement the task"),
    )
    assert result3.accepted is True
    assert result3.blocked is None
    assert result3.phase is LifecyclePhase.IMPLEMENTATION


def test_phase_workflow_review_phase_step_gates_on_verdict() -> None:
    # v0.1.31 / T-31-A-06: a step targeting a REVIEW phase runs as a review step and is
    # gated on verdict — a REJECTED verdict (with valid evidence) STILL BLOCKs.
    rejected = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="qa rejected",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        structured_output={"verdict": "REJECTED", "task_group": "review-qa"},
    )
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(runtime=FakeAgentRuntime(result=rejected), run_store=store)

    result = workflow.run(
        run_id="run-qa-rejected",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=_scope(),
    )

    assert result.accepted is False
    assert result.blocked is not None
    assert "APPROVED verdict" in result.blocked.reason


def test_phase_workflow_persists_policy_snapshot_and_threads_resolved_model() -> None:
    # T-28-A-07: a single-step run persists the workflow_policy snapshot, and the resolved
    # model on the scope reaches the worker's request.
    import dataclasses

    from dadaia_workspace.core.models.workflow_execution import (
        PolicySource,
        ResolvedModelConfig,
        WorkflowPolicySnapshot,
        WorkflowPolicyStepEntry,
    )

    approved = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="ok",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        structured_output={"verdict": "APPROVED"},
    )
    runtime = FakeAgentRuntime(result=approved)
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(runtime=runtime, run_store=store)

    resolved = ResolvedModelConfig(
        profile_id="codex-review-deep",
        harness="codex",
        model="gpt-5.5",
        reasoning="high",
        source=PolicySource.CLI,
    )
    snapshot = WorkflowPolicySnapshot(
        workflow_id="implementation",
        policy_id="default",
        resolved_at="2026-06-26T12:00:00Z",
        steps=(
            WorkflowPolicyStepEntry(
                step="review_qa",
                harness="codex",
                model_profile="codex-review-deep",
                model="gpt-5.5",
                reasoning="high",
                source=PolicySource.CLI,
            ),
        ),
    )

    workflow.run(
        run_id="run-qa-policy",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=dataclasses.replace(_scope(), resolved_model=resolved),
        policy_snapshot=snapshot,
    )

    # snapshot persisted on the run (survives the transition via dataclasses.replace)
    persisted = store.saved["run-qa-policy"]
    assert persisted.workflow_policy is not None
    assert persisted.workflow_policy.step("review_qa") is not None
    # resolved model threaded into the worker request
    assert runtime.received_models[0] == resolved
