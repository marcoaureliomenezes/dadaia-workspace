"""`extends` inheritance tests for the overlay store (T-30-C-03 / WS-OVERLAYS).

A non-``default`` context is honored via an ``extends`` chain (``context → extends… →
default``). The store parses + validates the graph; the accessors walk it. Contract
(A15/A16):

- a context resolves a step through its inheritance chain (nearest level wins);
- a **missing** ``extends`` parent is a hard validation error (never silent fallthrough);
- an ``extends`` **cycle** is rejected at parse time;
- ``default`` is the root and may not declare ``extends``;
- an overlay with **no** ``extends`` parses + resolves byte-identically (back-compat L7).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.workflow_execution import (
    WorkflowModelPolicyStoreError,
)
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _store(tmp_path: Path) -> JsonWorkflowModelPolicyStore:
    return JsonWorkflowModelPolicyStore(_workspace(tmp_path))


def test_extends_chain_resolution_nearest_wins_and_harness_inheritance(
    tmp_path: Path,
) -> None:
    """default defines `implement`; child overrides `review_qa`; grandchild overrides
    `implement`. The grandchild resolves its own `implement`, the child's
    `review_qa`, and inherits nothing else. A separate harness-only chain proves
    default_harness/step_harness inherit through `extends` the same way."""
    overlay = {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "default": {
                "workflows": {
                    "implementation": {"steps": {"implement": "codex-implementation-standard"}}
                }
            },
            "child": {
                "extends": "default",
                "workflows": {"implementation": {"steps": {"review_qa": "codex-review-deep"}}},
            },
            "grandchild": {
                "extends": "child",
                "workflows": {"implementation": {"steps": {"implement": "pi-reasoning-high"}}},
            },
        },
    }
    parsed = _store(tmp_path).parse(overlay)
    # grandchild's own override wins
    assert parsed.step_profile("grandchild", "implementation", "implement") == "pi-reasoning-high"
    # inherited from child
    assert parsed.step_profile("grandchild", "implementation", "review_qa") == "codex-review-deep"
    # nothing defines review_security anywhere in the chain
    assert parsed.step_profile("grandchild", "implementation", "review_security") is None

    harness_overlay = {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "default": {
                "workflows": {
                    "implementation": {
                        "steps": {},
                        "default_harness": "codex",
                        "harnesses": {"implement": "codex"},
                    }
                }
            },
            "pi-shop": {
                "extends": "default",
                "workflows": {"implementation": {"steps": {}, "default_harness": "pi"}},
            },
        },
    }
    parsed_harness = _store(tmp_path / "harness").parse(harness_overlay)
    # pi-shop overrides the default harness, inherits the per-step harness from default.
    assert parsed_harness.workflow_default_harness("pi-shop", "implementation") == "pi"
    assert parsed_harness.step_harness("pi-shop", "implementation", "implement") == "codex"


@pytest.mark.parametrize(
    ("overlay", "expected_message_fragments"),
    [
        pytest.param(
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "child": {
                        "extends": "nonexistent-parent",
                        "workflows": {"implementation": {"steps": {}}},
                    }
                },
            },
            ["nonexistent-parent", "unknown parent"],
            id="missing-extends-parent-is-hard-error",
        ),
        pytest.param(
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "a": {"extends": "b", "workflows": {}},
                    "b": {"extends": "a", "workflows": {}},
                },
            },
            ["cycle"],
            id="extends-cycle-is-rejected",
        ),
        pytest.param(
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {"a": {"extends": "a", "workflows": {}}},
            },
            [],  # either "extend itself" or "cycle" — checked separately below
            id="self-extends-is-rejected",
        ),
        pytest.param(
            {
                "schema_version": "workflow-model-policy-v1",
                "policy_id": "default",
                "contexts": {
                    "parent": {"workflows": {}},
                    "default": {"extends": "parent", "workflows": {}},
                },
            },
            ["root"],
            id="default-may-not-declare-extends",
        ),
    ],
)
def test_extends_validation_matrix(
    tmp_path: Path, overlay: dict[str, object], expected_message_fragments: list[str]
) -> None:
    with pytest.raises(WorkflowModelPolicyStoreError) as exc:
        _store(tmp_path).parse(overlay)
    message = str(exc.value).lower()
    if expected_message_fragments:
        for fragment in expected_message_fragments:
            assert fragment.lower() in message
    else:
        assert "extend itself" in message or "cycle" in message


def test_extends_default_root_is_valid_and_round_trips_through_save_load(
    tmp_path: Path,
) -> None:
    # A context may extend the 'default' root even when 'default' carries no overrides.
    overlay = {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "child": {
                "extends": "default",
                "workflows": {"implementation": {"steps": {"implement": "pi-reasoning-low"}}},
            }
        },
    }
    parsed = _store(tmp_path).parse(overlay)
    assert parsed.step_profile("child", "implementation", "implement") == "pi-reasoning-low"

    round_trip_overlay = {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "default": {"workflows": {}},
            "child": {
                "extends": "default",
                "workflows": {"implementation": {"steps": {"implement": "pi-reasoning-high"}}},
            },
        },
    }
    store = _store(tmp_path / "round-trip")
    parsed_rt = store.parse(round_trip_overlay)
    store.save(parsed_rt)
    loaded = store.load()
    assert loaded is not None
    assert loaded.extends == {"child": "default"}
    assert loaded.step_profile("child", "implementation", "implement") == "pi-reasoning-high"


def test_no_extends_back_compat_round_trip(tmp_path: Path) -> None:
    # L7: a v0.1.28/29-shaped overlay (no extends key anywhere) parses, resolves, and
    # round-trips byte-identically — to_dict carries no `extends` key.
    overlay = {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "default": {
                "workflows": {
                    "implementation": {"steps": {"implement": "codex-implementation-standard"}}
                }
            }
        },
    }
    store = _store(tmp_path)
    parsed = store.parse(overlay)
    assert parsed.extends == {}
    assert parsed.step_profile("default", "implementation", "implement") == (
        "codex-implementation-standard"
    )
    payload = parsed.to_dict()
    assert "extends" not in payload["contexts"]["default"]
    # round-trips through save/load unchanged
    store.save(parsed)
    loaded = store.load()
    assert loaded is not None
    assert loaded.extends == {}
    assert loaded.to_dict() == payload
