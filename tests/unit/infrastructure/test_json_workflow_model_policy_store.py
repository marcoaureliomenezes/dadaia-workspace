"""Unit tests for the workflow-model-policy overlay store (T-28-A-03).

Mirrors ``JsonLifecycleRunStore`` resilience: atomic temp+rename writes, a
``.last-good.json`` backup, and the load contract **missing != invalid** —
``load()`` returns ``None`` for an absent file (defaults) but raises a typed
``WorkflowModelPolicyStoreError`` for invalid JSON / unknown top-level fields /
wrong schema version. D-2: only the ``default`` context overlay is honored.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.workflow_execution import (
    WorkflowModelPolicyOverlay,
    WorkflowModelPolicyStoreError,
)
from dadaia_workspace.infrastructure.json_workflow_model_policy_store import (
    JsonWorkflowModelPolicyStore,
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir()
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


def test_missing_file_returns_none(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    assert store.load() is None  # missing == defaults, NOT an error


def test_path_is_canonical(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonWorkflowModelPolicyStore(workspace)
    assert store.path == workspace / ".dadaia" / "states" / "workflow_model_policy.json"


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    overlay = store.parse(_valid_overlay())
    store.save(overlay)
    loaded = store.load()
    assert loaded is not None
    assert loaded.policy_id == "default"
    assert loaded.step_profile("default", "implementation", "implement") == (
        "codex-implementation-standard"
    )


def test_save_then_load_round_trips_harness_only_workflow(tmp_path: Path) -> None:
    """A harness-only overlay (named only in default_harness/step_harness, no profile
    `steps`) must survive save→load — regression for
    `overlay-todict-drops-harness-only-workflow` (to_dict iterated only `contexts`)."""
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
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


def test_invalid_json_raises(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonWorkflowModelPolicyStore(workspace)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(WorkflowModelPolicyStoreError):
        store.load()


def test_unknown_top_level_field_raises(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonWorkflowModelPolicyStore(workspace)
    bad = _valid_overlay()
    bad["bogus_field"] = 1
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(WorkflowModelPolicyStoreError) as exc:
        store.load()
    assert "bogus_field" in str(exc.value)


def test_wrong_schema_version_raises(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonWorkflowModelPolicyStore(workspace)
    bad = _valid_overlay()
    bad["schema_version"] = "workflow-model-policy-v999"
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(WorkflowModelPolicyStoreError):
        store.load()


def test_root_not_object_raises(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonWorkflowModelPolicyStore(workspace)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(WorkflowModelPolicyStoreError):
        store.load()


def test_save_writes_last_good_backup_from_prior_valid_file(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    first = store.parse(_valid_overlay())
    store.save(first)
    prior_bytes = store.path.read_bytes()

    second = _valid_overlay()
    second["policy_id"] = "v2"
    store.save(store.parse(second))

    last_good = store.path.with_suffix(".json.last-good.json")
    assert last_good.is_file()
    # last-good holds the PRIOR valid file's bytes
    assert last_good.read_bytes() == prior_bytes
    loaded = store.load()
    assert loaded is not None
    assert loaded.policy_id == "v2"


def test_first_save_has_no_last_good(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    store.save(store.parse(_valid_overlay()))
    last_good = store.path.with_suffix(".json.last-good.json")
    assert not last_good.exists()


def test_save_is_atomic_no_tmp_left_behind(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonWorkflowModelPolicyStore(workspace)
    store.save(store.parse(_valid_overlay()))
    states = workspace / ".dadaia" / "states"
    leftovers = [p for p in states.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


def test_only_default_context_honored(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    overlay = _valid_overlay()
    contexts = overlay["contexts"]
    assert isinstance(contexts, dict)
    contexts["other-ctx"] = {
        "workflows": {"implementation": {"steps": {"implement": "pi-reasoning-high"}}}
    }
    parsed = store.parse(overlay)
    # default context override is honored
    assert parsed.step_profile("default", "implementation", "implement") == (
        "codex-implementation-standard"
    )
    # WS-OVERLAYS (replaces the D-2 collapse): a non-default context IS now honored. Here
    # 'other-ctx' declares its own override and inherits 'default' for anything it omits.
    assert parsed.step_profile("other-ctx", "implementation", "implement") == "pi-reasoning-high"


def test_step_profile_absent_returns_none(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    parsed = store.parse(_valid_overlay())
    assert parsed.step_profile("default", "implementation", "missing-step") is None
    assert parsed.step_profile("default", "missing-workflow", "implement") is None


# ---------------------------------------------------------------------------
# v0.1.29 / T-29-A-04 — overlay carries harness (default_harness + per-step harnesses)
# ---------------------------------------------------------------------------


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


def test_back_compat_overlay_without_harness_parses(tmp_path: Path) -> None:
    # A v0.1.28-shaped overlay (no harness fields) parses and exposes empty accessors.
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    parsed = store.parse(_valid_overlay())
    assert parsed.workflow_default_harness("default", "implementation") is None
    assert parsed.step_harness("default", "implementation", "implement") is None


def test_harness_overlay_parses_accessors(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    parsed = store.parse(_harness_overlay())
    assert parsed.workflow_default_harness("default", "implementation") == "pi"
    assert parsed.step_harness("default", "implementation", "implement") == "codex"
    assert parsed.step_harness("default", "implementation", "review_qa") is None


def test_harness_overlay_round_trips(tmp_path: Path) -> None:
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    parsed = store.parse(_harness_overlay())
    store.save(parsed)
    loaded = store.load()
    assert loaded is not None
    assert loaded.workflow_default_harness("default", "implementation") == "pi"
    assert loaded.step_harness("default", "implementation", "implement") == "codex"


def test_harness_overlay_to_dict_omits_empty_fields(tmp_path: Path) -> None:
    # to_dict omits empty harness fields for a byte-stable v0.1.28-compatible round-trip.
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    parsed = store.parse(_valid_overlay())
    payload = parsed.to_dict()
    wf = payload["contexts"]["default"]["workflows"]["implementation"]
    assert "default_harness" not in wf
    assert "harnesses" not in wf


def test_non_default_harness_context_now_honored(tmp_path: Path) -> None:
    # WS-OVERLAYS (replaces the D-2 collapse): a non-default context's harness overlay is
    # now honored. 'other' declares its own default_harness and inherits 'default' for the
    # per-step harness it omits.
    store = JsonWorkflowModelPolicyStore(_workspace(tmp_path))
    overlay = _harness_overlay()
    contexts = overlay["contexts"]
    assert isinstance(contexts, dict)
    contexts["other"] = {
        "workflows": {"implementation": {"default_harness": "pi", "harnesses": {}}}
    }
    parsed = store.parse(overlay)
    assert parsed.workflow_default_harness("other", "implementation") == "pi"
    # 'other' omits the per-step harness, so it inherits the 'default' context value.
    assert parsed.step_harness("other", "implementation", "implement") == "codex"
