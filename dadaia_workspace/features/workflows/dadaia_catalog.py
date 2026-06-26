"""dadaia-workflow catalog — features/workflows/dadaia_catalog.py.

The operator must be able to open dadaia-panel and clearly understand *every*
dadaia-workflow (the v0.1.24 two-layer redesign, WS-8 / ADR-E): its **purpose**,
its ordered **step sequence**, the per-step **harness/model** options it can run on,
its **availability** (runnable now vs partially migrated vs deferred), and a
**diagram** (server-rendered SVG DAG + a Mermaid flowchart of the step sequence).

Unlike the legacy ``*.workflow.md`` declarative DAGs served by
:class:`WorkflowsService.get_detail`, this catalog describes the *real* Python-owned
dadaia-workflows — there is no second drifting source. Each workflow's step list is
introspected directly from its authoritative definition:

- ``release_definition`` → :data:`...workflows.release_definition._SEQUENCE` (fully
  available — the WS-5 reference workflow);
- ``implementation`` → :func:`...lifecycle.pipeline.implementation_ladder` (partial —
  two steps are fragment-driven, the rest still carry the generic suffix);
- ``backlog_definition`` / ``audit`` / ``research`` / ``bug_report`` →
  :data:`...workflows._deferred.DEFERRED_WORKFLOWS` (deferred — entry points raise).

The per-step harness/model options come from the single discrete Layer-2 catalog
(:mod:`dadaia_workspace.core.harness_models`, LAW 2 / ADR-B): a model step may run on
``pi`` (3 discrete options) or ``codex`` (2 options); the deterministic ``fake`` test
adapter carries no model. Python-owned gate steps (no worker) carry no harness/model.

Everything here is **pure data assembly over existing sources** — zero I/O, no second
catalog table — so it stays import-linter clean and is trivially unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from dadaia_workspace.core import harness_models
from dadaia_workspace.core.models.lifecycle import AgentRuntimeKind
from dadaia_workspace.features.lifecycle.pipeline import implementation_ladder
from dadaia_workspace.features.lifecycle.workflows._deferred import DEFERRED_WORKFLOWS
from dadaia_workspace.features.lifecycle.workflows.release_definition import _SEQUENCE
from dadaia_workspace.features.workflows.dag import render_dag_svg
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
    diagram_mermaid: str = field(default="")


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
        "Will turn raw bug/backlog signal into curated, grilled backlog entries ready for "
        "a release. Scaffolded only — the entry point raises NotImplementedError; deferred "
        "to a follow-up release."
    ),
    "audit": (
        "Will run the project-auditor fan-out (multi-lens review producing committed audit "
        "reports). Scaffolded only — the entry point raises; deferred to a follow-up "
        "release."
    ),
    "research": (
        "Will run a bounded research spike producing a findings handoff. Scaffolded only — "
        "the entry point raises; deferred to a follow-up release."
    ),
    "bug_report": (
        "Will drive structured bug triage + registration. Scaffolded only — the entry "
        "point raises; deferred to a follow-up release."
    ),
}

_DISPLAY_NAMES: dict[str, str] = {
    "release_definition": "Release Definition",
    "implementation": "Implementation",
    "backlog_definition": "Backlog Definition",
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
# Mermaid flowchart of the step sequence (operator explicitly wants mermaid)
# ---------------------------------------------------------------------------


def _mermaid_node_id(order: int) -> str:
    return f"s{order}"


def _mermaid_label(step: DadaiaWorkflowStepDTO) -> str:
    """A readable, mermaid-safe node label (no characters that break the parser)."""
    base = step.label.replace("_", " ")
    safe = "".join(ch for ch in base if ch.isalnum() or ch == " ").strip() or step.label
    suffix = " (gate)" if step.is_gate else ""
    return f"{safe}{suffix}"


def render_step_mermaid(steps: list[DadaiaWorkflowStepDTO]) -> str:
    """Render the ordered step sequence as a Mermaid ``flowchart TD``.

    The output is a fenced ```mermaid block so it renders through the panel's existing
    mistune mermaid path (``panel/views/_md_render.py``) exactly like memory-atom
    diagrams — no new client dependency. Gate steps are diamond nodes; worker steps are
    rounded rectangles; consecutive steps are linked top-to-bottom.
    """
    if not steps:
        return "```mermaid\nflowchart TD\n  empty[No steps]\n```"
    lines = ["```mermaid", "flowchart TD"]
    for step in steps:
        node = _mermaid_node_id(step.order)
        label = _mermaid_label(step)
        if step.is_gate:
            lines.append(f"  {node}{{{label}}}")
        else:
            lines.append(f"  {node}([{label}])")
    for prev, nxt in zip(steps, steps[1:], strict=False):
        lines.append(f"  {_mermaid_node_id(prev.order)} --> {_mermaid_node_id(nxt.order)}")
    lines.append("```")
    return "\n".join(lines)


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
        steps.append(
            DadaiaWorkflowStepDTO(
                order=order,
                label=rstep.label,
                role=rstep.role,
                purpose=_RELEASE_STEP_PURPOSE.get(rstep.label, ""),
                is_gate=rstep.is_review or rstep.fragment_id is None,
                harness_options=harness_options,
                model_options=model_options,
                runtime_kind=runtime,
                fragment_id=rstep.fragment_id,
            )
        )
    return steps


def _implementation_steps() -> list[DadaiaWorkflowStepDTO]:
    steps: list[DadaiaWorkflowStepDTO] = []
    ladder = implementation_ladder(AgentRuntimeKind.FAKE)
    for order, pstep in enumerate(ladder, start=1):
        harness_options, model_options = _harness_options_for(is_worker_step=True)
        is_gate = pstep.label.startswith("review")
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
            )
        )
    return steps


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
        diagram_svg=render_dag_svg(_steps_to_stage_dtos(steps)) if steps else "",
        diagram_mermaid=render_step_mermaid(steps),
    )


# ---------------------------------------------------------------------------
# Public catalog API
# ---------------------------------------------------------------------------


def _all_workflows() -> list[DadaiaWorkflowDTO]:
    workflows: list[DadaiaWorkflowDTO] = [
        _build_workflow("release_definition", AVAILABILITY_AVAILABLE, _release_definition_steps()),
        _build_workflow("implementation", AVAILABILITY_PARTIAL, _implementation_steps()),
    ]
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


__all__ = [
    "AVAILABILITY_AVAILABLE",
    "AVAILABILITY_DEFERRED",
    "AVAILABILITY_PARTIAL",
    "DadaiaWorkflowDTO",
    "DadaiaWorkflowStepDTO",
    "get_dadaia_workflow",
    "list_dadaia_workflows",
    "render_step_mermaid",
]
