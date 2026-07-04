"""Unit tests for pure lifecycle core models."""

import dataclasses

import pytest

from dadaia_workspace.core.models.lifecycle import (
    TRANSITIONS,
    AgentRunRequest,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeKind,
    BlockedState,
    GateEvidence,
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
    is_legal_transition,
)


def test_lifecycle_transition_table_allows_expected_forward_path() -> None:
    assert is_legal_transition(LifecyclePhase.BACKLOG_DEFINITION, LifecyclePhase.RELEASE_DEFINITION)
    assert is_legal_transition(LifecyclePhase.RELEASE_DEFINITION, LifecyclePhase.IMPLEMENTATION)
    assert is_legal_transition(LifecyclePhase.IMPLEMENTATION, LifecyclePhase.QA_REVIEW)
    assert is_legal_transition(LifecyclePhase.QA_REVIEW, LifecyclePhase.SECURITY_REVIEW)
    assert is_legal_transition(LifecyclePhase.SECURITY_REVIEW, LifecyclePhase.CODE_REVIEW)
    assert is_legal_transition(LifecyclePhase.CODE_REVIEW, LifecyclePhase.CLOSURE)


def test_lifecycle_transition_table_rejects_illegal_skips() -> None:
    assert not is_legal_transition(LifecyclePhase.BACKLOG_DEFINITION, LifecyclePhase.IMPLEMENTATION)
    assert not is_legal_transition(LifecyclePhase.IMPLEMENTATION, LifecyclePhase.CLOSURE)
    assert not is_legal_transition(LifecyclePhase.QA_REVIEW, LifecyclePhase.CODE_REVIEW)


def test_blocked_phase_can_resume_to_any_lifecycle_phase_except_itself() -> None:
    for phase in LifecyclePhase:
        if phase is LifecyclePhase.BLOCKED:
            assert not is_legal_transition(LifecyclePhase.BLOCKED, phase)
        else:
            assert is_legal_transition(LifecyclePhase.BLOCKED, phase)


def test_review_phases_cannot_backtrack_to_implementation() -> None:
    # FR4 (v0.1.56): the three review->implementation backtrack edges are removed. The
    # state table no longer permits a (non-blocked) review phase to return to
    # IMPLEMENTATION; the retained operator-driven rework path is BLOCKED -> IMPLEMENTATION
    # (covered by test_blocked_phase_can_resume_* above).
    assert not is_legal_transition(LifecyclePhase.QA_REVIEW, LifecyclePhase.IMPLEMENTATION)
    assert not is_legal_transition(LifecyclePhase.SECURITY_REVIEW, LifecyclePhase.IMPLEMENTATION)
    assert not is_legal_transition(LifecyclePhase.CODE_REVIEW, LifecyclePhase.IMPLEMENTATION)


def test_transitions_table_pins_review_targets_by_frozenset_equality() -> None:
    # AC-5 (v0.1.56): exact frozenset-equality pins (not spot-checks) so a future stray
    # review->implementation edge fails the pin. Each review phase's only legal targets
    # are the next forward phase and BLOCKED.
    assert TRANSITIONS[LifecyclePhase.QA_REVIEW] == frozenset(
        {LifecyclePhase.SECURITY_REVIEW, LifecyclePhase.BLOCKED}
    )
    assert TRANSITIONS[LifecyclePhase.SECURITY_REVIEW] == frozenset(
        {LifecyclePhase.CODE_REVIEW, LifecyclePhase.BLOCKED}
    )
    assert TRANSITIONS[LifecyclePhase.CODE_REVIEW] == frozenset(
        {LifecyclePhase.CLOSURE, LifecyclePhase.BLOCKED}
    )


def test_lifecycle_run_round_trips_to_primitive_dict() -> None:
    run = LifecycleRun(
        run_id="20260618T040000Z-abc123",
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="lifecycle preflight",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.BLOCKED,
        current_step="push_readiness",
        expected_artifacts=("handoff",),
        idempotency_key="ctx-release-command",
        blocked=BlockedState(
            reason="push_blocked",
            blocked_at_step="push_readiness",
            resume_token="resume-1",
            operator_command="git push",
            detail={"branch": "feature/v0.1.15"},
        ),
    )

    data = run.to_dict()
    assert data["phase"] == "implementation"
    assert data["status"] == "blocked"
    assert data["expected_artifacts"] == ["handoff"]
    assert data["blocked"] == {
        "reason": "push_blocked",
        "blocked_at_step": "push_readiness",
        "resume_token": "resume-1",
        "operator_command": "git push",
        "detail": {"branch": "feature/v0.1.15"},
    }

    assert LifecycleRun.from_dict(data) == run


def test_gate_requirement_round_trips_review_identity() -> None:
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="security-reviewer",
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
        commit_sha="abc123",
        task_group="T-015-01",
        max_unresolved_severity="MEDIUM",
    )

    data = requirement.to_dict()
    assert data == {
        "evidence_kind": "handoff",
        "required_agent": "security-reviewer",
        "required_verdict": "APPROVED",
        "release_id": "v0.1.15",
        "commit_sha": "abc123",
        "task_group": "T-015-01",
        "max_unresolved_severity": "MEDIUM",
    }
    assert GateRequirement.from_dict(data) == requirement


def test_gate_evidence_round_trips_review_artifact_identity() -> None:
    evidence = GateEvidence(
        evidence_kind=GateEvidenceKind.HANDOFF,
        source=".dadaia/handoff/dadaia-workspace/review.handoff.json",
        context="dadaia-workspace",
        release_id="v0.1.15",
        agent="qa-engineer",
        verdict=GateVerdict.APPROVED,
        commit_sha="abc123",
        task_group="T-015-01",
        metrics={"tests_passed": "8"},
    )

    data = evidence.to_dict()
    assert data == {
        "evidence_kind": "handoff",
        "source": ".dadaia/handoff/dadaia-workspace/review.handoff.json",
        "context": "dadaia-workspace",
        "release_id": "v0.1.15",
        "agent": "qa-engineer",
        "verdict": "APPROVED",
        "commit_sha": "abc123",
        "task_group": "T-015-01",
        "metrics": {"tests_passed": "8"},
    }
    assert GateEvidence.from_dict(data) == evidence


def test_agent_run_request_round_trips_scoped_prompt_contract() -> None:
    request = AgentRunRequest(
        role="software-engineer",
        prompt="Implement T-015-01 only.",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="dadaia-workspace",
        release_id="v0.1.15",
        task_id="T-015-01",
        model_profile="codex-default",
        allowed_paths=("dadaia_workspace/core/models/lifecycle.py",),
        forbidden_paths=("repos/other",),
        expected_schema="agent-run-result-v1",
        required_evidence=(GateEvidenceKind.TEST_RESULT, GateEvidenceKind.DIRTY_DIFF),
    )

    data = request.to_dict()
    assert data["runtime"] == "codex_exec"
    assert data["allowed_paths"] == ["dadaia_workspace/core/models/lifecycle.py"]
    assert data["required_evidence"] == ["test_result", "dirty_diff"]
    assert AgentRunRequest.from_dict(data) == request


def test_agent_run_result_round_trips_structured_output() -> None:
    result = AgentRunResult(
        status=AgentRunStatus.SUCCEEDED,
        summary="Implemented lifecycle models.",
        artifact_refs=("tests/unit/core/test_lifecycle_models.py",),
        structured_output={"tests": "passed"},
    )

    data = result.to_dict()
    assert data["status"] == "succeeded"
    assert data["structured_output"] == {"tests": "passed"}
    assert AgentRunResult.from_dict(data) == result


def test_agent_run_request_carries_resolved_model(tmp_path: object = None) -> None:
    from dadaia_workspace.core.models.workflow_execution import (
        PolicySource,
        ResolvedModelConfig,
    )

    request = AgentRunRequest(
        role="software-engineer",
        prompt="Implement.",
        runtime=AgentRuntimeKind.CODEX_EXEC,
        context="dadaia-workspace",
        release_id="v0.1.28",
        resolved_model=ResolvedModelConfig(
            profile_id="codex-implementation-standard",
            harness="codex",
            model="gpt-5.5",
            reasoning="medium",
            source=PolicySource.CLI,
        ),
    )
    data = request.to_dict()
    assert data["resolved_model"]["model"] == "gpt-5.5"
    assert AgentRunRequest.from_dict(data) == request


def test_agent_run_request_resolved_model_defaults_none() -> None:
    request = AgentRunRequest(
        role="r",
        prompt="p",
        runtime=AgentRuntimeKind.FAKE,
        context="c",
        release_id="v0.1.28",
    )
    assert request.resolved_model is None
    assert request.to_dict()["resolved_model"] is None


def test_agent_run_request_back_compat_without_resolved_model() -> None:
    # An old serialized request (no 'resolved_model' key) still loads.
    legacy = {
        "role": "r",
        "prompt": "p",
        "runtime": "fake",
        "context": "c",
        "release_id": "v0.1.28",
        "task_id": None,
        "model_profile": None,
        "allowed_paths": [],
        "forbidden_paths": [],
        "expected_schema": None,
        "required_evidence": [],
    }
    request = AgentRunRequest.from_dict(legacy)
    assert request.resolved_model is None


def test_lifecycle_run_carries_workflow_policy_snapshot() -> None:
    from dadaia_workspace.core.models.workflow_execution import (
        PolicySource,
        WorkflowPolicySnapshot,
        WorkflowPolicyStepEntry,
    )

    snapshot = WorkflowPolicySnapshot(
        workflow_id="implementation",
        policy_id="default",
        resolved_at="2026-06-26T12:00:00Z",
        source_precedence=("cli", "library-default"),
        steps=(
            WorkflowPolicyStepEntry(
                step="implement",
                harness="codex",
                model_profile="codex-implementation-standard",
                model="gpt-5.5",
                reasoning="medium",
                source=PolicySource.LIBRARY_DEFAULT,
            ),
        ),
    )
    run = LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.28",
        command="pipeline",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="implement",
        workflow_policy=snapshot,
    )
    data = run.to_dict()
    assert data["workflow_policy"]["workflow_id"] == "implementation"
    assert LifecycleRun.from_dict(data) == run


def test_lifecycle_run_back_compat_without_workflow_policy() -> None:
    # M1: an old v1 record (no 'workflow_policy' key) still loads.
    legacy = {
        "run_id": "run-1",
        "context": "dadaia-workspace",
        "release_id": "v0.1.15",
        "command": "implement",
        "phase": "implementation",
        "status": "running",
        "current_step": "implement",
        "expected_artifacts": [],
        "idempotency_key": "idem-1",
        "blocked": None,
        "injected_context": [],
    }
    run = LifecycleRun.from_dict(legacy)
    assert run.workflow_policy is None


def test_lifecycle_models_are_frozen() -> None:
    run = LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="status",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=LifecycleRunStatus.RUNNING,
        current_step="status",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        run.status = LifecycleRunStatus.COMPLETED  # type: ignore[misc]
