"""Unit tests for ``core.model_registry`` — the one module answering which model an
agent gets (sa-agent-model-resolved-by-two-modules): the registry, the D-3 effort clamp
and the ``resolve_agent_model`` precedence (FR4): override > applied template >
``balanced`` default. The ADR 0022 table and G-1 are pinned in
``tests/contract/test_agent_tier_taxonomy.py``.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.model_registry import (
    REGISTRY,
    AgentModelOverride,
    AgentModelPolicyOverlay,
    codex_effort_for_claude_effort,
    is_fable_model,
    registry_by_claude_id,
    resolve_agent_model,
)


def test_registry_invariant_sweep_with_content_pins() -> None:
    """Intent: CONTRACT — agent-model-templates-pin-superseded-opus-and-lack-the-economy-template.

    No duplicate claude_ids; every codex_id lacks the claude- prefix (ADR-5). Pins: the
    haiku-4-5 id, sonnet-5 -> gpt-5.6-terra/standard, opus-5-5 on dispatch with opus-5's
    codex id, fable-5 on deep; G-1's Fable family is every registered claude-fable-* id
    (bug g1-fable-guard-matches-only-claude-fable-5-so-fable-5-1-lands-on-security-reviewer).
    """
    ids = [entry.claude_id for entry in REGISTRY]
    assert len(ids) == len(set(ids)), f"duplicate claude_id in REGISTRY: {ids}"
    assert not any(entry.codex_id.startswith("claude-") for entry in REGISTRY)

    index = registry_by_claude_id()
    assert "claude-haiku-4-5-20251001" in index
    assert "claude-haiku-3-5" not in index
    assert (index["claude-sonnet-5"].codex_id, index["claude-sonnet-5"].tier) == (
        "gpt-5.6-terra",
        "standard",
    )
    assert (index["claude-opus-5-5"].codex_id, index["claude-opus-5-5"].tier) == (
        "gpt-5.6-sol",
        "dispatch",
    )
    assert index["claude-opus-5"].codex_id == "gpt-5.6-sol"
    assert index["claude-fable-5"].tier == "deep"
    assert is_fable_model("claude-fable-5-1")
    assert not is_fable_model("claude-opus-5")
    assert not is_fable_model("claude-fable-9")  # unregistered


@pytest.mark.parametrize(
    "claude_effort,codex_effort",
    [("low", "low"), ("medium", "medium"), ("high", "high"), ("xhigh", "high"), ("max", "high")],
)
def test_codex_effort_clamp_map(claude_effort: str, codex_effort: str) -> None:
    assert codex_effort_for_claude_effort(claude_effort) == codex_effort  # type: ignore[arg-type]


SE, PE = "dd-software-engineer", "dd-product-engineer"
MAXQ_SE_OPUS48 = AgentModelPolicyOverlay(
    applied_template="max-quality", overrides={SE: AgentModelOverride(model="claude-opus-4-8")}
)


@pytest.mark.parametrize(
    ("agent", "overlay", "expected"),
    [
        pytest.param(SE, None, ("claude-opus-5-5", "low", "default"), id="no_overlay_resolves_balanced_default"),
        pytest.param(PE, AgentModelPolicyOverlay(applied_template="max-quality", overrides={}), ("claude-fable-5-1", "high", "template"), id="applied_template_resolves_source_template"),
        pytest.param(SE, MAXQ_SE_OPUS48, ("claude-opus-4-8", "medium", "override"), id="ac3_per_field_override_merges_with_applied_template"),
        pytest.param(SE, AgentModelPolicyOverlay(applied_template=None, overrides={SE: AgentModelOverride(effort="max")}), ("claude-opus-5-5", "max", "override"), id="effort_only_override_keeps_template_model"),
        pytest.param(PE, AgentModelPolicyOverlay(applied_template="max-quality", overrides={PE: AgentModelOverride(model="claude-haiku-4-5-20251001", effort="low")}), ("claude-haiku-4-5-20251001", "low", "override"), id="full_override_beats_template"),
        pytest.param(PE, MAXQ_SE_OPUS48, ("claude-fable-5-1", "high", "template"), id="ac3_other_agents_keep_applied_template_when_only_one_overridden"),
    ],
)  # fmt: skip
def test_resolve_agent_model_precedence_table(
    agent: str, overlay: AgentModelPolicyOverlay | None, expected: tuple[str, str | None, str]
) -> None:
    """FR4: override (per field) > applied template > ``balanced`` default."""
    resolved = resolve_agent_model(agent, overlay)
    assert (resolved.model, resolved.effort, resolved.source) == expected


@pytest.mark.parametrize(
    ("agent", "overlay", "match"),
    [
        pytest.param("not-an-agent", None, "unknown agent", id="unknown_agent"),
        pytest.param(SE, AgentModelPolicyOverlay(applied_template="nope", overrides={}), "nope", id="unknown_applied_template"),
    ],
)  # fmt: skip
def test_resolve_agent_model_rejects_unknown(
    agent: str, overlay: AgentModelPolicyOverlay | None, match: str
) -> None:
    """An unknown agent or template is refused by name."""
    with pytest.raises(ValueError, match=match):
        resolve_agent_model(agent, overlay)
