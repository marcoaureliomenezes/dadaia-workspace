"""WS-1 — LifecyclePhaseWorkflow drives one step end-to-end on a selectable harness."""

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


def _scope() -> PromptScope:
    return PromptScope(
        role="qa-engineer",
        context="dadaia-workspace",
        release_id="multiharness-engine-v0116",
        task_id="review-qa",
        prompt="run the qa gate",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def test_phase_workflow_accepts_on_approved_verdict_and_persists_run() -> None:
    approved = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="qa approved",
        artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        structured_output={"verdict": "APPROVED", "task_group": "review-qa"},
    )
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(
        runtime=FakeAgentRuntime(result=approved),
        run_store=store,
    )

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
    # The run record was persisted at its accepted phase (resumable).
    assert store.saved["run-qa-1"].phase is LifecyclePhase.QA_REVIEW


def test_phase_workflow_blocks_when_factory_fake_gives_no_verdict() -> None:
    store = _MemoryRunStore()
    workflow = LifecyclePhaseWorkflow(
        runtime=build_agent_runtime(AgentRuntimeKind.FAKE),
        run_store=store,
    )

    result = workflow.run(
        run_id="run-qa-2",
        command="review-qa",
        from_phase=LifecyclePhase.IMPLEMENTATION,
        target_phase=LifecyclePhase.QA_REVIEW,
        scope=_scope(),
    )

    assert result.accepted is False
    assert result.blocked is not None
    assert "APPROVED verdict" in result.blocked.reason
    # Even a blocked run is persisted for resume/audit.
    assert "run-qa-2" in store.saved


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
