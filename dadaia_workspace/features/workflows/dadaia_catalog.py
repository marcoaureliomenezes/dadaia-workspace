"""dadaia-workflow catalog — features/workflows/dadaia_catalog.py.

The operator must be able to open dadaia-panel and clearly understand *every*
dadaia-workflow (the v0.1.24 two-layer redesign, WS-8 / ADR-E): its **purpose**,
its ordered **step sequence**, the per-step **harness/model** options it can run on,
its **availability** (runnable now vs partially migrated vs deferred), and a
**diagram** (server-rendered SVG DAG fluxogram, enriched with per-node harness/model).

Unlike the legacy ``*.workflow.md`` declarative DAGs served by
:class:`WorkflowsService.get_detail`, this catalog describes the *real* Python-owned
dadaia-workflows — there is no second drifting source. Each workflow's step list is
introspected directly from its authoritative definition:

- ``release_definition`` → :data:`...workflows.release_definition._SEQUENCE` (fully
  available — the WS-5 reference workflow);
- ``implementation`` → :func:`...lifecycle.pipeline.implementation_ladder` (partial —
  two steps are fragment-driven, the rest still carry the generic suffix);
- ``backlog_definition`` → :data:`...workflows.backlog_definition._SEQUENCE` (available —
  the v0.1.26 R2 §4 workflow body with Python-owned gates);
- ``audit`` / ``research`` / ``bug_report`` →
  :data:`...workflows._deferred.DEFERRED_WORKFLOWS` (deferred — entry points raise).

The per-step harness/model options come from the single discrete Layer-2 catalog
(:mod:`dadaia_workspace.core.harness_models`, LAW 2 / ADR-B): a model step may run on
``pi`` (4 discrete options) or ``codex`` (2 options); the deterministic ``fake`` test
adapter carries no model. Python-owned gate steps (no worker) carry no harness/model.

Everything here is **pure data assembly over existing sources** — zero I/O, no second
catalog table — so it stays import-linter clean and is trivially unit-testable.

**Wave B (v0.1.28 — T-28-B-01): the governed source of truth.** Each worker (model) step
now carries a ``default_harness`` plus a ``default_profile`` for *each* supported harness
(:attr:`DadaiaWorkflowStepDTO.default_profiles`), every profile id resolving to a built-in
:class:`WorkflowModelProfile` in :mod:`dadaia_workspace.features.lifecycle.model_profiles`.
:func:`governed_workflow_catalog` projects this catalog onto the resolver's
:class:`WorkflowCatalog` seam, so the :class:`WorkflowExecutionPolicyResolver` reads the
*same* single source the panel reads — there is no second model table. An import-time
guard (:func:`_assert_catalog_defaults_resolve`, mirroring
``model_profiles._assert_profiles_resolve``) fails loudly if any default profile is
ungoverned or harness-mismatched.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from dadaia_workspace.core import harness_models
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder
from dadaia_workspace.features.lifecycle.policy_resolver import (
    DEFAULT_PROFILE_BY_HARNESS_PURPOSE,
    CatalogStep,
    CatalogWorkflow,
    WorkflowCatalog,
)
from dadaia_workspace.features.lifecycle.workflows._deferred import DEFERRED_WORKFLOWS
from dadaia_workspace.features.lifecycle.workflows.audit import _SEQUENCE as _AUDIT_SEQUENCE
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    _SEQUENCE as _BACKLOG_SEQUENCE,
)
from dadaia_workspace.features.lifecycle.workflows.bug_report import (
    _SEQUENCE as _BUG_REPORT_SEQUENCE,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import _SEQUENCE
from dadaia_workspace.features.lifecycle.workflows.research import (
    _SEQUENCE as _RESEARCH_SEQUENCE,
)
from dadaia_workspace.features.workflows.dag import NodeMeta, render_dag_svg
from dadaia_workspace.features.workflows.service import StageDTO

# ---------------------------------------------------------------------------
# Availability vocabulary (ADR-E)
# ---------------------------------------------------------------------------

#: The workflow is fully migrated and runnable end-to-end today.
AVAILABILITY_AVAILABLE = "available"
#: The workflow runs, but only some steps are fragment-driven (the rest are generic).
AVAILABILITY_PARTIAL = "partial"
#: The workflow is scaffolded only; its entry point raises and it cannot run yet.
AVAILABILITY_DEFERRED = "deferred"

#: The Layer-2 harness names a model step may run on. ``fake`` is the deterministic
#: test adapter (no model); the two real workers come from the discrete catalog.
_MODEL_HARNESS_OPTIONS: tuple[str, ...] = (harness_models.PI_HARNESS, harness_models.CODEX_HARNESS)


# ---------------------------------------------------------------------------
# DTOs (additive — these are new types; legacy WorkflowDetailDTO is untouched)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DadaiaWorkflowStepDTO:
    """One step of a dadaia-workflow, fully described for the panel.

    ``harness_options`` is the set of Layer-2 harnesses this step can run on (empty for
    a Python-owned gate step that runs no worker). ``model_options`` maps each harness
    to its discrete ``"<model_id>:<effort>"`` choices from the single
    :mod:`harness_models` catalog. ``is_gate`` marks a review/commit gate.
    """

    order: int
    label: str
    role: str
    purpose: str
    is_gate: bool
    harness_options: list[str]
    model_options: dict[str, list[str]]
    runtime_kind: str | None = None
    fragment_id: str | None = None
    #: Wave B (T-28-B-01) — the governed default harness for this worker step, and the
    #: default model **profile** id for every supported harness. ``default_harness`` is
    #: ``None`` and ``default_profiles`` is empty for a Python-owned gate step (no worker).
    #: Every profile id resolves to a built-in :class:`WorkflowModelProfile`.
    default_harness: str | None = None
    default_profiles: dict[str, str] = field(default_factory=dict)
    #: The shared fragment ids the step composes (alongside ``fragment_id``); carried for
    #: the run-snapshot's auditability (the resolver threads these onto each step entry).
    shared_fragment_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DadaiaWorkflowDTO:
    """A fully self-describing dadaia-workflow for the panel catalog (WS-8 / ADR-E)."""

    name: str
    display_name: str
    purpose: str
    availability: str
    step_count: int
    steps: list[DadaiaWorkflowStepDTO]
    diagram_svg: str = field(default="")


# ---------------------------------------------------------------------------
# Per-step purpose copy (operator-facing; sourced from the §6.1 step roles)
# ---------------------------------------------------------------------------

_RELEASE_STEP_PURPOSE: dict[str, str] = {
    "release_scope": (
        "Project-manager grills and fixes the bug + backlog set the release will solve, "
        "producing the scoped problem statement the SPEC is written against."
    ),
    "spec_create": (
        "Product-engineer authors SPEC.md — the approved problem/solution contract — and "
        "hands it off for review."
    ),
    "spec_arch_review": (
        "Software-architect reviews the SPEC for architectural soundness; a REJECTED "
        "verdict blocks advancement."
    ),
    "spec_qa_review": (
        "QA-engineer reviews the SPEC for testable acceptance criteria; a REJECTED verdict "
        "blocks advancement."
    ),
    "plan_create": "Product-engineer authors PLAN.md — the implementation approach for the SPEC.",
    "plan_review": (
        "QA-engineer and software-architect jointly review the PLAN; a REJECTED verdict "
        "blocks advancement."
    ),
    "tasks_create": (
        "Product-engineer decomposes the PLAN into TASKS.md — ordered, write-scoped "
        "implementable units."
    ),
    "tasks_implementability_review": (
        "Software-engineer reviews TASKS for implementability and clear write sets; a "
        "REJECTED verdict blocks advancement."
    ),
    "definition_commit_gate": (
        "Python-owned terminal gate: advances the release from RELEASE_DEFINITION to "
        "IMPLEMENTATION only when every prior review gate passed. Runs no worker."
    ),
}

_IMPLEMENTATION_STEP_PURPOSE: dict[str, str] = {
    "implement": (
        "Software-engineer implements the reserved task test-first (the fragment-driven "
        "TDD step) and emits an implementation handoff."
    ),
    "review_qa": (
        "QA-engineer validates acceptance + runs the suite (fragment-driven); a REJECTED "
        "verdict blocks advancement."
    ),
    "review_security": (
        "Security-reviewer audits the commit against the OWASP checklist (generic step — "
        "not yet fragment-migrated)."
    ),
    "review_code": (
        "Code-reviewer reviews the diff for the pre-PR gate (generic step — not yet "
        "fragment-migrated)."
    ),
}

_CLOSURE_STEP_PURPOSE: dict[str, str] = {
    "close": (
        "Product-engineer runs the release-closure step (CODE_REVIEW -> CLOSURE): writes "
        "CLOSURE.md and finalizes the release. Generic worker step (not yet fragment-migrated)."
    ),
    "closure_removal_gate": (
        "Python-owned terminal gate: applies residual-aware backlog removal over the "
        "consumed-ledger (archive-then-remove fully-shipped items; rewrite partials). Runs "
        "no worker."
    ),
}

_BACKLOG_STEP_PURPOSE: dict[str, str] = {
    "intake_grill": (
        "Project-manager grills the operator demand into proposed (subject -> change) "
        "intents (mandatory grill; fragment-driven)."
    ),
    "subject_bind": (
        "Python binds every proposed subject through the canonical-subject registry; HALTs "
        "on any unresolved/ambiguous subject (no silent NEW)."
    ),
    "existing_backlog_review": (
        "Python runs the deterministic set-intersection classifier over the bound intents "
        "vs every existing item (model offline by default; downgrade seam fail-closed)."
    ),
    "reconcile_decision": (
        "Python blocks a NEW file unless every existing item is UNRELATED; otherwise forces "
        "an UPDATE/MERGE."
    ),
    "conflict_resolution_grill": (
        "Project-manager grills a DIVERGENT_CONFLICT into one reconciled change — conditional, "
        "runs only when the review found a conflict (fragment-driven)."
    ),
    "backlog_author": (
        "Product-engineer authors the single consistent item (NEW file XOR edit existing — "
        "never a twin; fragment-driven)."
    ),
    "backlog_review_gate": (
        "Python re-runs the classifier over the authored result and blocks any "
        "DUPLICATE/DIVERGENT_CONFLICT it would introduce."
    ),
}

# Wave-E fragment+gate workflow bodies (T-30-E-01..03). Each step's purpose is sourced from
# its fragment role; the terminal gate is Python-owned (no worker).
_AUDIT_STEP_PURPOSE: dict[str, str] = {
    "audit_scope": (
        "Project-auditor bounds the audit question, lenses, surfaces, and acceptance rubric "
        "(fragment-driven)."
    ),
    "drift_scan": (
        "Project-auditor scans the bounded surfaces for drift and returns a verdict + findings "
        "(review gate — blocking drift BLOCKS)."
    ),
    "triage": (
        "Project-manager disposes every finding into disposition-ready output (bug / backlog / "
        "accepted-risk / resolved — never a deletion; fragment-driven)."
    ),
    "audit_disposition_gate": (
        "Python-owned terminal gate: completes the audit only when every prior gate passed and "
        "the workflow-step handoff graph is complete. Runs no worker."
    ),
}

_RESEARCH_STEP_PURPOSE: dict[str, str] = {
    "research_scope": (
        "Project-manager frames the research question, the decision it informs, the evidence "
        "bar, and the bounded surfaces (fragment-driven)."
    ),
    "investigate": (
        "Software-architect gathers evidence within the bounded scope (fragment-driven)."
    ),
    "synthesis": (
        "Project-manager synthesizes the evidence into a recommended next step — backlog / "
        "release action / justified no-action (fragment-driven)."
    ),
    "research_synthesis_gate": (
        "Python-owned terminal gate: completes the spike only when every prior step passed and "
        "the workflow-step handoff graph is complete. Runs no worker."
    ),
}

_BUG_REPORT_STEP_PURPOSE: dict[str, str] = {
    "bug_intake": (
        "Project-manager normalizes + redacts the reported symptom into the bug-record fields "
        "(fragment-driven)."
    ),
    "dedupe": (
        "Product-engineer decides new-vs-duplicate against tracked bugs (review gate — a "
        "duplicate BLOCKS the write)."
    ),
    "bug_write": (
        "Product-engineer files exactly one ADDITIVE specs/bugs/ record (no lease, never "
        "blocked; fragment-driven)."
    ),
    "bug_record_gate": (
        "Python-owned terminal gate: completes the run only when every prior gate passed and "
        "the workflow-step handoff graph is complete. Runs no worker."
    ),
}

_WORKFLOW_PURPOSE: dict[str, str] = {
    "release_definition": (
        "Turns an approved bug + backlog set into an approved release definition. Python "
        "owns the §6.1 step order and every review gate; each model step's prompt is a "
        "fragment bundle + scoped context + output schema run on a discrete (harness, "
        "model). It walks scope → SPEC → SPEC reviews → PLAN → PLAN review → TASKS → "
        "implementability review → a terminal Python commit gate that advances the "
        "release to IMPLEMENTATION."
    ),
    "implementation": (
        "Threads a reserved task through the IMPLEMENTATION→CLOSURE review ladder: "
        "implement (TDD) → QA review → security review → code review. The implement and "
        "QA steps are fragment-driven; the security and code review steps still carry the "
        "generic suffix (partial migration), so the workflow is marked partial."
    ),
    "backlog_definition": (
        "Turns an operator demand into one consistent backlog item by construction. Python "
        "owns the gates: it binds every proposed subject through the canonical-subject "
        "registry (HALT on unresolved), classifies the demand against every existing item "
        "with the deterministic set-intersection classifier (model offline by default), "
        "blocks a NEW file unless every existing item is UNRELATED, runs a conditional "
        "conflict-resolution grill only on a DIVERGENT_CONFLICT, and re-validates the "
        "authored result. It walks intake_grill → subject_bind → existing_backlog_review → "
        "reconcile_decision → conflict_resolution_grill → backlog_author → backlog_review_gate."
    ),
    "closure": (
        "Closes a release: a single product-engineer worker step (close) advances "
        "CODE_REVIEW -> CLOSURE, followed by a Python-owned terminal gate that applies "
        "residual-aware backlog removal over the consumed-ledger. Closure has no multi-step "
        "ladder; the close worker step is generic (not yet fragment-migrated), so the "
        "workflow is marked partial."
    ),
    "audit": (
        "Runs a bounded audit: project-auditor scopes the audit question + lenses, scans the "
        "bounded surfaces for drift (a review gate — blocking drift BLOCKS), and project-auditor "
        "triages every finding into disposition-ready output (bug / backlog / accepted-risk / "
        "resolved — never a deletion). Python owns the step order, the drift-scan gate, and the "
        "terminal disposition gate. It walks audit_scope → drift_scan → triage → "
        "audit_disposition_gate."
    ),
    "research": (
        "Runs a bounded research spike: product-engineer frames the question + evidence bar, "
        "software-architect investigates within the bounded scope, and product-engineer "
        "synthesizes the evidence into a recommended next step (backlog / release action / "
        "justified no-action). Python owns the step order and the terminal synthesis gate. It "
        "walks research_scope → investigate → synthesis → research_synthesis_gate."
    ),
    "bug_report": (
        "Normalizes a reported symptom into one additive bug record: project-auditor captures + "
        "redacts the symptom/repro/severity, product-engineer dedupes against tracked bugs (a "
        "review gate — a duplicate BLOCKS the write), and product-engineer files exactly one "
        "ADDITIVE specs/bugs/ record (no lease, never blocked). Python owns the step order, the "
        "dedupe gate, and the terminal record gate. It walks bug_intake → dedupe → bug_write → "
        "bug_record_gate."
    ),
}

_DISPLAY_NAMES: dict[str, str] = {
    "release_definition": "Release Definition",
    "implementation": "Implementation",
    "backlog_definition": "Backlog Definition",
    "closure": "Release Closure",
    "audit": "Audit Fan-out",
    "research": "Research",
    "bug_report": "Bug Report",
}


# ---------------------------------------------------------------------------
# Step harness/model assembly
# ---------------------------------------------------------------------------


def _model_options() -> dict[str, list[str]]:
    """The full discrete model catalog for every model-capable harness (LAW 2)."""
    return {h: list(harness_models.model_choices(h)) for h in _MODEL_HARNESS_OPTIONS}


def _harness_options_for(*, is_worker_step: bool) -> tuple[list[str], dict[str, list[str]]]:
    """Return (harness_options, model_options) for a step.

    A worker (model) step can run on any Layer-2 model harness; a Python-owned gate
    step runs no worker, so it carries no harness/model options.
    """
    if not is_worker_step:
        return [], {}
    return list(_MODEL_HARNESS_OPTIONS), _model_options()


# ---------------------------------------------------------------------------
# Governed default profiles (Wave B / T-28-B-01)
# ---------------------------------------------------------------------------
#
# Each worker step defaults to a model **profile** per supported harness. A
# review/gate worker step defaults to the harness's deep-reasoning profile; a producing
# worker step defaults to the harness's standard implementation profile. The per-harness
# default-by-purpose map has ONE home — ``policy_resolver.DEFAULT_PROFILE_BY_HARNESS_PURPOSE``
# (T-30-C-05 nit i; previously a verbatim twin lived here). The profile ids are governed:
# ``_assert_catalog_defaults_resolve`` ties them to the built-in registry at import time
# (mirroring ``model_profiles._assert_profiles_resolve``) — no second table.

#: The harness a worker step defaults to when more than one is supported (LAW 1: codex/pi).
_DEFAULT_WORKER_HARNESS: str = harness_models.CODEX_HARNESS


def _default_profiles_for(
    *, harness_options: list[str], is_gate: bool
) -> tuple[str | None, dict[str, str]]:
    """Return (default_harness, {harness: default_profile_id}) for a step.

    A worker step (``harness_options`` non-empty) defaults to the deep profile when it is a
    review/gate step, else the standard profile, for *each* supported harness. The default
    harness is :data:`_DEFAULT_WORKER_HARNESS` when supported, else the first option. A
    Python-owned gate step (no worker) carries no default harness/profile.
    """
    if not harness_options:
        return None, {}
    purpose = "deep" if is_gate else "standard"
    profiles: dict[str, str] = {}
    for harness in harness_options:
        by_purpose = DEFAULT_PROFILE_BY_HARNESS_PURPOSE.get(harness)
        if by_purpose is None:  # pragma: no cover - guarded by _MODEL_HARNESS_OPTIONS
            continue
        profiles[harness] = by_purpose[purpose]
    default_harness = (
        _DEFAULT_WORKER_HARNESS if _DEFAULT_WORKER_HARNESS in profiles else harness_options[0]
    )
    return default_harness, profiles


# ---------------------------------------------------------------------------
# Card fluxogram enrichment (server-rendered SVG is the single diagram source)
# ---------------------------------------------------------------------------


def _node_meta_for_steps(steps: list[DadaiaWorkflowStepDTO]) -> dict[str, NodeMeta]:
    """Build the ``{stage_id: NodeMeta}`` enrichment map for the card fluxogram.

    Keyed by ``step.label`` (the stage id ``_steps_to_stage_dtos`` assigns), each worker
    step maps to its **governed default** harness + concrete model, resolved from the
    step's ``default_profiles`` via the built-in profile registry — the same single source
    the resolver reads (no second table). A Python-owned gate step (``default_harness is
    None``) carries no worker and is omitted, so its node stays bare. Enrichment lives here
    on the catalog side; ``dag.py``'s shared contract is untouched.
    """
    meta: dict[str, NodeMeta] = {}
    for step in steps:
        harness = step.default_harness
        if harness is None:
            continue
        profile_id = step.default_profiles.get(harness)
        if profile_id is None:  # pragma: no cover - guarded by catalog import assert
            continue
        profile = model_profiles.resolve(profile_id)
        meta[step.label] = NodeMeta(harness=harness, model=profile.model_id)
    return meta


def _steps_to_stage_dtos(steps: list[DadaiaWorkflowStepDTO]) -> list[StageDTO]:
    """Map dadaia-workflow steps onto StageDTO so render_dag_svg can draw the DAG.

    The dadaia-workflows are strictly sequential (Python owns the order), so each step
    ``needs`` its predecessor. Gate steps map to ``gate=True`` (rendered with the ⊙
    marker by the existing SVG renderer).
    """
    stage_dtos: list[StageDTO] = []
    prev_id: str | None = None
    for step in steps:
        stage_dtos.append(
            StageDTO(
                id=step.label,
                agent=step.role,
                needs=[prev_id] if prev_id is not None else [],
                parallel_group=None,
                gate=step.is_gate,
                expected_output_path=None,
                must_include=None,
                on_failure="stop",
            )
        )
        prev_id = step.label
    return stage_dtos


# ---------------------------------------------------------------------------
# Per-workflow step builders (introspect the real definitions)
# ---------------------------------------------------------------------------


def _release_definition_steps() -> list[DadaiaWorkflowStepDTO]:
    steps: list[DadaiaWorkflowStepDTO] = []
    for order, rstep in enumerate(_SEQUENCE, start=1):
        is_worker = rstep.fragment_id is not None
        harness_options, model_options = _harness_options_for(is_worker_step=is_worker)
        runtime = rstep.runtime_kind.value if rstep.runtime_kind is not None else None
        is_gate = rstep.is_review or rstep.fragment_id is None
        default_harness, default_profiles = _default_profiles_for(
            harness_options=harness_options, is_gate=is_gate
        )
        steps.append(
            DadaiaWorkflowStepDTO(
                order=order,
                label=rstep.label,
                role=rstep.role,
                purpose=_RELEASE_STEP_PURPOSE.get(rstep.label, ""),
                is_gate=is_gate,
                harness_options=harness_options,
                model_options=model_options,
                runtime_kind=runtime,
                fragment_id=rstep.fragment_id,
                default_harness=default_harness,
                default_profiles=default_profiles,
                shared_fragment_ids=rstep.shared_fragment_ids,
            )
        )
    return steps


def _implementation_steps() -> list[DadaiaWorkflowStepDTO]:
    steps: list[DadaiaWorkflowStepDTO] = []
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    for order, pstep in enumerate(ladder, start=1):
        harness_options, model_options = _harness_options_for(is_worker_step=True)
        is_gate = pstep.label.startswith("review")
        default_harness, default_profiles = _default_profiles_for(
            harness_options=harness_options, is_gate=is_gate
        )
        steps.append(
            DadaiaWorkflowStepDTO(
                order=order,
                label=pstep.label,
                role=pstep.role,
                purpose=_IMPLEMENTATION_STEP_PURPOSE.get(pstep.label, ""),
                is_gate=is_gate,
                harness_options=harness_options,
                model_options=model_options,
                runtime_kind=pstep.runtime_kind.value,
                fragment_id=pstep.fragment_id,
                default_harness=default_harness,
                default_profiles=default_profiles,
                shared_fragment_ids=pstep.shared_fragment_ids,
            )
        )
    return steps


def _backlog_definition_steps() -> list[DadaiaWorkflowStepDTO]:
    steps: list[DadaiaWorkflowStepDTO] = []
    for order, bstep in enumerate(_BACKLOG_SEQUENCE, start=1):
        is_worker = bstep.fragment_id is not None
        harness_options, model_options = _harness_options_for(is_worker_step=is_worker)
        runtime = bstep.runtime_kind.value if bstep.runtime_kind is not None else None
        # Python-disposing steps (no fragment) are the gates; the conditional grill
        # and the model steps are worker steps.
        is_gate = bstep.fragment_id is None
        default_harness, default_profiles = _default_profiles_for(
            harness_options=harness_options, is_gate=is_gate
        )
        steps.append(
            DadaiaWorkflowStepDTO(
                order=order,
                label=bstep.label,
                role=bstep.role,
                purpose=_BACKLOG_STEP_PURPOSE.get(bstep.label, ""),
                is_gate=is_gate,
                harness_options=harness_options,
                model_options=model_options,
                runtime_kind=runtime,
                fragment_id=bstep.fragment_id,
                default_harness=default_harness,
                default_profiles=default_profiles,
                shared_fragment_ids=bstep.shared_fragment_ids,
            )
        )
    return steps


class _FragmentGateStep(Protocol):
    """The structural shape shared by the Wave-E fragment+gate step dataclasses.

    ``AuditStep`` / ``ResearchStep`` / ``BugReportStep`` are distinct frozen dataclasses
    that mirror ``ReleaseStep``'s field shape. This Protocol lets one builder introspect any
    of them without a hard import of each concrete type. Members are read-only properties so
    a frozen dataclass with the same fields structurally matches.
    """

    @property
    def label(self) -> str: ...
    @property
    def role(self) -> str: ...
    @property
    def fragment_id(self) -> str | None: ...
    @property
    def shared_fragment_ids(self) -> tuple[str, ...]: ...
    @property
    def is_review(self) -> bool: ...
    @property
    def runtime_kind(self) -> AgentRuntimeKind | None: ...


def _fragment_gate_steps(
    sequence: Sequence[_FragmentGateStep], purpose: dict[str, str]
) -> list[DadaiaWorkflowStepDTO]:
    """Build catalog step DTOs for a Wave-E fragment+gate workflow body.

    Mirrors ``_release_definition_steps``: a model step (``fragment_id`` set) is a worker step
    — a review step defaults to the deep profile, a producing step to the standard profile; a
    step with no fragment is the Python-owned terminal gate (no worker).
    """
    steps: list[DadaiaWorkflowStepDTO] = []
    for order, fstep in enumerate(sequence, start=1):
        is_worker = fstep.fragment_id is not None
        harness_options, model_options = _harness_options_for(is_worker_step=is_worker)
        runtime = fstep.runtime_kind.value if fstep.runtime_kind is not None else None
        is_gate = fstep.is_review or fstep.fragment_id is None
        default_harness, default_profiles = _default_profiles_for(
            harness_options=harness_options, is_gate=is_gate
        )
        steps.append(
            DadaiaWorkflowStepDTO(
                order=order,
                label=fstep.label,
                role=fstep.role,
                purpose=purpose.get(fstep.label, ""),
                is_gate=is_gate,
                harness_options=harness_options,
                model_options=model_options,
                runtime_kind=runtime,
                fragment_id=fstep.fragment_id,
                default_harness=default_harness,
                default_profiles=default_profiles,
                shared_fragment_ids=fstep.shared_fragment_ids,
            )
        )
    return steps


def _audit_steps() -> list[DadaiaWorkflowStepDTO]:
    return _fragment_gate_steps(_AUDIT_SEQUENCE, _AUDIT_STEP_PURPOSE)


def _research_steps() -> list[DadaiaWorkflowStepDTO]:
    return _fragment_gate_steps(_RESEARCH_SEQUENCE, _RESEARCH_STEP_PURPOSE)


def _bug_report_steps() -> list[DadaiaWorkflowStepDTO]:
    return _fragment_gate_steps(_BUG_REPORT_SEQUENCE, _BUG_REPORT_STEP_PURPOSE)


def _closure_steps() -> list[DadaiaWorkflowStepDTO]:
    """Build closure's real step list (T-29-B-01).

    Closure has **no** multi-step ladder. Its authoritative definition is the
    ``dadaia lifecycle close`` verb (``cli/commands/lifecycle.py``): a single
    ``_run_phase_step(label="close", role="product-engineer", CODE_REVIEW -> CLOSURE)``
    worker step, plus a Python-owned ``_apply_closure_removal`` post-step (the
    consumed-ledger backlog removal) modeled here as a terminal gate. The close worker step
    is **generic** (no fragment) — so, per WMP-5, it carries no output-schema obligation; it
    is cataloged honestly, not invented as a fragment-driven step.
    """
    # The single real worker step: generic (no fragment), so it carries no output schema.
    close_harness_options, close_model_options = _harness_options_for(is_worker_step=True)
    close_default_harness, close_default_profiles = _default_profiles_for(
        harness_options=close_harness_options, is_gate=False
    )
    close_step = DadaiaWorkflowStepDTO(
        order=1,
        label="close",
        role="product-engineer",
        purpose=_CLOSURE_STEP_PURPOSE["close"],
        is_gate=False,
        harness_options=close_harness_options,
        model_options=close_model_options,
        runtime_kind=None,
        fragment_id=None,
        default_harness=close_default_harness,
        default_profiles=close_default_profiles,
        shared_fragment_ids=(),
    )
    # The Python-owned removal post-step modeled as a terminal gate: no worker.
    gate_harness_options, gate_model_options = _harness_options_for(is_worker_step=False)
    gate_default_harness, gate_default_profiles = _default_profiles_for(
        harness_options=gate_harness_options, is_gate=True
    )
    removal_gate = DadaiaWorkflowStepDTO(
        order=2,
        label="closure_removal_gate",
        role="python",
        purpose=_CLOSURE_STEP_PURPOSE["closure_removal_gate"],
        is_gate=True,
        harness_options=gate_harness_options,
        model_options=gate_model_options,
        runtime_kind=None,
        fragment_id=None,
        default_harness=gate_default_harness,
        default_profiles=gate_default_profiles,
        shared_fragment_ids=(),
    )
    return [close_step, removal_gate]


def _build_workflow(
    name: str, availability: str, steps: list[DadaiaWorkflowStepDTO]
) -> DadaiaWorkflowDTO:
    return DadaiaWorkflowDTO(
        name=name,
        display_name=_DISPLAY_NAMES.get(name, name),
        purpose=_WORKFLOW_PURPOSE.get(name, ""),
        availability=availability,
        step_count=len(steps),
        steps=steps,
        diagram_svg=(
            render_dag_svg(_steps_to_stage_dtos(steps), _node_meta_for_steps(steps))
            if steps
            else ""
        ),
    )


# ---------------------------------------------------------------------------
# Public catalog API
# ---------------------------------------------------------------------------


def _all_workflows() -> list[DadaiaWorkflowDTO]:
    workflows: list[DadaiaWorkflowDTO] = [
        _build_workflow("release_definition", AVAILABILITY_AVAILABLE, _release_definition_steps()),
        _build_workflow("implementation", AVAILABILITY_PARTIAL, _implementation_steps()),
        _build_workflow("backlog_definition", AVAILABILITY_AVAILABLE, _backlog_definition_steps()),
        _build_workflow("closure", AVAILABILITY_PARTIAL, _closure_steps()),
        # Wave-E (v0.1.30 T-30-E-01..03): real fragment+gate bodies — now AVAILABLE.
        _build_workflow("audit", AVAILABILITY_AVAILABLE, _audit_steps()),
        _build_workflow("research", AVAILABILITY_AVAILABLE, _research_steps()),
        _build_workflow("bug_report", AVAILABILITY_AVAILABLE, _bug_report_steps()),
    ]
    # No workflow remains deferred (DEFERRED_WORKFLOWS is empty as of Wave E), but the loop is
    # kept so a future deferred workflow is enumerated honestly without a code change.
    for name in DEFERRED_WORKFLOWS:
        workflows.append(_build_workflow(name, AVAILABILITY_DEFERRED, []))
    return workflows


def list_dadaia_workflows() -> list[DadaiaWorkflowDTO]:
    """Return every dadaia-workflow, fully described, in catalog order."""
    return _all_workflows()


def get_dadaia_workflow(name: str) -> DadaiaWorkflowDTO | None:
    """Return one fully-described dadaia-workflow by name, or ``None`` if unknown."""
    for workflow in _all_workflows():
        if workflow.name == name:
            return workflow
    return None


# ---------------------------------------------------------------------------
# Governed catalog projection onto the resolver's WorkflowCatalog seam (Wave B)
# ---------------------------------------------------------------------------


_OUTPUT_SCHEMA_DEFAULT = "agent-run-result-v1"


def _governed_step(step: DadaiaWorkflowStepDTO) -> CatalogStep | None:
    """Project one worker step onto the resolver's :class:`CatalogStep`.

    Gate steps (no worker, ``default_harness is None``) are not governed model steps and
    are skipped — the resolver only resolves model policy for steps that run a worker.
    """
    if step.default_harness is None:
        return None
    default_profile = step.default_profiles[step.default_harness]
    fragments = (step.fragment_id, *step.shared_fragment_ids) if step.fragment_id else ()
    return CatalogStep(
        label=step.label,
        role=step.role,
        default_harness=step.default_harness,
        default_profile=default_profile,
        # T-29-A-01: carry the per-harness default profile map onto the resolver seam so
        # the resolver can auto-select a profile for an effective-harness override (D-1).
        default_profiles=dict(step.default_profiles),
        fragments=fragments,
        output_schema=_OUTPUT_SCHEMA_DEFAULT if step.fragment_id else None,
    )


def governed_workflow_catalog() -> WorkflowCatalog:
    """Project this catalog onto the resolver's :class:`WorkflowCatalog` seam (T-28-B-01).

    This is the **single governed source** the :class:`WorkflowExecutionPolicyResolver`
    reads — the same source the panel reads — so CLI and panel never disagree on which
    model a step runs. Only the worker (model) steps of each available/partial workflow are
    governed; Python-owned gate steps and deferred (zero-step) workflows carry no model
    policy and are omitted.
    """
    workflows: list[CatalogWorkflow] = []
    for workflow in _all_workflows():
        steps = tuple(
            governed
            for governed in (_governed_step(step) for step in workflow.steps)
            if governed is not None
        )
        if steps:
            workflows.append(CatalogWorkflow(workflow_id=workflow.name, steps=steps))
    return WorkflowCatalog(workflows=tuple(workflows))


def _assert_catalog_defaults_resolve() -> None:
    """Fail loudly if any worker step's default profile is ungoverned (no-second-table guard).

    Mirrors ``model_profiles._assert_profiles_resolve``: every default profile id must
    resolve in the built-in registry, and each per-harness default profile's own harness
    must match the harness it is declared for. Runs at import time.

    Raises:
        ValueError: if a default profile id is unknown or harness-mismatched.
    """
    for workflow in _all_workflows():
        for step in workflow.steps:
            for harness, profile_id in step.default_profiles.items():
                profile = model_profiles.resolve(profile_id)
                if profile.harness != harness:
                    raise ValueError(
                        f"{workflow.name}.{step.label}: default profile {profile_id!r} runs "
                        f"on harness {profile.harness!r}, declared as default for {harness!r}"
                    )
            if (
                step.default_harness is not None
                and step.default_harness not in step.default_profiles
            ):
                raise ValueError(
                    f"{workflow.name}.{step.label}: default harness "
                    f"{step.default_harness!r} has no default profile"
                )


_assert_catalog_defaults_resolve()


__all__ = [
    "AVAILABILITY_AVAILABLE",
    "AVAILABILITY_DEFERRED",
    "AVAILABILITY_PARTIAL",
    "DadaiaWorkflowDTO",
    "DadaiaWorkflowStepDTO",
    "get_dadaia_workflow",
    "governed_workflow_catalog",
    "list_dadaia_workflows",
]
