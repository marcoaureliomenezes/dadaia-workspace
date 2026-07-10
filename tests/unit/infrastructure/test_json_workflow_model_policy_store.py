"""Unit tests for the workflow-model-policy overlay store (T-28-A-03).

Mirrors ``JsonLifecycleRunStore`` resilience: atomic temp+rename writes, a
``.last-good.json`` backup, and the load contract **missing != invalid** —
``load()`` returns ``None`` for an absent file (defaults) but raises a typed
``WorkflowModelPolicyStoreError`` for invalid JSON / unknown top-level fields /
wrong schema version. D-2: only the ``default`` context overlay was honored
pre-WS-OVERLAYS; a non-default context is now honored via inheritance (see
``test_workflow_model_policy_extends.py`` for the extends-graph coverage).

The generic load/parse/save+last-good store contract is asserted once via the
shared ``_store_contract`` helpers; this file keeps the store-specific logic: the
harness-only-overlay round-trip bug regression, and the harness accessor /
back-compat / non-default-context-honored behavior.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.workflow_execution import (
    WorkflowModelPolicyOverlay,
    WorkflowModelPolicyStoreError,
)
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)

from ._store_contract import (
    assert_corrupt_json_raises_typed_error,
    assert_last_good_snapshot_of_prior_valid_file,
    assert_missing_file_loads_default,
    assert_root_not_object_rejected,
    assert_save_is_atomic_no_tmp_leftover,
    assert_unknown_top_level_field_rejected,
    assert_wrong_schema_version_rejected,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _valid_overlay() -> dict[str, object]:
    return {
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


def _harness_overlay() -> dict[str, object]:
    return {
        "schema_version": "workflow-model-policy-v1",
        "policy_id": "default",
        "contexts": {
            "default": {
                "workflows": {
                    "implementation": {
                        "steps": {},
                        "default_harness": "pi",
                        "harnesses": {"implement": "codex"},
                    }
                }
            }
        },
    }


def test_load_and_save_contract(tmp_path: Path) -> None:
    """missing->None / corrupt / unknown-field / wrong schema_version / non-object
    root / atomic-no-tmp / last-good snapshot — the shared store-contract template."""
    assert_missing_file_loads_default(JsonWorkflowModelPolicyStore(_workspace(tmp_path)), None)
    assert_corrupt_json_raises_typed_error(
        JsonWorkflowModelPolicyStore(_workspace(tmp_path / "corrupt")),
        WorkflowModelPolicyStoreError,
    )
    assert_unknown_top_level_field_rejected(
        JsonWorkflowModelPolicyStore(_workspace(tmp_path / "unknown")),
        _valid_overlay(),
        WorkflowModelPolicyStoreError,
        bogus_key="bogus_field",
    )
    assert_wrong_schema_version_rejected(
        JsonWorkflowModelPolicyStore(_workspace(tmp_path / "schema")),
        _valid_overlay(),
        WorkflowModelPolicyStoreError,
        "workflow-model-policy-v999",
    )
    assert_root_not_object_rejected(
        JsonWorkflowModelPolicyStore(_workspace(tmp_path / "root")),
        WorkflowModelPolicyStoreError,
    )

    atomic_store = JsonWorkflowModelPolicyStore(_workspace(tmp_path / "atomic"))
    assert_save_is_atomic_no_tmp_leftover(atomic_store, atomic_store.parse(_valid_overlay()))

    last_good_store = JsonWorkflowModelPolicyStore(_workspace(tmp_path / "lastgood"))
    second = _valid_overlay()
    second["policy_id"] = "v2"
    assert_last_good_snapshot_of_prior_valid_file(
        last_good_store,
        last_good_store.parse(_valid_overlay()),
        last_good_store.parse(second),
    )
    loaded_after = last_good_store.load()
    assert loaded_after is not None
    assert loaded_after.policy_id == "v2"


def test_save_then_load_round_trips_and_harness_only_overlay_round_trips(
    tmp_path: Path,
) -> None:
    """A harness-only overlay (named only in default_harness/step_harness, no profile
    `steps`) must survive save→load — regression for
    `overlay-todict-drops-harness-only-workflow` (to_dict iterated only `contexts`).
    This is the ONLY coverage of that regression — keep verbatim."""
    plain_store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    plain_overlay = plain_store.parse(_valid_overlay())
    plain_store.save(plain_overlay)
    loaded_plain = plain_store.load()
    assert loaded_plain is not None
    assert loaded_plain.policy_id == "default"
    assert loaded_plain.step_profile("default", "implementation", "implement") == (
        "codex-implementation-standard"
    )

    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path / "harness-only"))
    overlay = WorkflowModelPolicyOverlay(
        policy_id="default",
        contexts={},
        default_harness_overlay={"default": {"implementation": "pi"}},
        step_harness_overlay={"default": {"implementation": {"implement": "pi"}}},
    )
    store.save(overlay)
    loaded = store.load()
    assert loaded is not None
    assert loaded.workflow_default_harness("default", "implementation") == "pi"
    assert loaded.step_harness("default", "implementation", "implement") == "pi"


def test_harness_accessors_back_compat_and_non_default_context(tmp_path: Path) -> None:
    """v0.1.29/T-29-A-04 harness accessors: a v0.1.28-shaped overlay (no harness
    fields) parses with empty accessors and to_dict omits empty harness fields
    (byte-stable back-compat round-trip); a harness overlay parses/round-trips its
    accessors; and (WS-OVERLAYS) a non-default context's own harness overlay is
    honored, inheriting whatever it omits from 'default'."""
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))

    # Back-compat: no harness fields anywhere.
    parsed_plain = store.parse(_valid_overlay())
    assert parsed_plain.workflow_default_harness("default", "implementation") is None
    assert parsed_plain.step_harness("default", "implementation", "implement") is None
    payload = parsed_plain.to_dict()
    wf = payload["contexts"]["default"]["workflows"]["implementation"]
    assert "default_harness" not in wf
    assert "harnesses" not in wf

    # Harness overlay parses accessors and round-trips through save/load.
    parsed_harness = store.parse(_harness_overlay())
    assert parsed_harness.workflow_default_harness("default", "implementation") == "pi"
    assert parsed_harness.step_harness("default", "implementation", "implement") == "codex"
    assert parsed_harness.step_harness("default", "implementation", "review_qa") is None
    store.save(parsed_harness)
    loaded = store.load()
    assert loaded is not None
    assert loaded.workflow_default_harness("default", "implementation") == "pi"
    assert loaded.step_harness("default", "implementation", "implement") == "codex"

    # Non-default context: own default_harness honored, per-step harness inherited.
    overlay = _harness_overlay()
    contexts = overlay["contexts"]
    assert isinstance(contexts, dict)
    contexts["other"] = {
        "workflows": {"implementation": {"default_harness": "pi", "harnesses": {}}}
    }
    parsed_other = store.parse(overlay)
    assert parsed_other.workflow_default_harness("other", "implementation") == "pi"
    assert parsed_other.step_harness("other", "implementation", "implement") == "codex"

    # Non-default context: profile step also honored via inheritance (D-2 replacement).
    overlay2 = _valid_overlay()
    contexts2 = overlay2["contexts"]
    assert isinstance(contexts2, dict)
    contexts2["other-ctx"] = {
        "workflows": {"implementation": {"steps": {"implement": "pi-reasoning-high"}}}
    }
    parsed2 = store.parse(overlay2)
    assert parsed2.step_profile("default", "implementation", "implement") == (
        "codex-implementation-standard"
    )
    assert parsed2.step_profile("other-ctx", "implementation", "implement") == "pi-reasoning-high"
