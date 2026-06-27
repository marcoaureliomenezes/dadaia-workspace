"""Single-step lifecycle phase workflow — the first real engine-driven verb path.

This is the first procedural workflow a ``dadaia lifecycle`` verb actually executes
(versus the ``unavailable_workflow`` stubs). It threads one bounded worker step
end-to-end: a scoped prompt → the per-step-selected harness (an injected
``AgentRuntimePort`` chosen by ``container.build_agent_runtime``) → the typed gate +
legal transition (``LifecycleAgentRunner`` + ``LifecycleStateMachine``) → a persisted,
resumable run record (``LifecycleRunStore``). The state machine stays provider-agnostic;
the harness is selectable/mixable per step purely by which adapter is injected.
"""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    GateRequirement,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.core.models.workflow_execution import WorkflowPolicySnapshot
from dadaia_workspace.core.protocols.agent_runtime import AgentRuntimePort
from dadaia_workspace.core.protocols.lifecycle_run_store import LifecycleRunStore
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptScope,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine

#: The review phases (v0.1.31 / C1). A phase step targeting one of these is a REVIEW step,
#: so its worker output is gated on ``verdict == APPROVED`` (L1). A step targeting any other
#: phase (e.g. a create/implementation phase) is a create step and is not verdict-gated.
_REVIEW_PHASES: frozenset[LifecyclePhase] = frozenset(
    {
        LifecyclePhase.QA_REVIEW,
        LifecyclePhase.SECURITY_REVIEW,
        LifecyclePhase.CODE_REVIEW,
    }
)


def is_review_phase(phase: LifecyclePhase) -> bool:
    """Whether a target phase is a review/gate phase (verdict-gated) vs a create phase.

    The single source of the review-vs-create distinction for phase-targeting callers —
    used by :meth:`LifecyclePhaseWorkflow.run` (to set ``is_review`` on the runner input)
    and by the CLI single-step verbs (to make the worker prompt step-kind-aware: review
    steps are instructed to emit a verdict; create steps are not — v0.1.32 D-2/L1).
    """
    return phase in _REVIEW_PHASES


@dataclass(frozen=True)
class PhaseWorkflowResult:
    """Typed outcome of one engine-driven phase step."""

    run_id: str
    accepted: bool
    phase: LifecyclePhase
    runtime_kind: AgentRuntimeKind
    blocked: BlockedState | None = None


class LifecyclePhaseWorkflow:
    """Run one bounded worker step through the engine on a selectable harness."""

    def __init__(
        self,
        *,
        runtime: AgentRuntimePort,
        run_store: LifecycleRunStore,
        prompt_builder: LifecyclePromptBuilder | None = None,
        state_machine: LifecycleStateMachine | None = None,
    ) -> None:
        self._runtime = runtime
        self._run_store = run_store
        self._prompt_builder = prompt_builder or LifecyclePromptBuilder()
        self._state_machine = state_machine or LifecycleStateMachine()

    def run(
        self,
        *,
        run_id: str,
        command: str,
        from_phase: LifecyclePhase,
        target_phase: LifecyclePhase,
        scope: PromptScope,
        requirements: tuple[GateRequirement, ...] = (),
        current_step: str | None = None,
        policy_snapshot: WorkflowPolicySnapshot | None = None,
        is_review: bool | None = None,
    ) -> PhaseWorkflowResult:
        step = current_step or target_phase.value
        # The verdict gate is review-only (v0.1.31 / L1). A step targeting a review phase
        # (QA/SECURITY/CODE) is a review step; otherwise it is a create step. The caller may
        # override explicitly via ``is_review``; default derives it from the target phase.
        review = is_review if is_review is not None else is_review_phase(target_phase)
        # The resolved governance snapshot (T-28-A-07 / LAW 7) is frozen onto the run before
        # the worker call; the resolved per-step model reaches the adapter via the scope's
        # ``resolved_model``. ``dataclasses.replace`` in the runner/state-machine preserves
        # the snapshot through the transition.
        run = LifecycleRun(
            run_id=run_id,
            context=scope.context,
            release_id=scope.release_id,
            command=command,
            phase=from_phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=step,
            idempotency_key=run_id,
            workflow_policy=policy_snapshot,
        )
        self._run_store.save(run)

        built = self._prompt_builder.build(scope, runtime=self._runtime.runtime_kind())
        runner = LifecycleAgentRunner(
            runtime=self._runtime,
            state_machine=self._state_machine,
        )
        decision = runner.run(
            run,
            AgentRunnerInput(
                request=built.request,
                target_phase=target_phase,
                requirements=requirements,
                current_step=step,
                is_review=review,
            ),
        )
        self._run_store.save(decision.run)
        # `decision.accepted` is True even for a (legal) transition INTO BLOCKED;
        # the gate's pass/fail signal is whether the run carries a blocked state.
        return PhaseWorkflowResult(
            run_id=run_id,
            accepted=decision.run.blocked is None,
            phase=decision.run.phase,
            runtime_kind=self._runtime.runtime_kind(),
            blocked=decision.run.blocked,
        )
