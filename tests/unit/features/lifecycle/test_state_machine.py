"""Unit tests for the pure lifecycle state machine."""

from __future__ import annotations

from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    GateEvidence,
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.state_machine import (
    LifecycleStateMachine,
    TransitionInput,
)


def _run(
    *,
    phase: LifecyclePhase = LifecyclePhase.IMPLEMENTATION,
    status: LifecycleRunStatus = LifecycleRunStatus.RUNNING,
    blocked: BlockedState | None = None,
) -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="implement",
        phase=phase,
        status=status,
        current_step="implementation",
        idempotency_key="resume-1",
        blocked=blocked,
    )


def test_accepts_legal_transition_with_structured_evidence() -> None:
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
        commit_sha="abc123",
        task_group="T-015-08",
    )
    evidence = GateEvidence(
        evidence_kind=GateEvidenceKind.HANDOFF,
        source=".dadaia/handoff/dadaia-workspace/qa.handoff.json",
        context="dadaia-workspace",
        release_id="v0.1.15",
        agent="qa-engineer",
        verdict=GateVerdict.APPROVED,
        commit_sha="abc123",
        task_group="T-015-08",
    )

    decision = LifecycleStateMachine().transition(
        _run(),
        TransitionInput(
            target_phase=LifecyclePhase.QA_REVIEW,
            evidence=(evidence,),
            requirements=(requirement,),
            current_step="qa-review",
        ),
    )

    assert decision.accepted is True
    assert decision.reason == "transition accepted"
    assert decision.run.phase is LifecyclePhase.QA_REVIEW
    assert decision.run.status is LifecycleRunStatus.RUNNING
    assert decision.run.current_step == "qa-review"
    assert decision.run.blocked is None


def test_rejects_illegal_transition_without_mutating_run() -> None:
    run = _run()

    decision = LifecycleStateMachine().transition(
        run,
        TransitionInput(target_phase=LifecyclePhase.CLOSURE),
    )

    assert decision.accepted is False
    assert decision.run == run
    assert decision.reason == "illegal transition: implementation -> closure"


def test_missing_structured_evidence_blocks_transition() -> None:
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
    )

    decision = LifecycleStateMachine().transition(
        _run(),
        TransitionInput(
            target_phase=LifecyclePhase.QA_REVIEW,
            requirements=(requirement,),
        ),
    )

    assert decision.accepted is False
    assert decision.missing_requirements == (requirement,)
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.status is LifecycleRunStatus.BLOCKED
    assert decision.run.blocked is not None
    assert decision.run.blocked.reason == "missing required transition evidence"
    assert decision.run.blocked.resume_token == "resume-1"
    assert decision.run.blocked.detail["target_phase"] == "qa_review"


def test_accepts_explicit_blocked_transition_with_blocked_state() -> None:
    blocked = BlockedState(
        reason="qa handoff missing",
        blocked_at_step="qa-review",
        resume_token="resume-qa",
        operator_command="dadaia lifecycle resume run-1",
    )

    decision = LifecycleStateMachine().transition(
        _run(),
        TransitionInput(
            target_phase=LifecyclePhase.BLOCKED,
            blocked_state=blocked,
            current_step="qa-review",
        ),
    )

    assert decision.accepted is True
    assert decision.reason == "transition blocked"
    assert decision.run.phase is LifecyclePhase.BLOCKED
    assert decision.run.status is LifecycleRunStatus.BLOCKED
    assert decision.run.current_step == "qa-review"
    assert decision.run.blocked == blocked


def test_resume_requires_matching_token() -> None:
    blocked = BlockedState(
        reason="security review pending",
        blocked_at_step="security-review",
        resume_token="resume-security",
    )
    run = _run(
        phase=LifecyclePhase.BLOCKED,
        status=LifecycleRunStatus.BLOCKED,
        blocked=blocked,
    )

    rejected = LifecycleStateMachine().transition(
        run,
        TransitionInput(
            target_phase=LifecyclePhase.SECURITY_REVIEW,
            resume_token="wrong",
        ),
    )
    accepted = LifecycleStateMachine().transition(
        run,
        TransitionInput(
            target_phase=LifecyclePhase.SECURITY_REVIEW,
            resume_token="resume-security",
            current_step="security-review",
        ),
    )

    assert rejected.accepted is False
    assert rejected.run == run
    assert rejected.reason == "resume token mismatch"
    assert accepted.accepted is True
    assert accepted.run.phase is LifecyclePhase.SECURITY_REVIEW
    assert accepted.run.status is LifecycleRunStatus.RUNNING
    assert accepted.run.blocked is None


# --- v0.1.57 FR5 / A5 — TransitionDecision.advanced single-sources the accept predicate --


def test_advanced_is_false_on_illegal_transition() -> None:
    """AC-8 root: an illegal transition returns the run UNCHANGED (blocked is None) but
    was NOT accepted — ``advanced`` is False while ``run.blocked is None`` alone is True."""
    # QA_REVIEW -> IMPLEMENTATION is illegal post-v0.1.56 FR4.
    decision = LifecycleStateMachine().transition(
        _run(phase=LifecyclePhase.QA_REVIEW),
        TransitionInput(target_phase=LifecyclePhase.IMPLEMENTATION),
    )
    assert decision.accepted is False
    assert decision.run.blocked is None
    assert decision.advanced is False


def test_advanced_is_false_on_legal_block() -> None:
    """A legal transition INTO BLOCKED is ``accepted=True`` but did not advance the phase."""
    decision = LifecycleStateMachine().transition(
        _run(phase=LifecyclePhase.QA_REVIEW),
        TransitionInput(
            target_phase=LifecyclePhase.BLOCKED,
            blocked_state=BlockedState(reason="held", blocked_at_step="qa-review"),
        ),
    )
    assert decision.accepted is True
    assert decision.run.blocked is not None
    assert decision.advanced is False


def test_advanced_is_false_on_missing_requirement_block() -> None:
    """A missing-evidence block is ``accepted=False`` with a blocked run — not advanced."""
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
    )
    decision = LifecycleStateMachine().transition(
        _run(),
        TransitionInput(
            target_phase=LifecyclePhase.QA_REVIEW,
            requirements=(requirement,),
        ),
    )
    assert decision.accepted is False
    assert decision.run.blocked is not None
    assert decision.advanced is False


def test_advanced_is_true_on_legal_success() -> None:
    """A legal transition with no unmet requirement advances — ``advanced`` is True."""
    decision = LifecycleStateMachine().transition(
        _run(),
        TransitionInput(target_phase=LifecyclePhase.QA_REVIEW, current_step="qa-review"),
    )
    assert decision.accepted is True
    assert decision.run.blocked is None
    assert decision.advanced is True
