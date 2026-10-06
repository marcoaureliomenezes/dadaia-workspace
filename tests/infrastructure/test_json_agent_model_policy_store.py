"""JsonAgentModelPolicyStore (v0.1.65 FR3/D-7): the shared store contract once, then the
store's own FR3 parse-rejection matrix and the D-7 Fable guard.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.model_registry import (
    AgentModelOverride,
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
        "overrides": {"dd-software-engineer": {"model": "claude-opus-4-8"}},
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
    ("mutate_doc", "match"),
    [
        pytest.param(lambda d: [], "root is not an object", id="root-not-object"),
        pytest.param(
            lambda d: {**d, "applied_template": "turbo-mode"},
            "unknown.*template.*turbo-mode",
            id="unknown-template",
        ),
        pytest.param(
            lambda d: {**d, "overrides": {"not-an-agent": {"model": "claude-opus-4-8"}}},
            "unknown agent.*not-an-agent",
            id="unknown-agent",
        ),
        pytest.param(
            lambda d: {**d, "overrides": {"dd-software-engineer": {"model": "claude-unknown-9-9"}}},
            "unknown model.*claude-unknown-9-9",
            id="unknown-model",
        ),
        pytest.param(
            lambda d: {**d, "overrides": {"dd-software-engineer": {"effort": "turbo"}}},
            "invalid effort.*turbo",
            id="invalid-effort",
        ),
        pytest.param(
            lambda d: {
                **d,
                "overrides": {
                    "dd-software-engineer": {"model": "claude-opus-4-8", "speed": "fast"}
                },
            },
            "unknown field.*speed",
            id="unknown-override-key",
        ),
        pytest.param(
            lambda d: {**d, "overrides": {"dd-software-engineer": {}}},
            "must carry 'model', 'effort', or both",
            id="empty-override",
        ),
    ],
)
def test_parse_rejection_matrix(tmp_path: Path, mutate_doc: object, match: str) -> None:
    doc = mutate_doc(_valid_doc())  # type: ignore[operator]
    with pytest.raises(AgentModelPolicyStoreError, match=match):
        _store(tmp_path).parse(doc)


def test_valid_doc_and_minimal_doc_parse(tmp_path: Path) -> None:
    store = _store(tmp_path)
    overlay = store.parse(_valid_doc())
    assert overlay.applied_template == "max-quality"
    assert overlay.overrides["dd-software-engineer"] == AgentModelOverride(model="claude-opus-4-8")

    minimal = store.parse({"schema_version": "agent-model-policy-v1"})
    assert minimal.applied_template is None
    assert minimal.overrides == {}


@pytest.mark.parametrize("fable_id", ["claude-fable-5", "claude-fable-5-1"])
def test_d7_rejects_fable_on_security_reviewer_but_allows_on_other_agents(
    tmp_path: Path, fable_id: str
) -> None:
    """D-7 (bug g1-fable-guard-matches-only-claude-fable-5-so-fable-5-1-lands-on-
    dd-code-reviewer): any Fable-family model on dd-code-reviewer is rejected at parse;
    the same model is allowed on any other agent."""
    store = _store(tmp_path)

    doc = _valid_doc()
    doc["overrides"] = {"dd-code-reviewer": {"model": fable_id}}
    with pytest.raises(
        AgentModelPolicyStoreError,
        match=f"{fable_id}.*dd-code-reviewer|dd-code-reviewer.*{fable_id}",
    ):
        store.parse(doc)

    doc2 = _valid_doc()
    doc2["overrides"] = {"dd-software-engineer": {"model": fable_id}}
    overlay = store.parse(doc2)
    assert overlay.overrides["dd-software-engineer"].model == fable_id


def test_save_atomic_last_good_and_reload(tmp_path: Path) -> None:
    """Atomic save, a last-good snapshot of the prior valid file, identical reload."""
    first = AgentModelPolicyOverlay(applied_template="balanced", overrides={})
    second = AgentModelPolicyOverlay(
        applied_template="max-quality",
        overrides={
            "dd-software-engineer": AgentModelOverride(model="claude-opus-4-8"),
            "dd-product-engineer": AgentModelOverride(effort="max"),
        },
    )

    assert_save_is_atomic_no_tmp_leftover(_store(tmp_path / "atomic"), first)
    assert_last_good_snapshot_of_prior_valid_file(_store(tmp_path / "lastgood"), first, second)
    assert_saved_value_reloads_identically(_store(tmp_path / "reload"), second)
