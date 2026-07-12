"""Research workflow body — scope→investigate→synthesis on fragments + Python gates.

The Wave-E (v0.1.30 Item 6) real workflow body that replaced the fail-loud
``_deferred.research`` stub. As of v0.1.57 FR1 it is a thin subclass of
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate.FragmentGateWorkflow` —
the ONE prompt-assembly + Python-gate seam shared with ``release_definition`` / ``audit`` /
``bug_report``. This body declares the divergence hooks (the ``research`` command, the
BACKLOG_DEFINITION initial phase, a terminal gate that COMPLETEs with no phase transition, and
the ``ResearchStep`` / ``ResearchResult`` dataclass types) and keeps its module-global
``_SEQUENCE``.

The sequence is:

1. ``research_scope`` (product-engineer) — frames the research question, the decision it
   informs, the evidence bar, and the bounded surfaces. Produces ``research-scope-handoff-v1``.
2. ``investigate`` (software-architect) — gathers evidence within the bounded scope. Consumes
   ``research_scope``; produces ``research-findings-handoff-v1``.
3. ``synthesis`` (product-engineer) — turns the evidence into a recommended next step (backlog
   / release action / justified no-action). Consumes ``investigate``; produces
   ``research-findings-handoff-v1``.
4. ``research_synthesis_gate`` (python, no model) — the terminal Python gate; COMPLETEs the run
   (no phase transition) only when every prior step passed and the handoff graph is complete.
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

__all__ = [
    "ResearchResult",
    "ResearchStep",
    "ResearchStepResult",
    "ResearchWorkflow",
    "_SEQUENCE",
]


@dataclass(frozen=True)
class ResearchStep:
    """One step of the research sequence (mirrors ``release_definition.ReleaseStep``)."""

    label: str
    role: str
    fragment_id: str | None
    shared_fragment_ids: tuple[str, ...] = ()
    is_review: bool = False
    runtime_kind: AgentRuntimeKind | None = None
    produces: str | None = None
    consumes: tuple[str, ...] = ()
    # Governance-resolved concrete model for this step (v0.1.56 / FR2). Threaded by
    # ``apply_resolved_policy`` (structural ``PolicyApplicableStep`` Protocol — no pipeline.py
    # edit) and forwarded to the request by the base ``_scope``. Additive-optional, mirroring
    # ``ReleaseStep``.
    resolved_model: ResolvedModelConfig | None = None
    model_profile: str | None = None


@dataclass(frozen=True)
class ResearchStepResult:
    """Typed outcome of one research step."""

    label: str
    accepted: bool
    is_gate: bool
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class ResearchResult:
    """Typed outcome of the whole research sequence."""

    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[ResearchStepResult, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The research sequence. The terminal gate carries no fragment and no model.
_SEQUENCE: tuple[ResearchStep, ...] = (
    ResearchStep(
        label="research_scope",
        role="product-engineer",
        fragment_id="research.research_scope",
        shared_fragment_ids=("shared.grill_questionnaire",),
        produces="research-scope-handoff-v1",
    ),
    ResearchStep(
        label="investigate",
        role="software-architect",
        fragment_id="research.investigate",
        shared_fragment_ids=("shared.output_handoff",),
        produces="research-findings-handoff-v1",
        consumes=("research_scope",),
    ),
    ResearchStep(
        label="synthesis",
        role="product-engineer",
        fragment_id="research.synthesis",
        shared_fragment_ids=("shared.output_handoff",),
        produces="research-findings-handoff-v1",
        consumes=("investigate",),
    ),
    ResearchStep(
        label="research_synthesis_gate",
        role="python",
        fragment_id=None,
    ),
)


class ResearchWorkflow(FragmentGateWorkflow[ResearchStep, ResearchResult]):
    """Run the research sequence with fragment prompts + Python gates.

    Thin subclass of :class:`FragmentGateWorkflow`; the terminal gate COMPLETEs with no phase
    transition (``_TERMINAL_PHASE`` unset).
    """

    _COMMAND = "research"
    _WORKFLOW_LABEL = "research"
    _INITIAL_PHASE = LifecyclePhase.BACKLOG_DEFINITION

    def run(
        self,
        run_id: str,
        sequence: tuple[ResearchStep, ...] = _SEQUENCE,
        *,
        resume_from: str | None = None,
    ) -> ResearchResult:
        """Execute the sequence; stop at the first blocked gate; complete on success."""
        return self._run_sequence(run_id, sequence, resume_from=resume_from)

    def _make_result(
        self,
        *,
        run_id: str,
        completed: bool,
        final_phase: LifecyclePhase,
        outcomes: tuple[_StepOutcome, ...],
        blocked: BlockedState | None,
    ) -> ResearchResult:
        return ResearchResult(
            run_id=run_id,
            completed=completed,
            final_phase=final_phase,
            steps=tuple(_to_step_result(outcome) for outcome in outcomes),
            blocked=blocked,
        )


def _to_step_result(outcome: _StepOutcome) -> ResearchStepResult:
    return ResearchStepResult(
        label=outcome.label,
        accepted=outcome.accepted,
        is_gate=outcome.is_gate,
        fragment_id=outcome.fragment_id,
        prompt_text=outcome.prompt_text,
        runtime_kind=outcome.runtime_kind,
        blocked=outcome.blocked,
    )
