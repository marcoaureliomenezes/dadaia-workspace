"""Unit tests for lifecycle agent runner using a fake AgentRuntimePort.

These all exercise a REVIEW step (a qa-engineer step targeting ``QA_REVIEW``), so every
``AgentRunnerInput`` sets ``is_review=True``. Under the v0.1.31 review-only gate the verdict
requirement keys on the explicit ``is_review`` flag (not the target phase): a review step
still BLOCKs on a missing/REJECTED verdict, missing artifact evidence, and out-of-scope
paths. Create-step (``is_review=False``) gate behavior is covered by
``test_agent_runner_review_only_gate.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.models.lifecycle import (
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)


@dataclass(frozen=True)
class FakeAgentRuntime:
    result: AgentRunResult

    def runtime_kind(self) -> AgentRuntimeKind:
        return AgentRuntimeKind.FAKE

    def run(self, request: AgentRunRequest) -> AgentRunResult:
        return self.result


def _run() -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="implementation",
        idempotency_key="resume-1",
    )


def _request() -> AgentRunRequest:
    return AgentRunRequest(
        role="qa-engineer",
        prompt="review task",
        runtime=AgentRuntimeKind.FAKE,
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-16",
        allowed_paths=(".dadaia/handoff/dadaia-workspace/**",),
        forbidden_paths=("repos/dadaia-workspace/src/secrets.py",),
        required_evidence=(GateEvidenceKind.HANDOFF,),
    )


def test_fake_agent_runtime_can_advance_after_structured_output_and_scope_evidence() -> None:
    runtime: AgentRuntimePort = FakeAgentRuntime(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="qa approved",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
            structured_output={
                "verdict": "APPROVED",
                "task_group": "T-015-16",
                "changed_paths": ".dadaia/handoff/dadaia-workspace/qa.handoff.json",
            },
        )
    )
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
        task_group="T-015-16",
    )

    decision = LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            requirements=(requirement,),
            current_step="qa-review",
            is_review=True,
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.QA_REVIEW
    assert decision.run.blocked is None


def test_summary_says_approved_without_structured_verdict_does_not_pass_gate() -> None:
    runtime: AgentRuntimePort = FakeAgentRuntime(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="APPROVED by qa",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        )
    )

    decision = LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="qa-review",
            is_review=True,
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.blocked is not None
    assert decision.run.blocked.reason == "agent result missing APPROVED verdict"


def test_agent_says_approved_without_artifact_evidence_does_not_pass_gate() -> None:
    runtime: AgentRuntimePort = FakeAgentRuntime(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            structured_output={"verdict": "APPROVED"},
        )
    )

    decision = LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="qa-review",
            is_review=True,
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.blocked is not None
    assert decision.run.blocked.reason == "agent result missing artifact evidence"


def test_out_of_scope_artifact_blocks_before_transition() -> None:
    runtime: AgentRuntimePort = FakeAgentRuntime(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            artifact_refs=("repos/dadaia-workspace/src/secrets.py",),
            structured_output={"verdict": "APPROVED"},
        )
    )

    decision = LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="qa-review",
            is_review=True,
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.blocked is not None
    assert decision.run.blocked.reason == "agent result contains out-of-scope paths"
    assert decision.run.blocked.detail["out_of_scope"] == "repos/dadaia-workspace/src/secrets.py"


def test_sibling_prefix_path_does_not_match_allowed_scope() -> None:
    runtime: AgentRuntimePort = FakeAgentRuntime(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            artifact_refs=(".dadaia/handoff/dadaia-workspace-secret/qa.handoff.json",),
            structured_output={"verdict": "APPROVED"},
        )
    )

    decision = LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="qa-review",
            is_review=True,
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.blocked is not None
    assert decision.run.blocked.detail["out_of_scope"] == (
        ".dadaia/handoff/dadaia-workspace-secret/qa.handoff.json"
    )


def test_changed_paths_are_validated_against_write_scope() -> None:
    runtime: AgentRuntimePort = FakeAgentRuntime(
        AgentRunResult(
            status=AgentRunStatus.SUCCEEDED,
            summary="approved",
            artifact_refs=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
            structured_output={
                "verdict": "APPROVED",
                "changed_paths": ".dadaia/handoff/dadaia-workspace/qa.handoff.json,"
                "repos/dadaia-workspace/src/secrets.py",
            },
        )
    )

    decision = LifecycleAgentRunner(runtime=runtime).run(
        _run(),
        AgentRunnerInput(
            request=_request(),
            target_phase=LifecyclePhase.QA_REVIEW,
            current_step="qa-review",
            is_review=True,
        ),
    )

    assert decision.accepted is True
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.blocked is not None
    assert decision.run.blocked.detail["out_of_scope"] == "repos/dadaia-workspace/src/secrets.py"
