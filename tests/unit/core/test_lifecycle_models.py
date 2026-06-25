"""Unit tests for pure lifecycle core models."""

import dataclasses

import pytest

from dadaia_workspace.core.models.lifecycle import (
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
