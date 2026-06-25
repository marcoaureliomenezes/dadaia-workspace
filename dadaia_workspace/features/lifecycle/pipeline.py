"""Multi-step lifecycle pipeline — one run threaded through several phases, each on a
per-step-selectable harness.

This is the multi-harness vision in one object: a single ``LifecycleRun`` advances through
an ordered sequence of bounded worker steps (e.g. implement → qa → security → code), and
each step runs on whatever harness that step selects (claude to implement, codex to review,
...). The state machine stays provider-agnostic; mixing harnesses is purely a per-step
adapter swap via the injected runtime factory. The pipeline stops at the first blocked gate
and persists progress at every step (resumable).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    GateEvidenceKind,
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
    PromptPrefix,
    PromptScope,
)
from dadaia_workspace.features.lifecycle.state_machine import LifecycleStateMachine

#: ``kind -> adapter`` — injected so tests can supply fakes per harness.
RuntimeFactory = Callable[[AgentRuntimeKind], AgentRuntimePort]


@dataclass(frozen=True)
class PipelineStep:
    """One bounded step in a lifecycle pipeline, bound to a chosen harness."""

    label: str
    role: str
    from_phase: LifecyclePhase
    target_phase: LifecyclePhase
    runtime_kind: AgentRuntimeKind
    requirements: tuple[GateRequirement, ...] = ()
    model_profile: str | None = None


@dataclass(frozen=True)
class PipelineStepResult:
    label: str
    runtime_kind: AgentRuntimeKind
    accepted: bool
    phase: LifecyclePhase
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[PipelineStepResult, ...] = ()
    blocked: BlockedState | None = None


class LifecyclePipeline:
    """Thread one run through an ordered, per-step-harness-selectable phase sequence."""

    def __init__(
        self,
        *,
        context: str,
        release_id: str,
        run_store: LifecycleRunStore,
        runtime_factory: RuntimeFactory,
        prefix: PromptPrefix | None = None,
        prompt_builder: LifecyclePromptBuilder | None = None,
        state_machine: LifecycleStateMachine | None = None,
    ) -> None:
        self._context = context
        self._release_id = release_id
        self._run_store = run_store
        self._runtime_factory = runtime_factory
        self._prefix = prefix
        self._prompt_builder = prompt_builder or LifecyclePromptBuilder()
        self._state_machine = state_machine or LifecycleStateMachine()

    def run(self, run_id: str, steps: tuple[PipelineStep, ...]) -> PipelineResult:
        if not steps:
            raise ValueError("pipeline requires at least one step")
        run = LifecycleRun(
            run_id=run_id,
            context=self._context,
            release_id=self._release_id,
            command="pipeline",
            phase=steps[0].from_phase,
            status=LifecycleRunStatus.RUNNING,
            current_step=steps[0].label,
            idempotency_key=run_id,
        )
        self._run_store.save(run)

        results: list[PipelineStepResult] = []
        for step in steps:
            runtime = self._runtime_factory(step.runtime_kind)
            built = self._prompt_builder.build(
                self._scope(step, run_id),
                runtime=runtime.runtime_kind(),
                prefix=self._prefix,
            )
            runner = LifecycleAgentRunner(runtime=runtime, state_machine=self._state_machine)
            decision = runner.run(
                run,
                AgentRunnerInput(
                    request=built.request,
                    target_phase=step.target_phase,
                    requirements=step.requirements,
                    current_step=step.label,
                ),
            )
            run = decision.run
            self._run_store.save(run)
            accepted = run.blocked is None
            results.append(
                PipelineStepResult(
                    label=step.label,
                    runtime_kind=step.runtime_kind,
                    accepted=accepted,
                    phase=run.phase,
                    blocked=run.blocked,
                )
            )
            if not accepted:
                return PipelineResult(
                    run_id=run_id,
                    completed=False,
                    final_phase=run.phase,
                    steps=tuple(results),
                    blocked=run.blocked,
                )
        return PipelineResult(
            run_id=run_id,
            completed=True,
            final_phase=run.phase,
            steps=tuple(results),
        )

    def _scope(self, step: PipelineStep, run_id: str) -> PromptScope:
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=(
                f"Run the {step.label} step for release {self._release_id} in context "
                f"{self._context}. Emit a handoff whose structured_output.verdict is APPROVED "
                "or REJECTED, with an artifact_ref pointing at the handoff document."
            ),
            allowed_paths=(f".dadaia/handoff/{self._context}/**",),
            required_evidence=(GateEvidenceKind.HANDOFF,),
            model_profile=step.model_profile,
        )


def implementation_ladder(default_kind: AgentRuntimeKind) -> tuple[PipelineStep, ...]:
    """The canonical release-implementation pipeline: implement → qa → security → code.

    Each step defaults to ``default_kind`` (override per step for harness mixing) and carries
    a step model tier (EPIC D11): implementation runs the standard tier, reviews/judgments run
    the deep tier — inverting the all-steps-on-the-top-tier tax.
    """
    return (
        PipelineStep(
            label="implement",
            role="software-engineer",
            from_phase=LifecyclePhase.IMPLEMENTATION,
            target_phase=LifecyclePhase.QA_REVIEW,
            runtime_kind=default_kind,
            model_profile="sonnet",
        ),
        PipelineStep(
            label="review_qa",
            role="qa-engineer",
            from_phase=LifecyclePhase.QA_REVIEW,
            target_phase=LifecyclePhase.SECURITY_REVIEW,
            runtime_kind=default_kind,
            model_profile="opus",
        ),
        PipelineStep(
            label="review_security",
            role="security-reviewer",
            from_phase=LifecyclePhase.SECURITY_REVIEW,
            target_phase=LifecyclePhase.CODE_REVIEW,
            runtime_kind=default_kind,
            model_profile="opus",
        ),
        PipelineStep(
            label="review_code",
            role="code-reviewer",
            from_phase=LifecyclePhase.CODE_REVIEW,
            target_phase=LifecyclePhase.CLOSURE,
            runtime_kind=default_kind,
            model_profile="opus",
        ),
    )


# Re-exported for callers assembling custom ladders.
__all__ = [
    "LifecyclePipeline",
    "PipelineResult",
    "PipelineStep",
    "PipelineStepResult",
    "RuntimeFactory",
    "implementation_ladder",
]
