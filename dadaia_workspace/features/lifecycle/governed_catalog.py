"""Governed dadaia-workflow catalog — features/lifecycle/governed_catalog.py.

**v0.1.54 FR2 (T-54-11): the cycle-break seam.** This module is the authoritative,
SVG-free assembly of the dadaia-workflow catalog. It lives in ``features/lifecycle``
because every source it introspects is a lifecycle internal — the workflow ``_SEQUENCE``
bodies, :func:`implementation_ladder`, :mod:`model_profiles`, and the resolver's
:class:`WorkflowCatalog` seam. Keeping the assembly here **breaks the former
``workflows <-> lifecycle`` import cycle**: this module imports only lifecycle internals
+ core (never ``features/workflows``), and the thin presentation shim
``features/workflows/dadaia_catalog.py`` imports *this* module (the one allowed
direction), re-exporting the public names so consumers keep the stable public path.

Everything here is **pure data assembly over existing sources** — zero I/O, no second
catalog table, no diagram rendering. The server-rendered SVG fluxogram is a
presentation concern owned by ``features/workflows/dadaia_catalog.py`` (which reaches
``features/workflows/dag.py``); every :class:`DadaiaWorkflowDTO` this module produces is
therefore SVG-free (``diagram_svg == ""``). The presentation shim enriches each workflow
with its diagram before returning it from ``list_dadaia_workflows`` / ``get_dadaia_workflow``.

**Wave B (v0.1.28 — T-28-B-01): the governed source of truth.** Each worker (model) step
carries a ``default_harness`` plus a ``default_profile`` for *each* supported harness
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
from dadaia_workspace.features.lifecycle.workflows.audit import _SEQUENCE as _AUDIT_SEQUENCE
from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
    _SEQUENCE as _BACKLOG_SEQUENCE,
)
from dadaia_workspace.features.lifecycle.workflows.release_definition import _SEQUENCE

# ---------------------------------------------------------------------------
# Availability vocabulary (ADR-E)
# ---------------------------------------------------------------------------

#: The workflow is fully migrated and runnable end-to-end today.
AVAILABILITY_AVAILABLE = "available"
#: The workflow runs, but only some steps are fragment-driven (the rest are generic).
AVAILABILITY_PARTIAL = "partial"
#: The workflow is scaffolded only; its entry point raises and it cannot run yet.
AVAILABILITY_DEFERRED = "deferred"

#: Deferred-workflow names, in catalog order. Empty since v0.1.30 Wave E — every workflow
#: ships a real fragment+gate body. Kept as the declared seam ``_all_workflows`` iterates so
#: a future deferred workflow is enumerated honestly without a code change. Inlined here in
#: v0.1.53 when the standalone ``_deferred`` module was retired.
DEFERRED_WORKFLOWS: tuple[str, ...] = ()

#: The Layer-2 harness names a model step may run on. ``fake`` is the deterministic
#: test adapter (no model); the two real workers come from the discrete catalog.
_MODEL_HARNESS_OPTIONS: tuple[str, ...] = (harness_models.PI_HARNESS, harness_models.CODEX_HARNESS)


# ---------------------------------------------------------------------------
# DTOs for the sole governed workflow catalog.
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
    """A fully self-describing dadaia-workflow for the panel catalog (WS-8 / ADR-E).

    Assembled SVG-free here (``diagram_svg == ""``); the presentation shim
    ``features/workflows/dadaia_catalog.py`` enriches it with the server-rendered diagram.
    """

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
    "spec_review": (
        "Software-architect and QA-engineer jointly review the SPEC in ONE pass "
        "(architecture + testability angles); a REJECTED verdict blocks advancement."
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
        "Software-engineer implements the approved release task set test-first (the fragment-driven "
        "TDD step) and emits an implementation handoff."
    ),
    "review_combined": (
        "QA-engineer, security-reviewer, and code-reviewer judge the change in ONE "
        "tri-angle pass (tests real, OWASP checks, correctness/architecture fidelity); "
        "a REJECTED verdict returns to implementation through the bounded loop."
    ),
    "close": (
        "Product-engineer records closure evidence and updates current memory only after "
        "the combined review approves (light-effort mechanical step)."
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
        "Product-engineer challenges the operator demand from evidence (OPT-IN via "
        "--grill; unresolved items become open_questions; its digest feeds the author)."
    ),
    "backlog_author": (
        "Product-engineer authors the single consistent item (NEW file XOR edit existing — "
        "never a twin; fragment-driven). The default path's ONE model call."
    ),
    "backlog_review_gate": (
        "Python validates what the author ACTUALLY wrote to disk: binds its intents "
        "through the registry, diffs against the pre-authoring snapshot, and blocks any "
        "DUPLICATE/DIVERGENT_CONFLICT it would introduce."
    ),
}

# Wave-E fragment+gate workflow bodies (T-30-E-01..03). Each step's purpose is sourced from
# its fragment role; the terminal gate is Python-owned (no worker).
_AUDIT_STEP_PURPOSE: dict[str, str] = {
    "audit_report": (
        "Project-auditor runs the whole audit arc in ONE pass: states the question, "
        "scans the lenses, emits findings, and routes each to a disposition (bug / "
        "backlog / accepted-risk / resolved — never a deletion; fragment-driven)."
    ),
    "audit_disposition_gate": (
        "Python-owned terminal gate: referential integrity only (every finding routed "
        "exactly once; no phantom disposition) — severity/lens are derived from the "
        "finding by id, never re-verified as byte copies. Runs no worker."
    ),
}

_WORKFLOW_PURPOSE: dict[str, str] = {
    "release_definition": (
        "Turns an approved bug + backlog set into an approved release definition. Python "
        "owns the §6.1 step order and every review gate; each model step's prompt is a "
        "fragment bundle + scoped context + output schema run on a discrete (harness, "
        "model). It walks scope → SPEC → SPEC reviews → PLAN → PLAN review → TASKS → "
        "implementability review → a terminal Python commit gate that advances the "
        "release to IMPLEMENTATION. A consumed backlog pick skips the scope model step."
    ),
    "implementation_reviews": (
        "Implements the approved release task set test-first, judges it with ONE combined "
        "tri-angle review (QA + security + code), then closes the release. A rejected "
        "review returns to implementation through the bounded correction loop with the "
        "rejection digest injected."
    ),
    "backlog_definition": (
        "Turns an operator demand into one consistent backlog item with ONE model call. "
        "backlog_author writes the item; the Python backlog_review_gate then validates "
        "what actually landed on disk — binds its intents through the canonical-subject "
        "registry and blocks any DUPLICATE/DIVERGENT_CONFLICT against the real backlog. "
        "--grill opts into an evidence-first intake step whose digest feeds the author. "
        "It walks [intake_grill] → backlog_author → backlog_review_gate."
    ),
    "audit": (
        "Runs a bounded audit in ONE model pass: project-auditor states the question, "
        "scans the lenses for drift, emits findings, and routes each to a disposition "
        "(bug / backlog / accepted-risk / resolved — never a deletion). The terminal "
        "Python gate checks referential integrity only. It walks audit_report → "
        "audit_disposition_gate."
    ),
}

_DISPLAY_NAMES: dict[str, str] = {
    "release_definition": "Release Definition",
    "implementation_reviews": "Implementation + Reviews",
    "backlog_definition": "Backlog Definition",
    "audit": "Audit",
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
    *, harness_options: list[str], is_gate: bool, light: bool = False
) -> tuple[str | None, dict[str, str]]:
    """Return (default_harness, {harness: default_profile_id}) for a step.

    A worker step (``harness_options`` non-empty) defaults to the deep profile when it is a
    review/gate step, the light profile when *light* (mechanical steps like ``close``),
    else the standard profile, for *each* supported harness. The default harness is
    :data:`_DEFAULT_WORKER_HARNESS` when supported, else the first option. A
    Python-owned gate step (no worker) carries no default harness/profile.
    """
    if not harness_options:
        return None, {}
    purpose = "light" if light else ("deep" if is_gate else "standard")
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


def resolve_default_model_id(profile_id: str) -> str:
    """Resolve a governed default-profile id to its concrete model id.

    The single model-profile registry is a lifecycle concern (:mod:`model_profiles`); the
    presentation-side catalog (``features/workflows/dadaia_catalog.py``) delegates model
    resolution here through the seam so it holds **no** direct
    ``workflows -> lifecycle.model_profiles`` edge — only the one seam edge to this module.
    """
    return model_profiles.resolve(profile_id).model_id


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
            harness_options=harness_options,
            is_gate=is_gate,
            light=pstep.label == "close",
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


def _closure_steps() -> list[DadaiaWorkflowStepDTO]:
    """Build the Python-owned terminal closure-removal gate."""
    gate_harness_options, gate_model_options = _harness_options_for(is_worker_step=False)
    gate_default_harness, gate_default_profiles = _default_profiles_for(
        harness_options=gate_harness_options, is_gate=True
    )
    removal_gate = DadaiaWorkflowStepDTO(
        order=1,
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
    return [removal_gate]


def _implementation_reviews_steps() -> list[DadaiaWorkflowStepDTO]:
    """Return one ordered implementation, review, and closure sequence."""
    from dataclasses import replace

    combined = [*_implementation_steps(), *_closure_steps()]
    return [replace(step, order=order) for order, step in enumerate(combined, start=1)]


def _svg_free_workflow(
    name: str, availability: str, steps: list[DadaiaWorkflowStepDTO]
) -> DadaiaWorkflowDTO:
    """Assemble one workflow DTO **without** its diagram SVG (presentation enriches it)."""
    return DadaiaWorkflowDTO(
        name=name,
        display_name=_DISPLAY_NAMES.get(name, name),
        purpose=_WORKFLOW_PURPOSE.get(name, ""),
        availability=availability,
        step_count=len(steps),
        steps=steps,
        diagram_svg="",
    )


# ---------------------------------------------------------------------------
# Public catalog API (SVG-free — presentation adds the diagram)
# ---------------------------------------------------------------------------


def _all_workflows() -> list[DadaiaWorkflowDTO]:
    workflows: list[DadaiaWorkflowDTO] = [
        _svg_free_workflow(
            "backlog_definition", AVAILABILITY_AVAILABLE, _backlog_definition_steps()
        ),
        _svg_free_workflow(
            "release_definition", AVAILABILITY_AVAILABLE, _release_definition_steps()
        ),
        _svg_free_workflow(
            "implementation_reviews",
            AVAILABILITY_AVAILABLE,
            _implementation_reviews_steps(),
        ),
        _svg_free_workflow("audit", AVAILABILITY_AVAILABLE, _audit_steps()),
    ]
    # No workflow remains deferred (DEFERRED_WORKFLOWS is empty as of Wave E), but the loop is
    # kept so a future deferred workflow is enumerated honestly without a code change.
    for name in DEFERRED_WORKFLOWS:
        workflows.append(_svg_free_workflow(name, AVAILABILITY_DEFERRED, []))
    return workflows


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
    "DEFAULT_PROFILE_BY_HARNESS_PURPOSE",
    "DEFERRED_WORKFLOWS",
    "DadaiaWorkflowDTO",
    "DadaiaWorkflowStepDTO",
    "governed_workflow_catalog",
    "resolve_default_model_id",
]
