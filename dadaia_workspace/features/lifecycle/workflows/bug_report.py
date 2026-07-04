"""Bug-report workflow body — intake→dedupe→bug_write on fragments + Python gates.

The Wave-E (v0.1.30 Item 6) real workflow body that replaced the fail-loud
``_deferred.bug_report`` stub. As of v0.1.57 FR1 it is a thin subclass of
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate.FragmentGateWorkflow` —
the ONE prompt-assembly + Python-gate seam shared with ``release_definition`` / ``audit`` /
``research``. This body declares the divergence hooks (the ``bug_report`` command, the
BACKLOG_DEFINITION initial phase, a terminal gate that COMPLETEs with no phase transition, and
the ``BugReportStep`` / ``BugReportResult`` dataclass types), keeps its module-global
``_SEQUENCE``, AND **overrides ``_scope``** for its ADDITIVE ``bug_write`` special-case.

The sequence is:

1. ``bug_intake`` (project-auditor) — normalizes a reported symptom into the bug-record fields
   (symptom / repro / expected-vs-actual / severity), redaction-clean. Produces
   ``bug-intake-handoff-v1``.
2. ``dedupe`` (product-engineer, **review**) — decides new-vs-duplicate against tracked bugs.
   Consumes ``bug_intake``; produces ``bug-dedupe-handoff-v1``. A REJECTED verdict (duplicate)
   BLOCKS the write — the duplicate is folded into the existing bug, not re-filed.
3. ``bug_write`` (product-engineer) — files exactly one **additive** bug record. Consumes
   ``dedupe``; produces ``bug-record-handoff-v1``.
4. ``bug_record_gate`` (python, no model) — the terminal Python gate; COMPLETEs the run (no
   phase transition) only when every prior step passed and the handoff graph is complete.

**A29 — ADDITIVE-only.** The ``bug_write`` step's worker scope allows writes **only** under the
bug channel (``specs/bugs/**``), which is the ADDITIVE path class — no lease is taken and the
write is never gate-blocked. The non-writing steps emit only to the handoff dir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    GateEvidenceKind,
    LifecyclePhase,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig
from dadaia_workspace.features.lifecycle.personas.loader import resolve_persona_for_role
from dadaia_workspace.features.lifecycle.prompt_builder import PromptScope
from dadaia_workspace.features.lifecycle.workflows._fragment_gate import (
    AssemblyStep,
    FragmentGateWorkflow,
    _StepOutcome,
)

__all__ = [
    "BugReportResult",
    "BugReportStep",
    "BugReportStepResult",
    "BugReportWorkflow",
    "_SEQUENCE",
]

#: The label of the single step permitted to write the additive bug record (A29). Its worker
#: scope allows ONLY the ADDITIVE ``specs/bugs/`` path class — no lease, never blocked.
_BUG_WRITE_STEP = "bug_write"


@dataclass(frozen=True)
class BugReportStep:
    """One step of the bug-report sequence (mirrors ``release_definition.ReleaseStep``)."""

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
    # edit) and forwarded to the request by the ``_scope`` override. Additive-optional,
    # mirroring ``ReleaseStep``.
    resolved_model: ResolvedModelConfig | None = None
    model_profile: str | None = None


@dataclass(frozen=True)
class BugReportStepResult:
    """Typed outcome of one bug-report step."""

    label: str
    accepted: bool
    is_gate: bool
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class BugReportResult:
    """Typed outcome of the whole bug-report sequence."""

    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[BugReportStepResult, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The bug-report sequence. The terminal gate carries no fragment and no model.
_SEQUENCE: tuple[BugReportStep, ...] = (
    BugReportStep(
        label="bug_intake",
        role="project-auditor",
        fragment_id="bug_report.bug_intake",
        shared_fragment_ids=("shared.output_handoff",),
        produces="bug-intake-handoff-v1",
    ),
    BugReportStep(
        label="dedupe",
        role="product-engineer",
        fragment_id="bug_report.dedupe",
        shared_fragment_ids=("shared.output_handoff",),
        is_review=True,
        produces="bug-dedupe-handoff-v1",
        consumes=("bug_intake",),
    ),
    BugReportStep(
        label=_BUG_WRITE_STEP,
        role="product-engineer",
        fragment_id="bug_report.bug_write",
        produces="bug-record-handoff-v1",
        consumes=("dedupe",),
    ),
    BugReportStep(
        label="bug_record_gate",
        role="python",
        fragment_id=None,
    ),
)


class BugReportWorkflow(FragmentGateWorkflow[BugReportStep, BugReportResult]):
    """Run the bug-report sequence with fragment prompts + Python gates.

    Thin subclass of :class:`FragmentGateWorkflow`; the terminal gate COMPLETEs with no phase
    transition (``_TERMINAL_PHASE`` unset). Overrides ``_scope`` so the ADDITIVE ``bug_write``
    step is scoped to the bug channel (A29).
    """

    _COMMAND = "bug_report"
    _WORKFLOW_LABEL = "bug_report"
    _INITIAL_PHASE = LifecyclePhase.BACKLOG_DEFINITION

    def run(self, run_id: str, sequence: tuple[BugReportStep, ...] = _SEQUENCE) -> BugReportResult:
        """Execute the sequence; stop at the first blocked gate; complete on success."""
        return self._run_sequence(run_id, sequence)

    def _scope(self, step: AssemblyStep, run_id: str, suffix: str) -> PromptScope:
        """Build the per-step worker scope, special-casing the ADDITIVE ``bug_write`` step.

        A29: the ``bug_write`` step allows writes ONLY under the ADDITIVE bug channel
        (``specs/bugs/**``) — no lease, never gate-blocked. Every other step is a non-writing
        analysis/review step and emits only to the handoff dir. The resolved model
        (``model_profile`` / ``resolved_model``) is threaded exactly as the base ``_scope``.
        """
        allowed: tuple[str, ...]
        if step.label == _BUG_WRITE_STEP:
            allowed = (f"repos/{self._context}/specs/bugs/**", "specs/bugs/**")
        else:
            allowed = (f".dadaia/handoff/{self._context}/**",)
        return PromptScope(
            role=step.role,
            context=self._context,
            release_id=self._release_id,
            task_id=f"{run_id}:{step.label}",
            prompt=suffix,
            allowed_paths=allowed,
            required_evidence=(GateEvidenceKind.HANDOFF,),
            model_profile=step.model_profile,
            resolved_model=step.resolved_model,
            persona=resolve_persona_for_role(step.role),
        )

    def _make_result(
        self,
        *,
        run_id: str,
        completed: bool,
        final_phase: LifecyclePhase,
        outcomes: tuple[_StepOutcome, ...],
        blocked: BlockedState | None,
    ) -> BugReportResult:
        return BugReportResult(
            run_id=run_id,
            completed=completed,
            final_phase=final_phase,
            steps=tuple(_to_step_result(outcome) for outcome in outcomes),
            blocked=blocked,
        )


def _to_step_result(outcome: _StepOutcome) -> BugReportStepResult:
    return BugReportStepResult(
        label=outcome.label,
        accepted=outcome.accepted,
        is_gate=outcome.is_gate,
        fragment_id=outcome.fragment_id,
        prompt_text=outcome.prompt_text,
        runtime_kind=outcome.runtime_kind,
        blocked=outcome.blocked,
    )
