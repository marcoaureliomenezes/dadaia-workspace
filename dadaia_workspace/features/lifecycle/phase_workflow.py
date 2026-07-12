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

from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

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
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort
from dadaia_workspace.features.lifecycle.agent_runner import (
    AgentRunnerInput,
    LifecycleAgentRunner,
)
from dadaia_workspace.features.lifecycle.prompt_builder import (
    LifecyclePromptBuilder,
    PromptScope,
)
from dadaia_workspace.features.lifecycle.role_atoms import inject_role_atoms
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
        specs_dir_resolver: Callable[[str], Path | None] | None = None,
        runtime_files: RuntimeFilePort | None = None,
        artifact_root: Path | None = None,
    ) -> None:
        self._runtime = runtime
        self._run_store = run_store
        self._prompt_builder = prompt_builder or LifecyclePromptBuilder()
        self._state_machine = state_machine or LifecycleStateMachine()
        # Resolve a context name → its ``specs/`` tree (v0.1.57 FR2 / A1). Injected by
        # ``build_lifecycle_phase_workflow`` (closing over ``workspace_root``) because the
        # context is only known at ``run()`` time from ``scope.context``. When ``None`` (a
        # fixture-constructed workflow) no role atom is injected.
        self._specs_dir_resolver = specs_dir_resolver
        # v0.1.78 T-D / FR-D: additive-optional run-artifact writer threaded to the
        # ``LifecycleAgentRunner`` this workflow constructs (see ``pipeline.py`` twin).
        self._runtime_files = runtime_files
        # Bug gate-accepts-phantom-artifact-evidence: when wired, declared artifact refs
        # must EXIST under this root or the step BLOCKs.
        self._artifact_root = artifact_root

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

        # FR2 (A1): resolve specs_dir from the run's context, append the role's mapped atom(s)
        # to the scope prompt, and record the atom refs on the run before the worker call —
        # the state machine's ``replace``-based transition preserves them onto ``decision.run``.
        specs_dir = (
            self._specs_dir_resolver(scope.context)
            if self._specs_dir_resolver is not None
            else None
        )
        run, injected_prompt = inject_role_atoms(
            run=run,
            step_label=step,
            role=scope.role,
            specs_dir=specs_dir,
            prompt=scope.prompt,
        )
        scope = replace(scope, prompt=injected_prompt)

        built = self._prompt_builder.build(scope, runtime=self._runtime.runtime_kind())
        runner = LifecycleAgentRunner(
            runtime=self._runtime,
            state_machine=self._state_machine,
            runtime_files=self._runtime_files,
            artifact_root=self._artifact_root,
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
        # FR5 (A5): the accept signal is the state machine's DUAL-signal ``advanced``
        # contract (``accepted and run.blocked is None``). The prior ``run.blocked is None``
        # reasoning missed the ILLEGAL-transition case — an illegal transition returns the
        # run unchanged (``blocked is None``) yet never advanced the phase, so the old
        # single-signal predicate wrongly reported ``accepted=True``.
        return PhaseWorkflowResult(
            run_id=run_id,
            accepted=decision.advanced,
            phase=decision.run.phase,
            runtime_kind=self._runtime.runtime_kind(),
            blocked=decision.run.blocked,
        )
