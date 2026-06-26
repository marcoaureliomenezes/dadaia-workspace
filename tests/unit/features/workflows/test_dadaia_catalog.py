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
