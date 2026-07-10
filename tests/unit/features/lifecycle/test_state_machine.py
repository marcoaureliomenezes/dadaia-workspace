"""Unit tests for the pure lifecycle state machine.

CRITICAL: transition legality + the ``advanced`` predicate (root of the v0.1.57 accepted
bug — see the FR5/A5 param table below).
"""

from __future__ import annotations

import pytest

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
    TransitionDecision,
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


# --- ① block/reject param: illegal-no-mutation / missing-evidence-blocks / explicit-blocked ---


def _illegal_case() -> tuple[LifecycleRun, TransitionInput]:
    return _run(), TransitionInput(target_phase=LifecyclePhase.CLOSURE)


def _missing_evidence_case() -> tuple[LifecycleRun, TransitionInput]:
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
    )
    return _run(), TransitionInput(
        target_phase=LifecyclePhase.QA_REVIEW,
        requirements=(requirement,),
    )


def _explicit_blocked_case() -> tuple[LifecycleRun, TransitionInput]:
    blocked = BlockedState(
        reason="qa handoff missing",
        blocked_at_step="qa-review",
        resume_token="resume-qa",
        operator_command="dadaia lifecycle resume run-1",
    )
    return _run(), TransitionInput(
        target_phase=LifecyclePhase.BLOCKED,
        blocked_state=blocked,
        current_step="qa-review",
    )


@pytest.mark.parametrize(
    "case_id,build,expect_accepted",
    [
        ("illegal-no-mutation", _illegal_case, False),
        ("missing-evidence-blocks", _missing_evidence_case, False),
        ("explicit-blocked-accepted", _explicit_blocked_case, True),
    ],
    ids=["illegal-no-mutation", "missing-evidence-blocks", "explicit-blocked-accepted"],
)
def test_block_and_reject_matrix(case_id: str, build, expect_accepted: bool) -> None:
    run, transition_input = build()
    decision: TransitionDecision = LifecycleStateMachine().transition(run, transition_input)

    assert decision.accepted is expect_accepted

    if case_id == "illegal-no-mutation":
        assert decision.run == run
        assert decision.reason == "illegal transition: implementation -> closure"
    elif case_id == "missing-evidence-blocks":
        assert decision.missing_requirements == transition_input.requirements
        assert decision.run.phase is LifecyclePhase.BLOCKED
        assert decision.run.status is LifecycleRunStatus.BLOCKED
        assert decision.run.blocked is not None
        assert decision.run.blocked.reason == "missing required transition evidence"
        assert decision.run.blocked.resume_token == "resume-1"
        assert decision.run.blocked.detail["target_phase"] == "qa_review"
    else:  # explicit-blocked-accepted
        assert decision.reason == "transition blocked"
        assert decision.run.phase is LifecyclePhase.BLOCKED
        assert decision.run.status is LifecycleRunStatus.BLOCKED
        assert decision.run.current_step == "qa-review"
        assert decision.run.blocked == transition_input.blocked_state


# --- ② `advanced` dual-signal param (v0.1.57 FR5 / A5) --------------------------------


def test_advanced_dual_signal_matrix() -> None:
    """``TransitionDecision.advanced`` single-sources the accept predicate: an illegal
    transition, a legal transition INTO BLOCKED, and a missing-requirement block are all
    ``advanced is False`` (even though ``accepted`` and ``run.blocked`` differ per case) —
    only a legal transition with no unmet requirement is ``advanced is True``."""
    # illegal: accepted=False, run.blocked is None, but NOT advanced.
    illegal = LifecycleStateMachine().transition(
        _run(phase=LifecyclePhase.QA_REVIEW),
        TransitionInput(target_phase=LifecyclePhase.IMPLEMENTATION),
    )
    assert illegal.accepted is False
    assert illegal.run.blocked is None
    assert illegal.advanced is False

    # legal block: accepted=True, run.blocked is set, but did not advance the phase.
    legal_block = LifecycleStateMachine().transition(
        _run(phase=LifecyclePhase.QA_REVIEW),
        TransitionInput(
            target_phase=LifecyclePhase.BLOCKED,
            blocked_state=BlockedState(reason="held", blocked_at_step="qa-review"),
        ),
    )
    assert legal_block.accepted is True
    assert legal_block.run.blocked is not None
    assert legal_block.advanced is False

    # missing requirement: accepted=False, run.blocked is set, not advanced.
    requirement = GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
    )
    missing_req = LifecycleStateMachine().transition(
        _run(),
        TransitionInput(target_phase=LifecyclePhase.QA_REVIEW, requirements=(requirement,)),
    )
    assert missing_req.accepted is False
    assert missing_req.run.blocked is not None
    assert missing_req.advanced is False

    # legal success: accepted=True, run.blocked is None, and advanced.
    success = LifecycleStateMachine().transition(
        _run(),
        TransitionInput(target_phase=LifecyclePhase.QA_REVIEW, current_step="qa-review"),
    )
    assert success.accepted is True
    assert success.run.blocked is None
    assert success.advanced is True
