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
    ) -> PhaseWorkflowResult:
        step = current_step or target_phase.value
        run = LifecycleRun(
            run_id=run_id,
            context=scope.context,
            release_id=scope.release_id,
            command=command,
            phase=from_phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=step,
            idempotency_key=run_id,
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
