"""Unit tests for ``infrastructure/json_agent_model_policy_store.py`` (v0.1.65 FR3/D-7).

Mirrors the ``json_workflow_model_policy_store`` discipline: missing file ⇒ ``None``
(defaults) ≠ invalid file ⇒ typed :class:`AgentModelPolicyStoreError`; atomic
temp+rename write with a ``.last-good.json`` snapshot of the PRIOR valid file; a shared
no-I/O :meth:`parse` path (consumed later by the panel validate endpoint). Every FR3
rejection carries a distinct, actionable message; D-7 rejects any combination that
resolves ``claude-fable-5`` onto ``security-reviewer``.

The generic load/parse/save+last-good store contract (missing->None, corrupt->typed
error, unknown-top-level-field, wrong schema_version, atomic-no-tmp, last-good
snapshot, reload-identity) is asserted once via the shared ``_store_contract`` helpers
— this file keeps only the store-specific logic: the FR3 parse-rejection matrix and
the D-7 governance invariant.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.agent_model_policy import (
    AgentModelOverride,
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
)
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)

from ._store_contract import (
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
        "applied_template": "subscription-saver",
        "overrides": {"software-engineer": {"model": "claude-opus-4-8"}},
    }


def test_load_contract(tmp_path: Path) -> None:
    """missing->None / corrupt->typed error / unknown-field / wrong schema_version —
    the shared store-contract template, applied once."""
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
            lambda d: {**d, "overrides": {"software-engineer": {"model": "claude-unknown-9-9"}}},
            "unknown model.*claude-unknown-9-9",
            id="unknown-model",
        ),
        pytest.param(
            lambda d: {**d, "overrides": {"software-engineer": {"effort": "turbo"}}},
            "invalid effort.*turbo",
            id="invalid-effort",
        ),
        pytest.param(
            lambda d: {
                **d,
                "overrides": {"software-engineer": {"model": "claude-opus-4-8", "speed": "fast"}},
            },
            "unknown field.*speed",
            id="unknown-override-key",
        ),
        pytest.param(
            lambda d: {**d, "overrides": {"software-engineer": {}}},
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
    assert overlay.applied_template == "subscription-saver"
    assert overlay.overrides["software-engineer"] == AgentModelOverride(model="claude-opus-4-8")

    minimal = store.parse({"schema_version": "agent-model-policy-v1"})
    assert minimal.applied_template is None
    assert minimal.overrides == {}

    plugin_store = _store(tmp_path / "plugin", plugin_agent_names=frozenset({"frontend-engineer"}))
    plugin_doc = _valid_doc()
    plugin_doc["overrides"] = {"frontend-engineer": {"effort": "high"}}
    plugin_overlay = plugin_store.parse(plugin_doc)
    assert plugin_overlay.overrides["frontend-engineer"] == AgentModelOverride(effort="high")


def test_d7_rejects_fable_on_security_reviewer_but_allows_on_other_agents(
    tmp_path: Path,
) -> None:
    """D-7: an override putting Fable on security-reviewer is rejected at parse; the
    same model is freely allowed on any other agent. This is the sole coverage of the
    D-7 governance invariant — keep both assertions explicit."""
    store = _store(tmp_path)

    doc = _valid_doc()
    doc["overrides"] = {"security-reviewer": {"model": "claude-fable-5"}}
    with pytest.raises(
        AgentModelPolicyStoreError,
        match="claude-fable-5.*security-reviewer|security-reviewer.*claude-fable-5",
    ):
        store.parse(doc)

    doc2 = _valid_doc()
    doc2["overrides"] = {"qa-engineer": {"model": "claude-fable-5"}}
    overlay = store.parse(doc2)
    assert overlay.overrides["qa-engineer"].model == "claude-fable-5"


def test_save_atomic_last_good_and_reload(tmp_path: Path) -> None:
    """save() is atomic (no .tmp leftover), snapshots the PRIOR valid file to
    .last-good.json on the second save (none on the first), and a saved overlay
    reloads identically."""
    first = AgentModelPolicyOverlay(applied_template="balanced", overrides={})
    second = AgentModelPolicyOverlay(
        applied_template="subscription-saver",
        overrides={
            "software-engineer": AgentModelOverride(model="claude-opus-4-8"),
            "qa-engineer": AgentModelOverride(effort="max"),
        },
    )

    assert_save_is_atomic_no_tmp_leftover(_store(tmp_path / "atomic"), first)
    assert_last_good_snapshot_of_prior_valid_file(_store(tmp_path / "lastgood"), first, second)
    assert_saved_value_reloads_identically(_store(tmp_path / "reload"), second)
