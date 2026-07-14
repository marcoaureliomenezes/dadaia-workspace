"""Unit tests for pure lifecycle core models."""

from __future__ import annotations

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


def test_transitions_table_pins_the_full_review_ladder_by_frozenset_equality() -> None:
    """AC-5 (v0.1.56): exact frozenset-equality pins (not spot-checks) so a future stray
    edge fails the pin. Subsumes the forward-path, illegal-skip, BLOCKED-resume, and
    no-review-backtrack spot checks as explicit rows/asserts below — the frozenset
    equality is the single source of truth for legal transitions.
    """
    # Forward path.
    assert is_legal_transition(LifecyclePhase.BACKLOG_DEFINITION, LifecyclePhase.RELEASE_DEFINITION)
    assert is_legal_transition(LifecyclePhase.RELEASE_DEFINITION, LifecyclePhase.IMPLEMENTATION)
    assert is_legal_transition(LifecyclePhase.IMPLEMENTATION, LifecyclePhase.QA_REVIEW)
    assert is_legal_transition(LifecyclePhase.QA_REVIEW, LifecyclePhase.SECURITY_REVIEW)
    assert is_legal_transition(LifecyclePhase.SECURITY_REVIEW, LifecyclePhase.CODE_REVIEW)
    assert is_legal_transition(LifecyclePhase.CODE_REVIEW, LifecyclePhase.CLOSURE)

    # Illegal skips.
    assert not is_legal_transition(LifecyclePhase.BACKLOG_DEFINITION, LifecyclePhase.IMPLEMENTATION)
    assert not is_legal_transition(LifecyclePhase.IMPLEMENTATION, LifecyclePhase.CLOSURE)
    assert not is_legal_transition(LifecyclePhase.QA_REVIEW, LifecyclePhase.CODE_REVIEW)

    # BLOCKED can resume to any phase except itself.
    for phase in LifecyclePhase:
        if phase is LifecyclePhase.BLOCKED:
            assert not is_legal_transition(LifecyclePhase.BLOCKED, phase)
        else:
            assert is_legal_transition(LifecyclePhase.BLOCKED, phase)

    # FR4 (v0.1.56): review phases cannot backtrack to IMPLEMENTATION — the retained
    # operator-driven rework path is BLOCKED -> IMPLEMENTATION only (proven above).
    assert not is_legal_transition(LifecyclePhase.QA_REVIEW, LifecyclePhase.IMPLEMENTATION)
    assert not is_legal_transition(LifecyclePhase.SECURITY_REVIEW, LifecyclePhase.IMPLEMENTATION)
    assert not is_legal_transition(LifecyclePhase.CODE_REVIEW, LifecyclePhase.IMPLEMENTATION)

    # The exact frozenset-equality pin: each review phase's only legal targets are the
    # next forward phase and BLOCKED.
    # QA_REVIEW additionally reaches CLOSURE: the combined single-review ladder runs
    # one tri-angle review under QA_REVIEW and advances straight to closure.
    assert TRANSITIONS[LifecyclePhase.QA_REVIEW] == frozenset(
        {LifecyclePhase.SECURITY_REVIEW, LifecyclePhase.CLOSURE, LifecyclePhase.BLOCKED}
    )
    assert TRANSITIONS[LifecyclePhase.SECURITY_REVIEW] == frozenset(
        {LifecyclePhase.CODE_REVIEW, LifecyclePhase.BLOCKED}
    )
    assert TRANSITIONS[LifecyclePhase.CODE_REVIEW] == frozenset(
        {LifecyclePhase.CLOSURE, LifecyclePhase.BLOCKED}
    )


@pytest.mark.parametrize(
    ("name", "build_fn", "assert_fn"),
    [
        (
            "lifecycle_run",
            lambda: LifecycleRun(
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
            ),
            lambda obj, data: (
                data["phase"] == "implementation"
                and data["status"] == "blocked"
                and data["expected_artifacts"] == ["handoff"]
                and data["blocked"]
                == {
                    "reason": "push_blocked",
                    "blocked_at_step": "push_readiness",
                    "resume_token": "resume-1",
                    "operator_command": "git push",
                    "detail": {"branch": "feature/v0.1.15"},
                }
                and LifecycleRun.from_dict(data) == obj
            ),
        ),
        (
            "gate_requirement",
            lambda: GateRequirement(
                evidence_kind=GateEvidenceKind.HANDOFF,
                required_agent="security-reviewer",
                required_verdict=GateVerdict.APPROVED,
                release_id="v0.1.15",
                commit_sha="abc123",
                task_group="T-015-01",
                max_unresolved_severity="MEDIUM",
            ),
            lambda obj, data: (
                data
                == {
                    "evidence_kind": "handoff",
                    "required_agent": "security-reviewer",
                    "required_verdict": "APPROVED",
                    "release_id": "v0.1.15",
                    "commit_sha": "abc123",
                    "task_group": "T-015-01",
                    "max_unresolved_severity": "MEDIUM",
                }
                and GateRequirement.from_dict(data) == obj
            ),
        ),
        (
            "gate_evidence",
            lambda: GateEvidence(
                evidence_kind=GateEvidenceKind.HANDOFF,
                source=".dadaia/handoff/dadaia-workspace/review.handoff.json",
                context="dadaia-workspace",
                release_id="v0.1.15",
                agent="qa-engineer",
                verdict=GateVerdict.APPROVED,
                commit_sha="abc123",
                task_group="T-015-01",
                metrics={"tests_passed": "8"},
            ),
            lambda obj, data: (
                data
                == {
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
                and GateEvidence.from_dict(data) == obj
            ),
        ),
        (
            "agent_run_request",
            lambda: AgentRunRequest(
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
            ),
            lambda obj, data: (
                data["runtime"] == "codex_exec"
                and data["allowed_paths"] == ["dadaia_workspace/core/models/lifecycle.py"]
                and data["required_evidence"] == ["test_result", "dirty_diff"]
                and AgentRunRequest.from_dict(data) == obj
            ),
        ),
        (
            "agent_run_result",
            lambda: AgentRunResult(
                status=AgentRunStatus.SUCCEEDED,
                summary="Implemented lifecycle models.",
                artifact_refs=("tests/unit/core/test_lifecycle_models.py",),
                structured_output={"tests": "passed"},
            ),
            lambda obj, data: (
                data["status"] == "succeeded"
                and data["structured_output"] == {"tests": "passed"}
                and AgentRunResult.from_dict(data) == obj
            ),
        ),
    ],
)
def test_round_trip_table(name: str, build_fn: object, assert_fn: object) -> None:
    obj = build_fn()  # type: ignore[operator]
    data = obj.to_dict()
    assert assert_fn(obj, data)  # type: ignore[operator]


def test_agent_run_request_resolved_model_carried_defaults_none_and_back_compat() -> None:
    from dadaia_workspace.core.models.workflow_execution import (
        PolicySource,
        ResolvedModelConfig,
    )

    # Carried.
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

    # Defaults None.
    plain = AgentRunRequest(
        role="r", prompt="p", runtime=AgentRuntimeKind.FAKE, context="c", release_id="v0.1.28"
    )
    assert plain.resolved_model is None
    assert plain.to_dict()["resolved_model"] is None

    # Legacy (no 'resolved_model' key) still loads.
    legacy: dict[str, object] = {
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
    restored = AgentRunRequest.from_dict(legacy)
    assert restored.resolved_model is None


def test_lifecycle_run_workflow_policy_snapshot_carried_and_back_compat() -> None:
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

    # M1: an old v1 record (no 'workflow_policy' key) still loads.
    legacy: dict[str, object] = {
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
    restored = LifecycleRun.from_dict(legacy)
    assert restored.workflow_policy is None
