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


@pytest.mark.parametrize(
    ("name", "agent", "overlay_fn", "expected"),
    [
        (
            "no_overlay_resolves_balanced_default",
            "dd-software-engineer",
            lambda: None,
            ("claude-opus-5-5", "low", "default"),
        ),
        (
            "applied_template_resolves_source_template",
            "dd-product-engineer",
            lambda: AgentModelPolicyOverlay(applied_template="max-quality", overrides={}),
            ("claude-fable-5-1", "high", "template"),
        ),
        (
            # AC-3: template max-quality + override {SE: model=opus-4-8} →
            # SE = opus-4-8 (override model) / medium (template effort), source=override.
            "per_field_override_merges_with_applied_template",
            "dd-software-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template="max-quality",
                overrides={"dd-software-engineer": AgentModelOverride(model="claude-opus-4-8")},
            ),
            ("claude-opus-4-8", "medium", "override"),
        ),
        (
            "effort_only_override_keeps_template_model",
            "dd-software-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template=None,
                overrides={"dd-software-engineer": AgentModelOverride(effort="max")},
            ),
            ("claude-opus-5-5", "max", "override"),
        ),
        (
            "full_override_beats_template",
            "dd-product-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template="max-quality",
                overrides={
                    "dd-product-engineer": AgentModelOverride(
                        model="claude-haiku-4-5-20251001", effort="low"
                    )
                },
            ),
            ("claude-haiku-4-5-20251001", "low", "override"),
        ),
        (
            # AC-3: an unrelated agent keeps the applied template when only ONE
            # other agent in the overlay is overridden.
            "ac3_other_agents_keep_applied_template_when_only_one_overridden",
            "dd-product-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template="max-quality",
                overrides={"dd-software-engineer": AgentModelOverride(model="claude-opus-4-8")},
            ),
            ("claude-fable-5-1", "high", "template"),
        ),
    ],
)
def test_resolve_agent_model_precedence_table(
    name: str,
    agent: str,
    overlay_fn: object,
    expected: tuple[str, str | None, str],
) -> None:
    overlay = overlay_fn()  # type: ignore[operator]
    resolved = resolve_agent_model(agent, overlay)
    assert (resolved.model, resolved.effort, resolved.source) == expected


@pytest.mark.parametrize(
    ("name", "agent", "overlay_fn", "match"),
    [
        ("unknown_agent", "not-an-agent", lambda: None, "unknown agent"),
        (
            "unknown_applied_template",
            "dd-software-engineer",
            lambda: AgentModelPolicyOverlay(applied_template="nope", overrides={}),
            "nope",
        ),
    ],
)
def test_resolve_agent_model_rejects_unknown(
    name: str, agent: str, overlay_fn: object, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        resolve_agent_model(agent, overlay_fn())  # type: ignore[operator]
