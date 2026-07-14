"""dadaia-workflow catalog presentation shim — features/workflows/dadaia_catalog.py.

The operator must be able to open dadaia-panel and clearly understand *every*
dadaia-workflow (the v0.1.24 two-layer redesign, WS-8 / ADR-E): its **purpose**,
its ordered **step sequence**, the per-step **harness/model** options it can run on,
its **availability** (runnable now vs partially migrated vs deferred), and a
**diagram** (server-rendered SVG DAG fluxogram, enriched with per-node harness/model).

**v0.1.54 FR2 (T-54-11): this module is now a thin presentation shim.** The governed
catalog data — every DTO, purpose/display copy, step builder, and the
:func:`governed_workflow_catalog` resolver projection — was extracted to
:mod:`dadaia_workspace.features.lifecycle.governed_catalog` to **break the former
``workflows <-> lifecycle`` import cycle** (the assembly introspects only lifecycle
internals, so it belongs in ``features/lifecycle``). This shim imports **exactly one**
lifecycle module — ``governed_catalog`` — the single allowed ``workflows -> lifecycle``
edge, and re-exports the public names so every consumer keeps the stable public path
``features.workflows.dadaia_catalog`` (zero importer edits).

What stays here is the **presentation concern**: enriching each SVG-free governed
:class:`DadaiaWorkflowDTO` with its server-rendered diagram (``features/workflows/dag.py``
via :func:`render_dag_svg`), which is why the diagram assembly lives on the workflows
(presentation) side and not in ``governed_catalog``.
"""

from __future__ import annotations

from dataclasses import replace

from dadaia_workspace.features.lifecycle.governed_catalog import (
    AVAILABILITY_AVAILABLE as AVAILABILITY_AVAILABLE,
)
from dadaia_workspace.features.lifecycle.governed_catalog import (
    AVAILABILITY_DEFERRED as AVAILABILITY_DEFERRED,
)
from dadaia_workspace.features.lifecycle.governed_catalog import (
    AVAILABILITY_PARTIAL as AVAILABILITY_PARTIAL,
)
from dadaia_workspace.features.lifecycle.governed_catalog import (
    DEFAULT_PROFILE_BY_HARNESS_PURPOSE as DEFAULT_PROFILE_BY_HARNESS_PURPOSE,
)
from dadaia_workspace.features.lifecycle.governed_catalog import (
    DEFERRED_WORKFLOWS as DEFERRED_WORKFLOWS,
)
from dadaia_workspace.features.lifecycle.governed_catalog import (
    DadaiaWorkflowDTO,
    DadaiaWorkflowStepDTO,
    _all_workflows,
    governed_workflow_catalog,
    resolve_default_model_id,
)
from dadaia_workspace.features.lifecycle.governed_catalog import (
    _assert_catalog_defaults_resolve as _assert_catalog_defaults_resolve,
)
from dadaia_workspace.features.workflows.dag import NodeMeta, StageDTO, render_dag_svg

# ---------------------------------------------------------------------------
# Card fluxogram enrichment (server-rendered SVG is the single diagram source)
# ---------------------------------------------------------------------------


def _node_meta_for_steps(steps: list[DadaiaWorkflowStepDTO]) -> dict[str, NodeMeta]:
    """Build the ``{stage_id: NodeMeta}`` enrichment map for the card fluxogram.

    Keyed by ``step.label`` (the stage id ``_steps_to_stage_dtos`` assigns), each worker
    step maps to its **governed default** harness + concrete model, resolved from the
    step's ``default_profiles`` via the governed seam's
    :func:`~dadaia_workspace.features.lifecycle.governed_catalog.resolve_default_model_id`
    — the same single source the resolver reads (no second table). A Python-owned gate step
    (``default_harness is None``) carries no worker and is omitted, so its node stays bare.
    Enrichment lives here on the presentation side; ``dag.py``'s shared contract is untouched.
    """
    meta: dict[str, NodeMeta] = {}
    for step in steps:
        harness = step.default_harness
        if harness is None:
            continue
        profile_id = step.default_profiles.get(harness)
        if profile_id is None:  # pragma: no cover - guarded by catalog import assert
            continue
        meta[step.label] = NodeMeta(harness=harness, model=resolve_default_model_id(profile_id))
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


def _build_workflow(workflow: DadaiaWorkflowDTO) -> DadaiaWorkflowDTO:
    """Enrich a governed (SVG-free) workflow DTO with its server-rendered diagram SVG.

    The governed catalog produces every :class:`DadaiaWorkflowDTO` SVG-free; this shim adds
    the diagram (the workflows-side presentation concern) so the public catalog accessors
    return fully-described, diagram-carrying workflows — byte-identical to the pre-split
    assembly.
    """
    steps = workflow.steps
    diagram_svg = (
        render_dag_svg(_steps_to_stage_dtos(steps), _node_meta_for_steps(steps)) if steps else ""
    )
    return replace(workflow, diagram_svg=diagram_svg)


# ---------------------------------------------------------------------------
# Public catalog API
# ---------------------------------------------------------------------------


def list_dadaia_workflows() -> list[DadaiaWorkflowDTO]:
    """Return every dadaia-workflow, fully described (with diagram SVG), in catalog order."""
    return [_build_workflow(workflow) for workflow in _all_workflows()]


def get_dadaia_workflow(name: str) -> DadaiaWorkflowDTO | None:
    """Return one fully-described dadaia-workflow by name, or ``None`` if unknown."""
    for workflow in list_dadaia_workflows():
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
    "governed_workflow_catalog",
    "list_dadaia_workflows",
]
