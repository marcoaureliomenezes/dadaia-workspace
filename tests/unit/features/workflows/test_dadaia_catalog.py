"""Unit tests for ``features/workflows/dadaia_catalog`` — T-28-B-01.

Wave B makes the dadaia-workflow catalog the **governed source of truth**: every
worker (model) step carries a ``default_harness`` plus a ``default_profile`` for each
supported harness, every default profile id resolves in the built-in
:mod:`model_profiles` registry, and the catalog satisfies the resolver's
:class:`WorkflowCatalog` seam (one source — no second table). These tests assert that
contract directly.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.policy_resolver import (
    WorkflowCatalog,
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.features.workflows import dadaia_catalog
from dadaia_workspace.features.workflows.dadaia_catalog import (
    DadaiaWorkflowDTO,
    DadaiaWorkflowStepDTO,
    get_dadaia_workflow,
    governed_workflow_catalog,
    list_dadaia_workflows,
)

# ---------------------------------------------------------------------------
# Step DTO: default harness + default profile per supported harness
# ---------------------------------------------------------------------------


def _worker_steps(workflow: DadaiaWorkflowDTO) -> list[DadaiaWorkflowStepDTO]:
    return [s for s in workflow.steps if s.harness_options]


def test_every_worker_step_has_default_harness() -> None:
    for workflow in list_dadaia_workflows():
        for step in _worker_steps(workflow):
            assert step.default_harness, (
                f"{workflow.name}.{step.label} worker step has no default_harness"
            )
            assert step.default_harness in step.harness_options


def test_every_worker_step_has_default_profile_per_supported_harness() -> None:
    for workflow in list_dadaia_workflows():
        for step in _worker_steps(workflow):
            for harness in step.harness_options:
                assert harness in step.default_profiles, (
                    f"{workflow.name}.{step.label} missing default profile for {harness!r}"
                )


def test_every_default_profile_id_resolves_in_registry() -> None:
    for workflow in list_dadaia_workflows():
        for step in _worker_steps(workflow):
            for harness, profile_id in step.default_profiles.items():
                profile = model_profiles.resolve(profile_id)
                # The profile's own harness must match the harness it is the default for.
                assert profile.harness == harness, (
                    f"{workflow.name}.{step.label}: default profile {profile_id!r} runs on "
                    f"{profile.harness!r}, declared as default for {harness!r}"
                )


def test_default_harness_has_a_default_profile() -> None:
    for workflow in list_dadaia_workflows():
        for step in _worker_steps(workflow):
            assert step.default_harness in step.default_profiles


def test_gate_steps_carry_no_default_harness_or_profile() -> None:
    for workflow in list_dadaia_workflows():
        for step in workflow.steps:
            if not step.harness_options:
                assert step.default_harness is None
                assert step.default_profiles == {}


def test_review_steps_default_to_a_deep_profile() -> None:
    """Review/gate worker steps default to a deep-reasoning profile; worker steps to standard."""
    impl = get_dadaia_workflow("implementation")
    assert impl is not None
    review = next(s for s in impl.steps if s.label == "review_qa")
    implement = next(s for s in impl.steps if s.label == "implement")
    assert "review" in review.default_profiles[review.default_harness]
    assert "implementation" in implement.default_profiles[implement.default_harness]


# ---------------------------------------------------------------------------
# The catalog satisfies the resolver's WorkflowCatalog seam
# ---------------------------------------------------------------------------


def test_governed_catalog_is_a_workflow_catalog() -> None:
    catalog = governed_workflow_catalog()
    assert isinstance(catalog, WorkflowCatalog)
    assert catalog.workflows, "governed catalog has no workflows"


def test_governed_catalog_carries_implementation_workflow() -> None:
    catalog = governed_workflow_catalog()
    impl = catalog.workflow("implementation")
    assert impl is not None
    labels = {s.label for s in impl.steps}
    assert {"implement", "review_qa", "review_security", "review_code"} <= labels


def test_governed_catalog_step_defaults_resolve_and_match_harness() -> None:
    catalog = governed_workflow_catalog()
    for workflow in catalog.workflows:
        for step in workflow.steps:
            profile = model_profiles.resolve(step.default_profile)
            assert profile.harness == step.default_harness, (
                f"{workflow.workflow_id}.{step.label}: default profile harness mismatch"
            )


def test_governed_catalog_carries_fragments_for_fragment_driven_steps() -> None:
    catalog = governed_workflow_catalog()
    impl = catalog.workflow("implementation")
    assert impl is not None
    implement = impl.step("implement")
    assert implement is not None
    assert implement.fragments, "implement step should carry fragment ids for snapshot fidelity"


def test_resolver_consumes_governed_catalog() -> None:
    """The resolver resolves a snapshot from the governed catalog (one source)."""
    resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
    snapshot = resolver.resolve("implementation")
    assert snapshot.workflow_id == "implementation"
    assert snapshot.steps, "snapshot has no steps"
    for entry in snapshot.steps:
        profile = model_profiles.resolve(entry.model_profile)
        assert entry.model == profile.model_id
        assert entry.harness == profile.harness


def test_resolver_rejects_unknown_step_override_against_governed_catalog() -> None:
    from dadaia_workspace.features.lifecycle.policy_resolver import (
        PolicyResolutionError,
        StepOverride,
    )

    resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
    with pytest.raises(PolicyResolutionError):
        resolver.resolve(
            "implementation",
            cli_overrides=(StepOverride(step="no_such_step", profile_id="codex-review-deep"),),
        )


# ---------------------------------------------------------------------------
# Single-source guarantee: import-time assert ties defaults to the registry
# ---------------------------------------------------------------------------


def test_assert_catalog_defaults_resolve_is_exposed_and_idempotent() -> None:
    # The module ran its guard at import time; calling it again must not raise.
    dadaia_catalog._assert_catalog_defaults_resolve()


# ---------------------------------------------------------------------------
# Wave B (T-29-B-01): closure cataloged as its real single worker step
# ---------------------------------------------------------------------------


def test_catalog_enumerates_closure_workflow() -> None:
    names = {w.name for w in list_dadaia_workflows()}
    assert "closure" in names


def test_closure_has_the_real_close_worker_step() -> None:
    closure = get_dadaia_workflow("closure")
    assert closure is not None
    labels = [s.label for s in closure.steps]
    assert "close" in labels
    close_step = next(s for s in closure.steps if s.label == "close")
    # The real close verb runs the product-engineer role (lifecycle.py:957).
    assert close_step.role == "product-engineer"
    # It is a worker (model) step, so it carries harness/model options + defaults.
    assert close_step.harness_options
    assert close_step.default_harness in close_step.default_profiles


def test_closure_models_the_removal_post_step_as_a_gate() -> None:
    closure = get_dadaia_workflow("closure")
    assert closure is not None
    gate = next((s for s in closure.steps if s.label == "closure_removal_gate"), None)
    assert gate is not None, "closure_removal_gate Python gate step missing"
    assert gate.is_gate is True
    # A Python-owned gate runs no worker — no harness/model/default profile.
    assert gate.harness_options == []
    assert gate.default_harness is None
    assert gate.default_profiles == {}


def test_closure_availability_is_partial_generic_worker() -> None:
    closure = get_dadaia_workflow("closure")
    assert closure is not None
    # closure's worker is generic (no fragment) — cataloged honestly as partial.
    assert closure.availability == dadaia_catalog.AVAILABILITY_PARTIAL


def test_closure_close_step_is_generic_no_fragment() -> None:
    """The real close verb has no fragment, so per WMP-5 it carries no output schema."""
    closure = get_dadaia_workflow("closure")
    assert closure is not None
    close_step = next(s for s in closure.steps if s.label == "close")
    assert close_step.fragment_id is None


def test_governed_catalog_carries_closure_with_close_step() -> None:
    catalog = governed_workflow_catalog()
    closure = catalog.workflow("closure")
    assert closure is not None
    close_step = closure.step("close")
    assert close_step is not None
    # A generic worker step carries no output schema (WMP-5 exemption).
    assert close_step.output_schema is None


def test_resolver_resolves_closure_policy() -> None:
    resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
    snapshot = resolver.resolve("closure")
    assert snapshot.workflow_id == "closure"
    labels = {e.step for e in snapshot.steps}
    assert "close" in labels
    for entry in snapshot.steps:
        profile = model_profiles.resolve(entry.model_profile)
        assert entry.harness == profile.harness


# ---------------------------------------------------------------------------
# Wave B (T-29-B-02) → Wave E (T-30-E-04): all 7 workflows enumerated.
# audit / research / bug_report ship real fragment+gate bodies as of v0.1.30 Wave E, so
# they are AVAILABLE with real governed steps — no longer deferred zero-step stubs.
# ---------------------------------------------------------------------------

#: The three workflows that became real fragment+gate bodies in v0.1.30 Wave E, with their
#: expected step labels (model steps + the terminal Python gate).
_WAVE_E_BODIES: dict[str, list[str]] = {
    "audit": ["audit_scope", "drift_scan", "triage", "audit_disposition_gate"],
    "research": ["research_scope", "investigate", "synthesis", "research_synthesis_gate"],
    "bug_report": ["bug_intake", "dedupe", "bug_write", "bug_record_gate"],
}


def test_catalog_enumerates_all_seven_workflows() -> None:
    """AC-7: every dadaia-workflow is enumerable in the catalog with availability."""
    names = {w.name for w in list_dadaia_workflows()}
    assert names == {
        "release_definition",
        "implementation",
        "backlog_definition",
        "closure",
        "audit",
        "research",
        "bug_report",
    }


def test_no_workflow_remains_deferred() -> None:
    """Wave E: DEFERRED_WORKFLOWS is empty — no workflow is cataloged as deferred."""
    from dadaia_workspace.features.lifecycle.workflows._deferred import DEFERRED_WORKFLOWS

    assert DEFERRED_WORKFLOWS == ()
    deferred = [
        w for w in list_dadaia_workflows() if w.availability == dadaia_catalog.AVAILABILITY_DEFERRED
    ]
    assert deferred == []


@pytest.mark.parametrize("name", sorted(_WAVE_E_BODIES))
def test_wave_e_body_available_with_real_steps(name: str) -> None:
    workflow = get_dadaia_workflow(name)
    assert workflow is not None
    assert workflow.availability == dadaia_catalog.AVAILABILITY_AVAILABLE
    assert [s.label for s in workflow.steps] == _WAVE_E_BODIES[name]
    assert workflow.step_count == len(_WAVE_E_BODIES[name])


@pytest.mark.parametrize("name", sorted(_WAVE_E_BODIES))
def test_wave_e_body_terminal_step_is_a_python_gate(name: str) -> None:
    workflow = get_dadaia_workflow(name)
    assert workflow is not None
    gate = workflow.steps[-1]
    assert gate.is_gate is True
    # A Python-owned terminal gate runs no worker — no harness/model/default profile.
    assert gate.harness_options == []
    assert gate.default_harness is None
    assert gate.default_profiles == {}


@pytest.mark.parametrize("name", sorted(_WAVE_E_BODIES))
def test_wave_e_body_is_governed_and_resolvable(name: str) -> None:
    """A real body is in the resolver seam and resolves a snapshot (no silent no-op)."""
    catalog = governed_workflow_catalog()
    governed = catalog.workflow(name)
    assert governed is not None

    resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
    snapshot = resolver.resolve(name)
    assert snapshot.workflow_id == name
    assert snapshot.steps, "snapshot has no governed steps"
    for entry in snapshot.steps:
        profile = model_profiles.resolve(entry.model_profile)
        assert entry.harness == profile.harness


# ---------------------------------------------------------------------------
# T-45-02 — node_meta enrichment of the card fluxogram (AC-1)
# ---------------------------------------------------------------------------


def test_node_meta_map_covers_every_worker_step() -> None:
    """The catalog node_meta builder maps each worker step's label to its default model."""
    for workflow in list_dadaia_workflows():
        meta = dadaia_catalog._node_meta_for_steps(workflow.steps)
        for step in workflow.steps:
            if step.default_harness is None:
                # Python-owned gate: no worker → omitted from the map.
                assert step.label not in meta
            else:
                assert step.label in meta, f"{workflow.name}.{step.label} missing node meta"
                node_meta = meta[step.label]
                assert node_meta.harness == step.default_harness
                profile = model_profiles.resolve(step.default_profiles[step.default_harness])
                assert node_meta.model == profile.model_id


def test_card_diagram_svg_carries_harness_model_line() -> None:
    """A card's diagram_svg is enriched with per-node harness/model (node-meta text)."""
    wf = get_dadaia_workflow("release_definition")
    assert wf is not None
    assert wf.diagram_svg
    # The enriched SVG carries the node-meta class (present only when node_meta is passed).
    assert "node-meta" in wf.diagram_svg
    # At least one governed harness label appears in the fluxogram.
    assert "codex" in wf.diagram_svg or "pi" in wf.diagram_svg


def test_card_diagram_svg_for_gate_only_context_stays_bare() -> None:
    """A workflow whose steps are all worker steps still enriches; gate nodes stay bare.

    closure has a generic worker (close) + a Python gate (closure_removal_gate). The worker
    node carries meta; the gate node label must not appear in the meta map.
    """
    meta = dadaia_catalog._node_meta_for_steps(get_dadaia_workflow("closure").steps)  # type: ignore[union-attr]
    assert "close" in meta
    assert "closure_removal_gate" not in meta
