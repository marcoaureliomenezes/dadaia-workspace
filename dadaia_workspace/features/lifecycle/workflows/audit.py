"""Audit workflow body — the audit scope→drift-scan→triage sequence on fragments + gates.

The Wave-E (v0.1.30 Item 6) real workflow body that replaced the fail-loud ``_deferred.audit``
stub. As of v0.1.57 FR1 it is a thin subclass of
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate.FragmentGateWorkflow` —
the ONE prompt-assembly + Python-gate seam shared with ``release_definition`` / ``research`` /
``bug_report``. This body declares the divergence hooks (the ``audit`` command, the QA_REVIEW
initial phase, a terminal gate that COMPLETEs with no phase transition, and the ``AuditStep`` /
``AuditResult`` dataclass types) and keeps its module-global ``_SEQUENCE``.

The sequence is:

1. ``audit_scope`` (project-auditor) — bounds the audit question, lenses, surfaces, and
   acceptance rubric. Produces ``audit-scope-handoff-v1``.
2. ``drift_scan`` (project-auditor, **review**) — runs the lenses over the bounded surfaces and
   returns a verdict + findings. Consumes ``audit_scope``; produces ``audit-findings-handoff-v1``.
   A REJECTED verdict (blocking drift) BLOCKS the run.
3. ``triage`` (project-auditor) — disposes every finding into **disposition-ready** output
   (A29). Consumes ``drift_scan``; produces ``audit-disposition-handoff-v1``.
4. ``audit_disposition_gate`` (python, no model) — the terminal Python gate. COMPLETEs the run
   (no phase transition; A29 — the audit deletes nothing and advances no release phase) only
   when every prior gate passed and the workflow-step handoff graph is complete.
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
    "AuditResult",
    "AuditStep",
    "AuditStepResult",
    "AuditWorkflow",
    "_SEQUENCE",
]


@dataclass(frozen=True)
class AuditStep:
    """One step of the audit sequence (mirrors ``release_definition.ReleaseStep``).

    A model step names its fragment id (``audit.step``), the shared fragment ids it cites, the
    runtime kind it runs on, and whether it is a **review** (a gate whose verdict can REJECT and
    BLOCK advancement). The terminal Python gate carries ``fragment_id=None`` and
    ``runtime_kind=None`` — it runs no model. ``produces``/``consumes`` are the workflow-step
    handoff data-plane edges; inert unless a resolver is wired (back-compat).
    """

    label: str
    role: str
    fragment_id: str | None
    shared_fragment_ids: tuple[str, ...] = ()
    is_review: bool = False
    runtime_kind: AgentRuntimeKind | None = None
    produces: str | None = None
    consumes: tuple[str, ...] = ()
    # Governance-resolved concrete model for this step (v0.1.56 / FR2). ``apply_resolved_policy``
    # threads the resolved snapshot model here (the structural ``PolicyApplicableStep`` Protocol
    # auto-satisfied by these two fields — no pipeline.py edit); the base ``_scope`` forwards it
    # to the request. Additive-optional, mirroring ``ReleaseStep``.
    resolved_model: ResolvedModelConfig | None = None
    model_profile: str | None = None


@dataclass(frozen=True)
class AuditStepResult:
    """Typed outcome of one audit step."""

    label: str
    accepted: bool
    is_gate: bool
    fragment_id: str | None = None
    prompt_text: str | None = None
    runtime_kind: AgentRuntimeKind | None = None
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class AuditResult:
    """Typed outcome of the whole audit sequence."""

    run_id: str
    completed: bool
    final_phase: LifecyclePhase
    steps: tuple[AuditStepResult, ...] = field(default_factory=tuple)
    blocked: BlockedState | None = None


#: The audit sequence. ``runtime_kind=None`` on a model step means the workflow's default
#: harness is used; the terminal gate carries no fragment and no model. Fragment ids match the
#: shipped ``audit/*`` bundle.
_SEQUENCE: tuple[AuditStep, ...] = (
    AuditStep(
        label="audit_scope",
        role="project-auditor",
        fragment_id="audit.audit_scope",
        produces="audit-scope-handoff-v1",
    ),
    AuditStep(
        label="drift_scan",
        role="project-auditor",
        fragment_id="audit.drift_scan",
        shared_fragment_ids=("shared.output_handoff",),
        is_review=True,
        produces="audit-findings-handoff-v1",
        consumes=("audit_scope",),
    ),
    AuditStep(
        label="triage",
        role="project-auditor",
        fragment_id="audit.triage",
        shared_fragment_ids=("shared.output_handoff",),
        produces="audit-disposition-handoff-v1",
        consumes=("drift_scan",),
    ),
    AuditStep(
        label="audit_disposition_gate",
        role="python",
        fragment_id=None,
    ),
)


class AuditWorkflow(FragmentGateWorkflow[AuditStep, AuditResult]):
    """Run the audit sequence with fragment prompts + Python gates.

    Thin subclass of :class:`FragmentGateWorkflow`. The terminal gate COMPLETEs the audit with
    no phase transition (``_TERMINAL_PHASE`` unset) — the audit produces disposition-ready
    output (A29) and advances no release phase.
    """

    _COMMAND = "audit"
    _WORKFLOW_LABEL = "audit"
    _INITIAL_PHASE = LifecyclePhase.QA_REVIEW

    def run(self, run_id: str, sequence: tuple[AuditStep, ...] = _SEQUENCE) -> AuditResult:
        """Execute the sequence; stop at the first blocked gate; complete on success."""
        return self._run_sequence(run_id, sequence)

    def _make_result(
        self,
        *,
        run_id: str,
        completed: bool,
        final_phase: LifecyclePhase,
        outcomes: tuple[_StepOutcome, ...],
        blocked: BlockedState | None,
    ) -> AuditResult:
        return AuditResult(
            run_id=run_id,
            completed=completed,
            final_phase=final_phase,
            steps=tuple(_to_step_result(outcome) for outcome in outcomes),
            blocked=blocked,
        )


def _to_step_result(outcome: _StepOutcome) -> AuditStepResult:
    return AuditStepResult(
        label=outcome.label,
        accepted=outcome.accepted,
        is_gate=outcome.is_gate,
        fragment_id=outcome.fragment_id,
        prompt_text=outcome.prompt_text,
        runtime_kind=outcome.runtime_kind,
        blocked=outcome.blocked,
    )
