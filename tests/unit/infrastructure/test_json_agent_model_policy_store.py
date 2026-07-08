"""Unit tests for ``infrastructure/json_agent_model_policy_store.py`` (v0.1.65 FR3/D-7).

Mirrors the ``json_workflow_model_policy_store`` discipline: missing file ⇒ ``None``
(defaults) ≠ invalid file ⇒ typed :class:`AgentModelPolicyStoreError`; atomic
temp+rename write with a ``.last-good.json`` snapshot of the PRIOR valid file; a shared
no-I/O :meth:`parse` path (consumed later by the panel validate endpoint). Every FR3
rejection carries a distinct, actionable message; D-7 rejects any combination that
resolves ``claude-fable-5`` onto ``security-reviewer``.
"""

from __future__ import annotations

import json
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


def _store(tmp_path: Path, **kwargs: object) -> JsonAgentModelPolicyStore:
    return JsonAgentModelPolicyStore(tmp_path, **kwargs)  # type: ignore[arg-type]


def _valid_doc() -> dict[str, object]:
    return {
        "schema_version": "agent-model-policy-v1",
        "applied_template": "subscription-saver",
        "overrides": {"software-engineer": {"model": "claude-opus-4-8"}},
    }


def _write(store: JsonAgentModelPolicyStore, doc: object) -> None:
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text(json.dumps(doc), encoding="utf-8")


# ---------------------------------------------------------------------------
# load(): missing != invalid
# ---------------------------------------------------------------------------


def test_missing_file_loads_none(tmp_path: Path) -> None:
    assert _store(tmp_path).load() is None


def test_path_is_canonical_workspace_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.path == tmp_path / ".dadaia" / "states" / "agent_model_policy.json"


def test_corrupt_json_raises_typed_error(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{not json", encoding="utf-8")
    with pytest.raises(AgentModelPolicyStoreError, match="invalid JSON"):
        store.load()


def test_valid_doc_round_trips(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _write(store, _valid_doc())
    overlay = store.load()
    assert overlay is not None
    assert overlay.applied_template == "subscription-saver"
    assert overlay.overrides["software-engineer"] == AgentModelOverride(model="claude-opus-4-8")


def test_minimal_doc_parses_to_empty_overlay(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _write(store, {"schema_version": "agent-model-policy-v1"})
    overlay = store.load()
    assert overlay is not None
    assert overlay.applied_template is None
    assert overlay.overrides == {}


# ---------------------------------------------------------------------------
# parse(): every FR3 rejection has a distinct typed message
# ---------------------------------------------------------------------------


def test_parse_rejects_non_object_root(tmp_path: Path) -> None:
    with pytest.raises(AgentModelPolicyStoreError, match="root is not an object"):
        _store(tmp_path).parse([])


def test_parse_rejects_unknown_top_level_key(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["surprise"] = 1
    with pytest.raises(AgentModelPolicyStoreError, match="unknown top-level field.*surprise"):
        _store(tmp_path).parse(doc)


def test_parse_rejects_wrong_schema_version(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["schema_version"] = "agent-model-policy-v0"
    with pytest.raises(AgentModelPolicyStoreError, match="schema version"):
        _store(tmp_path).parse(doc)


def test_parse_rejects_unknown_template(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["applied_template"] = "turbo-mode"
    with pytest.raises(AgentModelPolicyStoreError, match="unknown.*template.*turbo-mode"):
        _store(tmp_path).parse(doc)


def test_parse_rejects_unknown_agent(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["overrides"] = {"not-an-agent": {"model": "claude-opus-4-8"}}
    with pytest.raises(AgentModelPolicyStoreError, match="unknown agent.*not-an-agent"):
        _store(tmp_path).parse(doc)


def test_parse_accepts_installed_plugin_agent(tmp_path: Path) -> None:
    store = _store(tmp_path, plugin_agent_names=frozenset({"frontend-engineer"}))
    doc = _valid_doc()
    doc["overrides"] = {"frontend-engineer": {"effort": "high"}}
    overlay = store.parse(doc)
    assert overlay.overrides["frontend-engineer"] == AgentModelOverride(effort="high")


def test_parse_rejects_unknown_model(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["overrides"] = {"software-engineer": {"model": "claude-unknown-9-9"}}
    with pytest.raises(AgentModelPolicyStoreError, match="unknown model.*claude-unknown-9-9"):
        _store(tmp_path).parse(doc)


def test_parse_rejects_invalid_effort(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["overrides"] = {"software-engineer": {"effort": "turbo"}}
    with pytest.raises(AgentModelPolicyStoreError, match="invalid effort.*turbo"):
        _store(tmp_path).parse(doc)


def test_parse_rejects_unknown_override_key(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["overrides"] = {"software-engineer": {"model": "claude-opus-4-8", "speed": "fast"}}
    with pytest.raises(AgentModelPolicyStoreError, match="unknown field.*speed"):
        _store(tmp_path).parse(doc)


def test_parse_rejects_empty_override(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["overrides"] = {"software-engineer": {}}
    with pytest.raises(AgentModelPolicyStoreError, match="must carry 'model', 'effort', or both"):
        _store(tmp_path).parse(doc)


def test_parse_rejects_fable_on_security_reviewer_via_override(tmp_path: Path) -> None:
    """D-7: an override putting Fable on security-reviewer is rejected at parse."""
    doc = _valid_doc()
    doc["overrides"] = {"security-reviewer": {"model": "claude-fable-5"}}
    with pytest.raises(
        AgentModelPolicyStoreError,
        match="claude-fable-5.*security-reviewer|security-reviewer.*claude-fable-5",
    ):
        _store(tmp_path).parse(doc)


def test_parse_allows_fable_on_other_agents(tmp_path: Path) -> None:
    doc = _valid_doc()
    doc["overrides"] = {"qa-engineer": {"model": "claude-fable-5"}}
    overlay = _store(tmp_path).parse(doc)
    assert overlay.overrides["qa-engineer"].model == "claude-fable-5"


# ---------------------------------------------------------------------------
# save(): atomic + .last-good.json snapshot of the PRIOR valid file
# ---------------------------------------------------------------------------


def test_save_writes_valid_json_atomically(tmp_path: Path) -> None:
    store = _store(tmp_path)
    overlay = AgentModelPolicyOverlay(
        applied_template="balanced",
        overrides={"qa-engineer": AgentModelOverride(effort="max")},
    )
    store.save(overlay)
    on_disk = json.loads(store.path.read_text(encoding="utf-8"))
    assert on_disk == {
        "schema_version": "agent-model-policy-v1",
        "applied_template": "balanced",
        "overrides": {"qa-engineer": {"effort": "max"}},
    }
    # No temp files left behind.
    leftovers = [p for p in store.path.parent.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


def test_save_snapshots_prior_valid_file_to_last_good(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = AgentModelPolicyOverlay(applied_template="balanced", overrides={})
    store.save(first)
    prior_bytes = store.path.read_bytes()
    second = AgentModelPolicyOverlay(applied_template="max-quality", overrides={})
    store.save(second)
    assert store.last_good_path.read_bytes() == prior_bytes
    reloaded = store.load()
    assert reloaded is not None and reloaded.applied_template == "max-quality"


def test_first_save_creates_no_last_good(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(AgentModelPolicyOverlay())
    assert not store.last_good_path.exists()


def test_saved_overlay_reloads_identically(tmp_path: Path) -> None:
    store = _store(tmp_path)
    overlay = AgentModelPolicyOverlay(
        applied_template="subscription-saver",
        overrides={
            "software-engineer": AgentModelOverride(model="claude-opus-4-8"),
            "qa-engineer": AgentModelOverride(effort="max"),
        },
    )
    store.save(overlay)
    assert store.load() == overlay
