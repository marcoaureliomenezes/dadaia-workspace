"""Unit tests for ``features/workflows/dadaia_catalog`` — T-28-B-01.

Wave B makes the dadaia-workflow catalog the **governed source of truth**: every
worker (model) step carries a ``default_harness`` plus a ``default_profile`` for each
supported harness, every default profile id resolves in the built-in
:mod:`model_profiles` registry, and the catalog satisfies the resolver's
:class:`WorkflowCatalog` seam (one source — no second table).

Catalog-resolves invariant prevents unresolvable dispatch at runtime, so
every-default-profile-resolves-in-registry and no-workflow-remains-deferred are kept
as named tests. node_meta/SVG rendering facets are owned by the golden
(test_dadaia_catalog_golden.py), which pins ``diagram_svg`` byte-for-byte including
node-meta markup — not duplicated here.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.lifecycle import model_profiles
from dadaia_workspace.features.lifecycle.policy_resolver import (
    PolicyResolutionError,
    StepOverride,
    WorkflowCatalog,
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.features.workflows import dadaia_catalog
from dadaia_workspace.features.workflows.dadaia_catalog import (
    DEFERRED_WORKFLOWS,
    DadaiaWorkflowDTO,
    DadaiaWorkflowStepDTO,
    get_dadaia_workflow,
    governed_workflow_catalog,
    list_dadaia_workflows,
)


def _worker_steps(workflow: DadaiaWorkflowDTO) -> list[DadaiaWorkflowStepDTO]:
    return [s for s in workflow.steps if s.harness_options]


# ---------------------------------------------------------------------------
# CRITICAL: every default profile id resolves in the registry (never-unresolvable-dispatch)
# ---------------------------------------------------------------------------


def test_every_default_profile_id_resolves_in_registry() -> None:
    for workflow in list_dadaia_workflows():
        for step in _worker_steps(workflow):
            for harness, profile_id in step.default_profiles.items():
                profile = model_profiles.resolve(profile_id)
                assert profile.harness == harness, (
                    f"{workflow.name}.{step.label}: default profile {profile_id!r} runs on "
                    f"{profile.harness!r}, declared as default for {harness!r}"
                )


def test_no_workflow_remains_deferred() -> None:
    """Wave E: DEFERRED_WORKFLOWS is empty — no workflow is cataloged as deferred."""
    assert DEFERRED_WORKFLOWS == ()
    deferred = [
        w for w in list_dadaia_workflows() if w.availability == dadaia_catalog.AVAILABILITY_DEFERRED
    ]
    assert deferred == []


# ---------------------------------------------------------------------------
# Per-step default invariants: harness/profile/gates/deep-review — 1 param test
# ---------------------------------------------------------------------------


def test_per_step_default_invariants() -> None:
    for workflow in list_dadaia_workflows():
        for step in _worker_steps(workflow):
            # every worker step has a default_harness in harness_options.
            assert step.default_harness, (
                f"{workflow.name}.{step.label} worker step has no default_harness"
            )
            assert step.default_harness in step.harness_options
            # every worker step has a default profile per supported harness.
            for harness in step.harness_options:
                assert harness in step.default_profiles, (
                    f"{workflow.name}.{step.label} missing default profile for {harness!r}"
                )
            # the default harness itself has a default profile.
            assert step.default_harness in step.default_profiles

        # gate steps carry no default harness/profile.
        for step in workflow.steps:
            if not step.harness_options:
                assert step.default_harness is None
                assert step.default_profiles == {}

    # review/gate worker steps default to a deep-reasoning profile; worker steps to standard.
    impl = get_dadaia_workflow("implementation")
    assert impl is not None
    review = next(s for s in impl.steps if s.label == "review_qa")
    implement = next(s for s in impl.steps if s.label == "implement")
    assert review.default_harness is not None
    assert implement.default_harness is not None
    assert "review" in review.default_profiles[review.default_harness]
    assert "implementation" in implement.default_profiles[implement.default_harness]


# ---------------------------------------------------------------------------
# Governed-catalog + resolver: consumes/rejects/idempotent — 1 test
# ---------------------------------------------------------------------------


def test_governed_catalog_and_resolver_contract() -> None:
    catalog = governed_workflow_catalog()
    assert isinstance(catalog, WorkflowCatalog)
    assert catalog.workflows, "governed catalog has no workflows"

    impl = catalog.workflow("implementation")
    assert impl is not None
    labels = {s.label for s in impl.steps}
    assert {"implement", "review_qa", "review_security", "review_code"} <= labels

    # every governed step's default profile resolves and matches the harness.
    for workflow in catalog.workflows:
        for step in workflow.steps:
            profile = model_profiles.resolve(step.default_profile)
            assert profile.harness == step.default_harness, (
                f"{workflow.workflow_id}.{step.label}: default profile harness mismatch"
            )

    # fragment-driven steps carry fragment ids for snapshot fidelity.
    implement_step = impl.step("implement")
    assert implement_step is not None
    assert implement_step.fragments, "implement step should carry fragment ids"

    # the resolver consumes the governed catalog (one source).
    resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
    snapshot = resolver.resolve("implementation")
    assert snapshot.workflow_id == "implementation"
    assert snapshot.steps, "snapshot has no steps"
    for entry in snapshot.steps:
        profile = model_profiles.resolve(entry.model_profile)
        assert entry.model == profile.model_id
        assert entry.harness == profile.harness

    # the resolver rejects an override targeting an unknown step.
    with pytest.raises(PolicyResolutionError):
        resolver.resolve(
            "implementation",
            cli_overrides=(StepOverride(step="no_such_step", profile_id="codex-review-deep"),),
        )

    # the import-time single-source guard is exposed and idempotent to re-invoke.
    dadaia_catalog._assert_catalog_defaults_resolve()


# ---------------------------------------------------------------------------
# Closure block + Wave-E trio + seven-workflows enumeration — 1 test
# ---------------------------------------------------------------------------


#: The three workflows that became real fragment+gate bodies in v0.1.30 Wave E, with their
#: expected step labels (model steps + the terminal Python gate).
_WAVE_E_BODIES: dict[str, list[str]] = {
    "audit": ["audit_scope", "drift_scan", "triage", "audit_disposition_gate"],
    "research": ["research_scope", "investigate", "synthesis", "research_synthesis_gate"],
    "bug_report": ["bug_intake", "dedupe", "bug_write", "bug_record_gate"],
}


def test_seven_workflows_closure_and_wave_e_bodies() -> None:
    # AC-7: every dadaia-workflow is enumerable in the catalog.
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

    # closure carries the real close worker step + the removal gate as a Python gate.
    closure = get_dadaia_workflow("closure")
    assert closure is not None
    labels = [s.label for s in closure.steps]
    assert "close" in labels
    close_step = next(s for s in closure.steps if s.label == "close")
    assert close_step.role == "product-engineer"
    assert close_step.harness_options
    assert close_step.default_harness in close_step.default_profiles
    assert close_step.fragment_id is None  # generic worker — no fragment (WMP-5)

    gate = next((s for s in closure.steps if s.label == "closure_removal_gate"), None)
    assert gate is not None
    assert gate.is_gate is True
    assert gate.harness_options == []
    assert gate.default_harness is None
    assert gate.default_profiles == {}

    assert closure.availability == dadaia_catalog.AVAILABILITY_PARTIAL

    catalog = governed_workflow_catalog()
    governed_closure = catalog.workflow("closure")
    assert governed_closure is not None
    governed_close_step = governed_closure.step("close")
    assert governed_close_step is not None
    assert governed_close_step.output_schema is None  # WMP-5 exemption

    closure_resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
    closure_snapshot = closure_resolver.resolve("closure")
    assert closure_snapshot.workflow_id == "closure"
    closure_labels = {e.step for e in closure_snapshot.steps}
    assert "close" in closure_labels
    for entry in closure_snapshot.steps:
        profile = model_profiles.resolve(entry.model_profile)
        assert entry.harness == profile.harness

    # Wave E bodies: available, real steps, terminal Python gate, governed+resolvable.
    for name, expected_labels in _WAVE_E_BODIES.items():
        workflow = get_dadaia_workflow(name)
        assert workflow is not None
        assert workflow.availability == dadaia_catalog.AVAILABILITY_AVAILABLE
        assert [s.label for s in workflow.steps] == expected_labels
        assert workflow.step_count == len(expected_labels)

        terminal_gate = workflow.steps[-1]
        assert terminal_gate.is_gate is True
        assert terminal_gate.harness_options == []
        assert terminal_gate.default_harness is None
        assert terminal_gate.default_profiles == {}

        wave_e_governed = catalog.workflow(name)
        assert wave_e_governed is not None
        wave_e_resolver = WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog())
        wave_e_snapshot = wave_e_resolver.resolve(name)
        assert wave_e_snapshot.workflow_id == name
        assert wave_e_snapshot.steps, "snapshot has no governed steps"
        for entry in wave_e_snapshot.steps:
            profile = model_profiles.resolve(entry.model_profile)
            assert entry.harness == profile.harness
