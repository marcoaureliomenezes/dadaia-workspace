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

from dadaia_workspace.core.models.workflow_execution import (
    PolicySource,
    WorkflowModelPolicyOverlay,
)
from dadaia_workspace.features.lifecycle.policy_resolver import (
    PolicyResolutionError,
    WorkflowExecutionPolicyResolver,
)
from dadaia_workspace.features.workflows.dadaia_catalog import governed_workflow_catalog
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)

_WORKFLOW = "implementation_reviews"


def _resolver(overlay: WorkflowModelPolicyOverlay | None = None) -> WorkflowExecutionPolicyResolver:
    return WorkflowExecutionPolicyResolver(catalog=governed_workflow_catalog(), overlay=overlay)


def _parse(document: dict[str, object], tmp_path) -> WorkflowModelPolicyOverlay:  # type: ignore[no-untyped-def]
    (tmp_path / ".dadaia").mkdir(exist_ok=True)
    return JsonWorkflowModelPolicyStore(tmp_path).parse(document)


# --- ① extends-chain: inherit + child-wins ----------------------------------------------


def test_extends_chain_inherits_and_child_override_wins(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # default overrides implement -> codex-review-deep (a valid codex profile for that step);
    # child inherits it via extends.
    inherit_overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation_reviews": {"steps": {"implement": "codex-review-deep"}}
                    }
                },
                "child": {"extends": "default", "workflows": {}},
            },
        },
        tmp_path,
    )
    inherited = _resolver(inherit_overlay).resolve(_WORKFLOW, context="child")
    impl = inherited.step("implement")
    assert impl is not None
    assert impl.model_profile == "codex-review-deep"
    assert impl.source is PolicySource.DEFAULT_OVERLAY

    child_wins_overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation_reviews": {"steps": {"implement": "codex-review-deep"}}
                    }
                },
                "pi-shop": {
                    "extends": "default",
                    "workflows": {
                        "implementation_reviews": {
                            "steps": {"implement": "pi-reasoning-high"},
                            "harnesses": {"implement": "pi"},
                        }
                    },
                },
            },
        },
        tmp_path,
    )
    child = _resolver(child_wins_overlay).resolve(_WORKFLOW, context="pi-shop")
    child_impl = child.step("implement")
    assert child_impl is not None
    assert child_impl.model_profile == "pi-reasoning-high"
    assert child_impl.harness == "pi"


# --- ② fail-closed param: unknown profile / stale step id in chain / harness mismatch ---

_FAIL_CLOSED_CASES = (
    (
        "unknown-profile",
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "child": {
                    "extends": "default",
                    "workflows": {
                        "implementation_reviews": {"steps": {"implement": "no-such-profile"}}
                    },
                }
            },
        },
        "child",
        None,
    ),
    (
        "harness-profile-mismatch",
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "child": {
                    "extends": "default",
                    "workflows": {
                        "implementation_reviews": {"steps": {"implement": "pi-reasoning-high"}}
                    },
                }
            },
        },
        "child",
        None,
    ),
)


@pytest.mark.parametrize(
    "document,context,expected_substring",
    [c[1:] for c in _FAIL_CLOSED_CASES],
    ids=[c[0] for c in _FAIL_CLOSED_CASES],
)
def test_fail_closed_matrix(
    tmp_path, document: dict[str, object], context: str, expected_substring: str | None
) -> None:  # type: ignore[no-untyped-def]
    overlay = _parse(document, tmp_path)
    with pytest.raises(PolicyResolutionError) as exc:
        _resolver(overlay).resolve(_WORKFLOW, context=context)
    if expected_substring is not None:
        assert expected_substring in str(exc.value)


def test_a_stale_step_id_in_the_chain_warns_instead_of_failing_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Deliberate contract change (bug r13-release-definition-rejects-legacy-overlay).

    A stale step id in the inherited chain used to fail closed. That is right for a CLI
    override — the operator just typed it — but a PERSISTED overlay is old state, and
    raising turned a library upgrade into a bricked workspace: four of the consumer-side
    validator's five R13 failures were this one cause, with no path forward but editing
    JSON by hand.

    Fail-closed is preserved where it protects (unknown profile, harness mismatch,
    unknown workflow — still in the matrix above). Here the entry is dropped and NAMED,
    and `dadaia policy doctor` still reports it as an ERROR, so wrong state is still
    diagnosed; it just no longer stops the operator from working.
    """
    overlay = _parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {
                        "implementation_reviews": {"steps": {"ghost-step": "codex-review-deep"}}
                    }
                },
                "child": {"extends": "default", "workflows": {}},
            },
        },
        tmp_path,
    )

    snapshot = _resolver(overlay).resolve(_WORKFLOW, context="child")

    assert "ghost-step" in " ".join(snapshot.warnings), snapshot.warnings
    assert "ghost-step" not in {entry.step for entry in snapshot.steps}
