"""Audit workflow body — one scoped model pass + a Python disposition gate.

The Wave-E three-step ladder (scope → drift-scan → triage) collapsed to a single
``audit_report`` model step (v0.2.x simplification): the old triage step was ~90%
mechanical copying that Python then re-verified byte-for-byte AFTER all sessions were
spent — the design maximized weak-model failure modes instead of absorbing them. Now
the model does the judgment work once (question, lenses, findings, routing) and
Python owns the bookkeeping:

1. ``audit_report`` (project-auditor) — states the audit question, scans the lenses,
   emits findings, and routes each finding to a disposition
   (``bug``/``backlog``/``accepted-risk``/``resolved``). Produces ``audit-report-v1``.
2. ``audit_disposition_gate`` (python, no model) — the terminal Python gate. Checks
   REFERENTIAL INTEGRITY only (every finding disposed exactly once; every disposition
   references a real finding — the audit-disposition law: route, never drop) and
   COMPLETEs the run with no phase transition (A29). Severity/lens live on the
   finding; Python derives them by id wherever needed — a disposition never has to
   byte-copy them and can never block the run over a copy slip.

Thin subclass of
:class:`~dadaia_workspace.features.lifecycle.workflows._fragment_gate.FragmentGateWorkflow`
(the ONE prompt-assembly + Python-gate seam shared with ``release_definition``);
``resume_from`` comes from the base.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dadaia_workspace.core.models.lifecycle import (
    AgentRuntimeKind,
    BlockedState,
    LifecyclePhase,
    LifecycleRun,
)
from dadaia_workspace.core.models.workflow_execution import ResolvedModelConfig
from dadaia_workspace.features.lifecycle.workflow_handoffs import (
    MalformedHandoffError,
    RequiredHandoffMissingError,
)
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
    # A failed audit verdict is domain evidence that must still be routed. Structural
    # output failures block; REJECTED itself does not abort this workflow.
    blocks_on_rejection: bool = True


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


#: The audit sequence: ONE model step + the terminal Python gate. ``runtime_kind=None``
#: on the model step means the workflow's default harness is used; the terminal gate
#: carries no fragment and no model. The fragment id matches the shipped ``audit/*`` bundle.
_SEQUENCE: tuple[AuditStep, ...] = (
    AuditStep(
        label="audit_report",
        role="project-auditor",
        fragment_id="audit.audit_report",
        produces="audit-report-v1",
    ),
    AuditStep(
        label="audit_disposition_gate",
        role="python",
        fragment_id=None,
    ),
)


class AuditWorkflow(FragmentGateWorkflow[AuditStep, AuditResult]):
    """Run the audit sequence with a fragment prompt + Python gates.

    Thin subclass of :class:`FragmentGateWorkflow`. The terminal gate COMPLETEs the audit with
    no phase transition (``_TERMINAL_PHASE`` unset) — the audit produces disposition-ready
    output (A29) and advances no release phase.
    """

    _COMMAND = "audit"
    _WORKFLOW_LABEL = "audit"
    _INITIAL_PHASE = LifecyclePhase.QA_REVIEW

    def run(
        self,
        run_id: str,
        sequence: tuple[AuditStep, ...] = _SEQUENCE,
        *,
        resume_from: str | None = None,
    ) -> AuditResult:
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
    ) -> AuditResult:
        return AuditResult(
            run_id=run_id,
            completed=completed,
            final_phase=final_phase,
            steps=tuple(_to_step_result(outcome) for outcome in outcomes),
            blocked=blocked,
        )

    def _terminal_semantic_block(
        self, run: LifecycleRun, step: AuditStep, sequence: tuple[AuditStep, ...]
    ) -> BlockedState | None:
        """Referential integrity only — Python derives, never re-verifies, copied fields.

        The audit-disposition law: every finding is routed exactly once and no
        disposition may reference a phantom finding. Severity/lens are read from the
        finding by id wherever needed — a copy mismatch can no longer exist, so it can
        no longer block a completed model session.
        """
        if self._handoff_resolver is None:
            return None
        try:
            report = self._handoff_resolver.resolve_required(
                run, producer_step="audit_report", attempt=0
            ).payload
        except (RequiredHandoffMissingError, MalformedHandoffError) as exc:
            return BlockedState(
                reason=f"audit disposition evidence is unavailable: {exc}",
                blocked_at_step=step.label,
            )

        findings_raw = report.get("findings")
        dispositions_raw = report.get("dispositions")
        finding_ids = [
            item["id"]
            for item in (findings_raw if isinstance(findings_raw, list) else [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        ]
        disposed_ids = [
            item["finding_id"]
            for item in (dispositions_raw if isinstance(dispositions_raw, list) else [])
            if isinstance(item, dict) and isinstance(item.get("finding_id"), str)
        ]
        violations: list[str] = []
        undisposed = sorted(set(finding_ids) - set(disposed_ids))
        if undisposed:
            violations.append(f"findings never disposed: {', '.join(undisposed)}")
        phantom = sorted(set(disposed_ids) - set(finding_ids))
        if phantom:
            violations.append(f"dispositions reference unknown findings: {', '.join(phantom)}")
        if len(disposed_ids) != len(set(disposed_ids)):
            violations.append("a finding is disposed more than once")
        if not violations:
            return None
        return BlockedState(
            reason="audit disposition contract is incomplete",
            blocked_at_step=step.label,
            detail={"violations": "; ".join(violations)},
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
