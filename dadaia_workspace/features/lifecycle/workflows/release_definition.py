"""Release-definition workflow body — the SPEC §6.1 sequence on fragments + gates (WS-5).

The keystone of the v0.1.24 two-layer redesign: the release-definition workflow runs as a
Python-owned procedure rather than a single generic ``"Run the {label} step"`` prompt. Python
owns step **order** and gate **decisions**; each model step's prompt is assembled from its
fragment bundle + the dynamically selected context (bounded by ``max_context_policy``) + the
output schema + the discrete ``(harness, model)`` for the step.

As of v0.1.57 FR1 the assembly + gate machinery lives once in
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate.FragmentGateWorkflow`
(the ONE prompt-assembly seam shared with ``audit`` / ``research`` / ``bug_report``). This body
is now a thin subclass that declares the five divergence hooks — the ``release_definition``
command, the RELEASE_DEFINITION initial phase, the terminal transition to IMPLEMENTATION, and
the ``ReleaseStep`` / ``ReleaseDefinitionResult`` dataclass types — and keeps its module-global
``_SEQUENCE`` (imported by the fragment-coverage / loader / persona guardrail suites).

**Python owns the gates.** Each review step's structured verdict (APPROVED / REJECTED) is read
by Python; a REJECTED or missing-evidence review BLOCKS advancement. The terminal
``definition_commit_gate`` is a Python step with **no model** — it advances the release to
IMPLEMENTATION only when every prior gate passed and the workflow-step handoff graph is whole.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    LifecyclePhase,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig
from dadaia_workspace.features.lifecycle.workflows._fragment_gate import (
    FragmentGateWorkflow,
    _StepOutcome,
)


@dataclass(frozen=True)
class ReleaseStep:
    """One step of the §6.1 release-definition sequence.

    A model step names its fragment id (``workflow.step``), the shared fragment ids it cites,
    the runtime kind it runs on, and whether it is a **review** (a gate whose verdict can
    REJECT and thereby BLOCK advancement). The terminal Python gate carries ``fragment_id=None``
    and ``runtime_kind=None`` — it runs no model.
    """

    label: str
    role: str
    fragment_id: str | None
    shared_fragment_ids: tuple[str, ...] = ()
    is_review: bool = False
    runtime_kind: AgentRuntimeKind | None = None
    # Workflow-step handoff data plane edges (v0.1.30 Item 5 / T-30-D-05). ``produces`` is the
    # named payload schema this step writes (None ⇒ no ledger payload); ``consumes`` is the
    # tuple of upstream producer-step labels this step resolves by exact (run id, producer
    # step, attempt) BEFORE running (A19/A20/A25). Inert unless a resolver is wired.
    produces: str | None = None
    consumes: tuple[str, ...] = ()
    # Governance-resolved concrete model for this step (v0.1.56 / FR1). ``apply_resolved_policy``
    # threads the resolved snapshot model here; the base ``_scope`` forwards it to the request so
    # the adapter runs the policy-selected model. Additive-optional, mirroring ``PipelineStep``.
    resolved_model: ResolvedModelConfig | None = None
    model_profile: str | None = None


@dataclass(frozen=True)
class ReleaseStepResult:
    """Typed outcome of one release-definition step."""

    label: str
    accepted: bool
    is_gate: bool
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class ReleaseDefinitionResult:
    """Typed outcome of the whole release-definition sequence."""

    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[ReleaseStepResult, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The §6.1 release-definition sequence. ``runtime_kind=None`` on a model step means the
#: workflow's default harness is used; the terminal gate carries no fragment and no model.
#: Fragment ids match the shipped ``release_definition/*`` bundle; ``spec_arch_review`` maps to
#: ``release_definition.spec_review_architecture``.
_SEQUENCE: tuple[ReleaseStep, ...] = (
    ReleaseStep(
        label="release_scope",
        role="product-engineer",
        fragment_id="release_definition.release_scope",
        shared_fragment_ids=(
            "shared.grill_questionnaire",
            "shared.output_handoff",
            "shared.anti_slop",
        ),
        produces="release-scope-handoff-v1",
    ),
    ReleaseStep(
        label="spec_create",
        role="product-engineer",
        fragment_id="release_definition.spec_create",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        consumes=("release_scope",),
    ),
    ReleaseStep(
        label="spec_arch_review",
        role="software-architect",
        fragment_id="release_definition.spec_review_architecture",
        shared_fragment_ids=(
            "shared.anti_slop",
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="spec-review-handoff-v1",
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="spec_qa_review",
        role="qa-engineer",
        fragment_id="release_definition.spec_review_qa",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="spec-review-handoff-v1",
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="plan_create",
        role="product-engineer",
        fragment_id="release_definition.plan_create",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        consumes=("spec_create",),
    ),
    ReleaseStep(
        label="plan_review",
        role="qa-engineer, software-architect",
        fragment_id="release_definition.plan_review",
        shared_fragment_ids=(
            "shared.anti_slop",
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="plan-review-handoff-v1",
        consumes=("plan_create",),
    ),
    ReleaseStep(
        label="tasks_create",
        role="product-engineer",
        fragment_id="release_definition.tasks_create",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.anti_slop",
            "shared.memory_selection",
        ),
        produces="generic-step-handoff-v1",
        consumes=("plan_create",),
    ),
    ReleaseStep(
        label="tasks_implementability_review",
        role="software-engineer",
        fragment_id="release_definition.tasks_review_implementability",
        shared_fragment_ids=(
            "shared.output_handoff",
            "shared.memory_selection",
        ),
        is_review=True,
        produces="tasks-review-handoff-v1",
        consumes=("tasks_create",),
    ),
    ReleaseStep(
        label="definition_commit_gate",
        role="python",
        fragment_id=None,
    ),
)


class ReleaseDefinitionWorkflow(FragmentGateWorkflow[ReleaseStep, ReleaseDefinitionResult]):
    """Run the §6.1 release-definition sequence with fragment prompts + Python gates.

    Thin subclass of :class:`FragmentGateWorkflow`: the shared assembly + gate machinery lives
    in the base; this body declares the divergence hooks and its result factory. The terminal
    gate transitions the release to IMPLEMENTATION (``_TERMINAL_PHASE``).
    """

    _COMMAND = "release_definition"
    _WORKFLOW_LABEL = "release-definition"
    _INITIAL_PHASE = LifecyclePhase.RELEASE_DEFINITION
    _TERMINAL_PHASE = LifecyclePhase.IMPLEMENTATION

    def run(
        self, run_id: str, sequence: tuple[ReleaseStep, ...] = _SEQUENCE
    ) -> ReleaseDefinitionResult:
        """Execute the sequence; stop at the first blocked gate; advance on success."""
        return self._run_sequence(run_id, sequence)

    def _make_result(
        self,
        *,
        run_id: str,
        completed: bool,
        final_phase: LifecyclePhase,
        outcomes: tuple[_StepOutcome, ...],
        blocked: BlockedState | None,
    ) -> ReleaseDefinitionResult:
        return ReleaseDefinitionResult(
            run_id=run_id,
            completed=completed,
            final_phase=final_phase,
            steps=tuple(_to_step_result(outcome) for outcome in outcomes),
            blocked=blocked,
        )


def _to_step_result(outcome: _StepOutcome) -> ReleaseStepResult:
    return ReleaseStepResult(
        label=outcome.label,
        accepted=outcome.accepted,
        is_gate=outcome.is_gate,
        fragment_id=outcome.fragment_id,
        prompt_text=outcome.prompt_text,
        runtime_kind=outcome.runtime_kind,
        blocked=outcome.blocked,
    )


__all__ = [
    "ReleaseDefinitionResult",
    "ReleaseDefinitionWorkflow",
    "ReleaseStep",
    "ReleaseStepResult",
]
