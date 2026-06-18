"""Pure lifecycle state machine for deterministic workflow transitions."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    GateEvidence,
    GateRequirement,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
    is_legal_transition,
)


@dataclass(frozen=True)
class TransitionInput:
    """Structured inputs used to evaluate a lifecycle phase transition."""

    target_phase: LifecyclePhase
    evidence: tuple[GateEvidence, ...] = ()
    requirements: tuple[GateRequirement, ...] = ()
    blocked_state: BlockedState | None = None
    resume_token: str | None = None
    current_step: str | None = None


@dataclass(frozen=True)
class TransitionDecision:
    """Decision returned by the lifecycle state machine."""

    accepted: bool
    run: LifecycleRun
    reason: str
    missing_requirements: tuple[GateRequirement, ...] = field(default_factory=tuple)


class LifecycleStateMachine:
    """Evaluate lifecycle transitions without filesystem, CLI, or LLM dependencies."""

    def transition(
        self,
        run: LifecycleRun,
        transition_input: TransitionInput,
    ) -> TransitionDecision:
        target = transition_input.target_phase
        if not is_legal_transition(run.phase, target):
            return TransitionDecision(
                accepted=False,
                run=run,
                reason=f"illegal transition: {run.phase.value} -> {target.value}",
            )

        if run.phase is LifecyclePhase.BLOCKED:
            resume_decision = self._resume(run, transition_input)
            if resume_decision is not None:
                return resume_decision

        if target is LifecyclePhase.BLOCKED:
            return self._block(run, transition_input)

        missing = self._missing_requirements(run, transition_input)
        if missing:
            blocked = BlockedState(
                reason="missing required transition evidence",
                blocked_at_step=transition_input.current_step or run.current_step,
                resume_token=run.idempotency_key,
                detail={
                    "source_phase": run.phase.value,
                    "target_phase": target.value,
                    "missing": ",".join(requirement.evidence_kind.value for requirement in missing),
                },
            )
            return TransitionDecision(
                accepted=False,
                run=replace(
                    run,
                    phase=LifecyclePhase.BLOCKED,
                    status=LifecycleRunStatus.BLOCKED,
                    blocked=blocked,
                ),
                reason=blocked.reason,
                missing_requirements=missing,
            )

        return TransitionDecision(
            accepted=True,
            run=replace(
                run,
                phase=target,
                status=LifecycleRunStatus.RUNNING,
                current_step=transition_input.current_step or target.value,
                blocked=None,
            ),
            reason="transition accepted",
        )

    def _resume(
        self,
        run: LifecycleRun,
        transition_input: TransitionInput,
    ) -> TransitionDecision | None:
        blocked = run.blocked
        if blocked is None:
            return TransitionDecision(
                accepted=False,
                run=run,
                reason="blocked run has no blocked state",
            )
        if (
            blocked.resume_token is not None
            and transition_input.resume_token != blocked.resume_token
        ):
            return TransitionDecision(
                accepted=False,
                run=run,
                reason="resume token mismatch",
            )
        return None

    def _block(
        self,
        run: LifecycleRun,
        transition_input: TransitionInput,
    ) -> TransitionDecision:
        if transition_input.blocked_state is None:
            return TransitionDecision(
                accepted=False,
                run=run,
                reason="blocked transition requires blocked_state",
            )
        return TransitionDecision(
            accepted=True,
            run=replace(
                run,
                phase=LifecyclePhase.BLOCKED,
                status=LifecycleRunStatus.BLOCKED,
                current_step=transition_input.current_step or run.current_step,
                blocked=transition_input.blocked_state,
            ),
            reason="transition blocked",
        )

    def _missing_requirements(
        self,
        run: LifecycleRun,
        transition_input: TransitionInput,
    ) -> tuple[GateRequirement, ...]:
        return tuple(
            requirement
            for requirement in transition_input.requirements
            if not self._has_matching_evidence(run, requirement, transition_input.evidence)
        )

    def _has_matching_evidence(
        self,
        run: LifecycleRun,
        requirement: GateRequirement,
        evidence_items: tuple[GateEvidence, ...],
    ) -> bool:
        for evidence in evidence_items:
            if evidence.context != run.context or evidence.release_id != run.release_id:
                continue
            if evidence.evidence_kind is not requirement.evidence_kind:
                continue
            if (
                requirement.required_agent is not None
                and evidence.agent != requirement.required_agent
            ):
                continue
            if (
                requirement.required_verdict is not None
                and evidence.verdict is not requirement.required_verdict
            ):
                continue
            if requirement.release_id is not None and evidence.release_id != requirement.release_id:
                continue
            if requirement.commit_sha is not None and evidence.commit_sha != requirement.commit_sha:
                continue
            if requirement.task_group is not None and evidence.task_group != requirement.task_group:
                continue
            return True
        return False
