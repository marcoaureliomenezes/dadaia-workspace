"""JsonAgentModelPolicyStore: the shared store contract, the load-rejection matrix, the
refusal of ``overrides`` with its runnable fix, and the ``applied_template``-only round trip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.model_registry import (
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
)
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)
from tests.fixtures._store_contract import (
    assert_corrupt_json_raises_typed_error,
    assert_last_good_snapshot_of_prior_valid_file,
    assert_missing_file_loads_default,
    assert_save_is_atomic_no_tmp_leftover,
    assert_saved_value_reloads_identically,
    assert_unknown_top_level_field_rejected,
    assert_wrong_schema_version_rejected,
)


def _store(tmp_path: Path, **kwargs: object) -> JsonAgentModelPolicyStore:
    return JsonAgentModelPolicyStore(tmp_path, **kwargs)  # type: ignore[arg-type]


def _valid_doc() -> dict[str, object]:
    return {
        "schema_version": "agent-model-policy-v1",
        "applied_template": "max-quality",
    }


def test_load_contract(tmp_path: Path) -> None:
    assert _store(tmp_path).path == tmp_path / ".dadaia" / "states" / "agent_model_policy.json"
    assert_missing_file_loads_default(_store(tmp_path), None)
    assert_corrupt_json_raises_typed_error(_store(tmp_path), AgentModelPolicyStoreError)
    assert_unknown_top_level_field_rejected(
        _store(tmp_path), _valid_doc(), AgentModelPolicyStoreError, bogus_key="surprise"
    )
    assert_wrong_schema_version_rejected(
        _store(tmp_path), _valid_doc(), AgentModelPolicyStoreError, "agent-model-policy-v0"
    )


@pytest.mark.parametrize(
    ("doc", "match"),
    [
        pytest.param([], "root is not an object", id="root-not-object"),
        pytest.param(
            {**_valid_doc(), "applied_template": "turbo-mode"},
            "unknown.*template.*turbo-mode",
            id="unknown-template",
        ),
    ],
)
def test_load_rejection_matrix(tmp_path: Path, doc: object, match: str) -> None:
    store = _store(tmp_path)
    store.path.parent.mkdir(parents=True)
    store.path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(AgentModelPolicyStoreError, match=match):
        store.load()


@pytest.mark.parametrize(
    ("applied_template", "command"),
    [
        pytest.param(
            "max-quality",
            "dadaia public install --template max-quality",
            id="valid-template-kept",
        ),
        pytest.param(
            "turbo-mode", "dadaia public install --template balanced", id="invalid-template-default"
        ),
        pytest.param(None, "dadaia public install --template balanced", id="no-template-default"),
    ],
)
def test_overrides_refused_with_runnable_fix(
    tmp_path: Path, applied_template: str | None, command: str
) -> None:
    store = _store(tmp_path)
    store.path.parent.mkdir(parents=True)
    doc = {
        **_valid_doc(),
        "applied_template": applied_template,
        "overrides": {"dd-sw-engineer-sr": {"effort": "medium"}},
    }
    store.path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(AgentModelPolicyStoreError, match="overrides") as raised:
        store.load()
    assert command in raised.value.fix  # type: ignore[attr-defined]


def test_applied_template_only_round_trip(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(AgentModelPolicyOverlay(applied_template="max-quality"))
    assert json.loads(store.path.read_text(encoding="utf-8")) == {
        "schema_version": "agent-model-policy-v1",
        "applied_template": "max-quality",
    }
    assert store.load() == AgentModelPolicyOverlay(applied_template="max-quality")


def test_save_atomic_last_good_and_reload(tmp_path: Path) -> None:
    """Atomic save, a last-good snapshot of the prior valid file, identical reload."""
    first = AgentModelPolicyOverlay(applied_template="balanced")
    second = AgentModelPolicyOverlay(applied_template="max-quality")

    assert_save_is_atomic_no_tmp_leftover(_store(tmp_path / "atomic"), first)
    assert_last_good_snapshot_of_prior_valid_file(_store(tmp_path / "lastgood"), first, second)
    assert_saved_value_reloads_identically(_store(tmp_path / "reload"), second)
