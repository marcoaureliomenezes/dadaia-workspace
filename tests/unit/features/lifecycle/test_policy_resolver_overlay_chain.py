"""Resolver per-context `extends` chain resolution tests (T-30-C-04 / WS-OVERLAYS, A15).

The :class:`WorkflowExecutionPolicyResolver` resolves a step's profile/harness through the
bound overlay's per-context ``extends`` chain. Contract:

- a non-``default`` context resolves a step through its inheritance chain;
- an unresolvable ref (unknown profile / harness mismatch / stale overlay step id anywhere
  in the chain) fails closed with ``PolicyResolutionError``;
- an overlay with no per-context keys resolves library defaults unchanged (back-compat).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.workflow_execution import PolicySource
from dadaia_workspace.features.lifecycle.policy_resolver import (
    PolicyResolutionError,
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
    WorkflowModelPolicyOverlay,
)

_WORKFLOW = "implementation"


def _resolver(overlay: WorkflowModelPolicyOverlay | None = None) -> WorkflowExecutionPolicyResolver:
    return WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog(), overlay=overlay)


def _parse(document: dict[str, object], tmp_path) -> WorkflowModelPolicyOverlay:  # type: ignore[no-untyped-def]
    (tmp_path / ".dadaia").mkdir(exist_ok=True)
    return JsonWorkflowModelPolicyStore(tmp_path).parse(document)


def test_chain_resolves_inherited_profile(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # default overrides implement -> codex-review-deep (a valid codex profile for that step);
    # child inherits it via extends.
    overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "codex-review-deep"}}}
                },
                "child": {"extends": "default", "workflows": {}},
            },
        },
        tmp_path,
    )
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="child")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-review-deep"
    assert impl.source is PolicySource.DEFAULT_OVERLAY


def test_child_override_wins_over_inherited(tmp_path) -> None:  # type: ignore[no-untyped-def]
    overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "codex-review-deep"}}}
                },
                "pi-shop": {
                    "extends": "default",
                    "workflows": {
                        "implementation": {
                            "steps": {"implement": "pi-reasoning-high"},
                            "harnesses": {"implement": "pi"},
                        }
                    },
                },
            },
        },
        tmp_path,
    )
    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="pi-shop")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.model_profile == "pi-reasoning-high"
    assert impl.harness == "pi"


def test_unresolvable_overlay_ref_fails_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # A context override naming an unknown profile is a hard failure (fail-closed).
    overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "child": {
                    "extends": "default",
                    "workflows": {"implementation": {"steps": {"implement": "no-such-profile"}}},
                }
            },
        },
        tmp_path,
    )
    with pytest.raises(PolicyResolutionError):
        _resolver(overlay).resolve(_WORKFLOW, context="child")


def test_stale_overlay_step_in_chain_fails_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"ghost-step": "codex-review-deep"}}}
                },
                "child": {"extends": "default", "workflows": {}},
            },
        },
        tmp_path,
    )
    with pytest.raises(PolicyResolutionError) as exc:
        _resolver(overlay).resolve(_WORKFLOW, context="child")
    assert "ghost-step" in str(exc.value)


def test_harness_profile_mismatch_in_overlay_fails_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # A pi profile on a step that resolves to codex (no harness override) is a mismatch.
    overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "child": {
                    "extends": "default",
                    "workflows": {"implementation": {"steps": {"implement": "pi-reasoning-high"}}},
                }
            },
        },
        tmp_path,
    )
    with pytest.raises(PolicyResolutionError):
        _resolver(overlay).resolve(_WORKFLOW, context="child")
