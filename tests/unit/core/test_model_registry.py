"""Unit tests for dadaia_workspace.core.model_registry — the single source of
truth for model id / Codex mapping / tier.

Covers registry invariants (no duplicate claude_ids, every entry has a tier + a
non-claude codex_id) and the Codex tier views. The MODEL_MAP key-equality contract
lives with the derived view in ``test_model_mapping.py``.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.model_registry import (
    REGISTRY,
    ModelEntry,
    codex_effort_for_tier,
    codex_tier_views,
    registry_by_claude_id,
)


def test_current_registry_is_collapse_free() -> None:
    """The LIVE registry must not collapse two distinct tiers into one
    (model id, reasoning effort) pair — proves the live values are valid."""
    views = codex_tier_views()  # raises on collapse
    pairs = [(v.codex_id, v.reasoning_effort) for v in views]
    assert len(pairs) == len(set(pairs)), f"tier collapse in live registry: {pairs}"


def test_registry_invariant_sweep_with_content_pins() -> None:
    """One sweep over every REGISTRY entry: no duplicate claude_ids, every entry carries
    a tier and a codex_id without the claude- prefix (ADR-5); registry_by_claude_id()
    indexes every entry. Content pins: the haiku-4-5 id drift fix and the sonnet-5
    mapping/tier (FR6/D-2), fable-5 on the deep tier.
    """
    ids = [entry.claude_id for entry in REGISTRY]
    assert len(ids) == len(set(ids)), f"duplicate claude_id in REGISTRY: {ids}"

    for entry in REGISTRY:
        assert entry.codex_id, f"{entry.claude_id} has empty codex_id"
        assert entry.tier in ("deep", "dispatch", "fast", "standard")
        assert not entry.codex_id.startswith("claude-")

    index = registry_by_claude_id()
    assert set(index) == {entry.claude_id for entry in REGISTRY}
    assert len(index) == len(REGISTRY)

    assert "claude-haiku-4-5-20251001" in index
    assert "claude-haiku-3-5" not in index
    assert (index["claude-sonnet-5"].codex_id, index["claude-sonnet-5"].tier) == (
        "gpt-5.6-terra",
        "standard",
    )
    assert index["claude-fable-5"].tier == "deep"


def test_registry_by_claude_id_raises_on_duplicate() -> None:
    dup = (
        ModelEntry("claude-x", "gpt-x", "fast"),
        ModelEntry("claude-x", "gpt-y", "fast"),
    )
    import dadaia_workspace.core.model_registry as mr

    original = mr.REGISTRY
    mr.REGISTRY = dup
    try:
        with pytest.raises(ValueError, match="Duplicate claude_id"):
            registry_by_claude_id()
    finally:
        mr.REGISTRY = original


def test_codex_tier_views_yield_effort_map_and_deep_dispatch_share_id() -> None:
    """Each registry tier renders to a Codex (model id, reasoning effort) pair; deep and
    dispatch share gpt-5.6-sol today but stay distinct via effort; codex_effort_for_tier
    matches the same map.
    """
    views = codex_tier_views()
    tiers = {v.tier for v in views}
    assert tiers == {"deep", "dispatch", "fast", "standard"}
    for view in views:
        assert view.codex_id, f"{view.tier} has empty codex_id"
        assert not view.codex_id.startswith("claude-")
        assert view.reasoning_effort in ("high", "medium", "low")

    by_tier = {v.tier: v for v in views}
    assert by_tier["deep"].codex_id == by_tier["dispatch"].codex_id
    assert by_tier["deep"].reasoning_effort == "high"
    assert by_tier["dispatch"].reasoning_effort == "medium"

    assert codex_effort_for_tier("deep") == "high"
    assert codex_effort_for_tier("dispatch") == "medium"
    assert codex_effort_for_tier("fast") == "medium"
    assert codex_effort_for_tier("standard") == "medium"


def test_codex_tier_views_raises_on_collapse() -> None:
    """A synthetic registry whose deep and dispatch tiers resolve to the IDENTICAL
    (model id, effort) pair must raise, naming both tiers. A tier carried by entries
    with disagreeing codex_ids is likewise ambiguous and must raise.
    """
    import dadaia_workspace.core.model_registry as mr

    # Both deep and dispatch -> gpt-collide, and force both efforts to "high" so
    # the pair is identical and the distinction collapses.
    colliding = (
        ModelEntry("claude-a", "gpt-collide", "deep"),
        ModelEntry("claude-b", "gpt-collide", "dispatch"),
        ModelEntry("claude-c", "gpt-fast", "fast"),
        ModelEntry("claude-d", "gpt-plg", "standard"),
    )
    original_reg = mr.REGISTRY
    original_effort = dict(mr._CODEX_TIER_EFFORT)
    mr.REGISTRY = colliding
    mr._CODEX_TIER_EFFORT["dispatch"] = "high"  # collapse: deep & dispatch both high
    try:
        with pytest.raises(ValueError, match="Codex tier collapse.*deep.*dispatch|dispatch.*deep"):
            codex_tier_views()
    finally:
        mr.REGISTRY = original_reg
        mr._CODEX_TIER_EFFORT.clear()
        mr._CODEX_TIER_EFFORT.update(original_effort)

    ambiguous = (
        ModelEntry("claude-a", "gpt-x", "deep"),
        ModelEntry("claude-b", "gpt-y", "deep"),
        ModelEntry("claude-c", "gpt-d", "dispatch"),
        ModelEntry("claude-e", "gpt-f", "fast"),
        ModelEntry("claude-g", "gpt-p", "standard"),
    )
    original = mr.REGISTRY
    mr.REGISTRY = ambiguous
    try:
        with pytest.raises(ValueError, match="multiple Codex ids"):
            codex_tier_views()
    finally:
        mr.REGISTRY = original


def test_fable_family_is_derived_from_the_registry() -> None:
    """G-1 is a family rule: every registered claude-fable-* id is Fable, nothing else
    (bug g1-fable-guard-matches-only-claude-fable-5-so-fable-5-1-lands-on-security-reviewer)."""
    from dadaia_workspace.core.model_registry import fable_model_ids, is_fable_model

    assert {"claude-fable-5", "claude-fable-5-1"} <= fable_model_ids()
    assert is_fable_model("claude-fable-5-1")
    assert not is_fable_model("claude-opus-5")


def test_opus_5_5_is_registered_on_the_dispatch_tier_with_the_tier_codex_id() -> None:
    """Intent: CONTRACT — agent-model-templates-pin-superseded-opus-and-lack-the-economy-template.

    Opus 5.5 is the current Opus model (ADR 0022); it shares the dispatch tier, so the
    one-codex-id-per-tier invariant forces opus-5's codex id.
    """
    index = registry_by_claude_id()
    assert index["claude-opus-5-5"].tier == "dispatch"
    assert index["claude-opus-5-5"].codex_id == index["claude-opus-5"].codex_id == "gpt-5.6-sol"
    codex_tier_views()  # the live registry stays collapse- and ambiguity-free
