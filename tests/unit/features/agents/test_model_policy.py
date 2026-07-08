"""Unit tests for the panel-facing L1 agent-model-policy service (v0.1.65 T-65-10).

RED-first for FR8: the service validates, saves, invokes the injected re-render
callable, and returns its summary; ``resolved_roster()`` tags every entry's source
(``override|template|default|pack``). The store and the re-render callable are
injected (D-4 — no ``features -> infrastructure`` import edge; the store here is a
lightweight in-memory fake honoring the same port).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.agent_model_templates import CORE_AGENTS, list_templates
from dadaia_workspace.core.models.agent_model_policy import (
    CLAUDE_EFFORTS,
    AgentModelOverride,
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
)
from dadaia_workspace.features.agents.model_policy import AgentModelPolicyService
from dadaia_workspace.infrastructure.json_agent_model_policy_store import (
    JsonAgentModelPolicyStore,
)


class _RecordingRerender:
    """Fake re-render callable recording invocations and returning a fixed summary."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> list[str]:
        self.calls += 1
        return [
            "[ok] .claude/agents/software-engineer.md",
            "[ok] .codex/agents/software-engineer.toml",
        ]


def _service(tmp_path, *, plugin_defaults=None, rerender=None):  # type: ignore[no-untyped-def]
    (tmp_path / ".dadaia").mkdir(exist_ok=True)
    plugin_defaults = plugin_defaults or {}
    store = JsonAgentModelPolicyStore(tmp_path, plugin_agent_names=frozenset(plugin_defaults))
    rerender = rerender if rerender is not None else _RecordingRerender()
    return (
        AgentModelPolicyService(
            store=store,
            rerender=rerender,
            plugin_pack_defaults=lambda: dict(plugin_defaults),
        ),
        store,
        rerender,
    )


# ---------------------------------------------------------------------------
# get_policy / resolved_roster
# ---------------------------------------------------------------------------


def test_get_policy_missing_overlay_reports_defaults(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service, _store, _rr = _service(tmp_path)
    payload = service.get_policy()
    assert payload["exists"] is False
    assert payload["policy"]["schema_version"] == "agent-model-policy-v1"
    resolved = payload["resolved"]
    assert set(resolved) == set(CORE_AGENTS)
    # No overlay: every core agent resolves from the library default (balanced).
    assert all(entry["source"] == "default" for entry in resolved.values())
    assert resolved["software-engineer"] == {
        "model": "claude-sonnet-5",
        "effort": "xhigh",
        "source": "default",
    }


def test_resolved_roster_tags_override_template_default_pack(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service, store, _rr = _service(tmp_path, plugin_defaults={"devops-engineer": "claude-sonnet-5"})
    store.save(
        AgentModelPolicyOverlay(
            applied_template="subscription-saver",
            overrides={"software-engineer": AgentModelOverride(model="claude-opus-4-8")},
        )
    )
    roster = service.resolved_roster()
    # AC-3: model from override, effort from the applied template.
    assert roster["software-engineer"] == {
        "model": "claude-opus-4-8",
        "effort": "xhigh",
        "source": "override",
    }
    assert roster["project-manager"]["source"] == "template"
    assert roster["project-manager"]["model"] == "claude-opus-4-8"
    # Plugin agent: pack default, effort omitted (F-6 — None).
    assert roster["devops-engineer"] == {
        "model": "claude-sonnet-5",
        "effort": None,
        "source": "pack",
    }


def test_get_policy_invalid_overlay_raises_typed_error(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service, store, _rr = _service(tmp_path)
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.write_text("{not json", encoding="utf-8")
    with pytest.raises(AgentModelPolicyStoreError):
        service.get_policy()


# ---------------------------------------------------------------------------
# templates_payload
# ---------------------------------------------------------------------------


def test_templates_payload_carries_rosters_models_and_efforts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service, _store, _rr = _service(tmp_path)
    payload = service.templates_payload()
    templates = payload["templates"]
    assert [t["id"] for t in templates] == ["balanced", "subscription-saver", "max-quality"]
    balanced = templates[0]
    assert balanced["default"] is True
    assert set(balanced["assignments"]) == set(CORE_AGENTS)
    assert balanced["assignments"]["project-manager"] == {
        "model": "claude-fable-5",
        "effort": "high",
    }
    assert "claude-sonnet-5" in payload["models"]
    assert payload["efforts"] == list(CLAUDE_EFFORTS)
    # Payload mirrors the library registry — nothing invented in the view layer.
    assert len(templates) == len(list_templates())


# ---------------------------------------------------------------------------
# validate / apply
# ---------------------------------------------------------------------------


def test_validate_rejects_fable_on_security_with_distinct_message(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service, _store, _rr = _service(tmp_path)
    raw = {
        "schema_version": "agent-model-policy-v1",
        "overrides": {"security-reviewer": {"model": "claude-fable-5"}},
    }
    with pytest.raises(AgentModelPolicyStoreError, match="security-reviewer"):
        service.validate(raw)


def test_apply_validates_saves_rerenders_and_returns_summary(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service, store, rerender = _service(tmp_path)
    raw = {
        "schema_version": "agent-model-policy-v1",
        "applied_template": "max-quality",
    }
    result = service.apply(raw)
    assert rerender.calls == 1
    assert result["rerendered"] == [
        "[ok] .claude/agents/software-engineer.md",
        "[ok] .codex/agents/software-engineer.toml",
    ]
    assert result["policy"]["applied_template"] == "max-quality"
    # Persisted: a fresh load resolves the applied template.
    persisted = store.load()
    assert persisted is not None and persisted.applied_template == "max-quality"
    # G-2 payload: per-harness pickup instructions ride along for the pop-up.
    assert "claude" in result["instructions"] and "codex" in result["instructions"]


def test_apply_invalid_never_saves_nor_rerenders(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service, store, rerender = _service(tmp_path)
    with pytest.raises(AgentModelPolicyStoreError):
        service.apply({"schema_version": "agent-model-policy-v1", "applied_template": "nope"})
    assert rerender.calls == 0
    assert not store.path.exists()
