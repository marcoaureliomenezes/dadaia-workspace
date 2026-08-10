"""Unit tests for dadaia_workspace.core.model_registry — the single source of
truth for model id / mapping / pricing / tier.

Covers registry invariants (append-only dated pricing, no duplicate claude_ids,
every entry has a tier + codex_id + non-empty pricing) and the most-recent-row
selection helper. The cross-table key-equality contract (MODEL_MAP keys ==
PRICING_TABLE keys == registry claude_ids) lives in
``test_model_mapping.py``/``test_pricing.py`` where both derived views are in
scope.
"""

from __future__ import annotations

from datetime import date

import pytest

from dadaia_workspace.core.model_registry import (
    REGISTRY,
    ModelEntry,
    ModelPricing,
    codex_effort_for_tier,
    codex_tier_views,
    current_pricing,
    registry_by_claude_id,
)


def test_current_registry_is_collapse_free() -> None:
    """The LIVE registry must not collapse two distinct tiers into one
    (model id, reasoning effort) pair — proves the live values are valid."""
    views = codex_tier_views()  # raises on collapse
    pairs = [(v.codex_id, v.reasoning_effort) for v in views]
    assert len(pairs) == len(set(pairs)), f"tier collapse in live registry: {pairs}"


def test_registry_invariant_sweep_with_content_pins() -> None:
    """One sweep over every REGISTRY entry proving: no duplicate claude_ids, every
    entry carries a tier + codex_id + non-empty pricing, no codex_id carries the
    claude- prefix (ADR-5), pricing rows carry a date, and each model's pricing
    history is append-only (strictly distinct effective_from dates so 'current' is
    unambiguous). registry_by_claude_id() indexes every entry.

    Content pins (bug fixes / FR landings) are folded in as rows: the haiku-4-5 id
    drift fix, the sonnet-5 mapping/tier/pricing (FR6/D-2), and the fable-5 pricing.
    """
    ids = [entry.claude_id for entry in REGISTRY]
    assert len(ids) == len(set(ids)), f"duplicate claude_id in REGISTRY: {ids}"

    for entry in REGISTRY:
        assert entry.codex_id, f"{entry.claude_id} has empty codex_id"
        assert entry.tier in ("deep", "dispatch", "fast", "standard")
        assert entry.pricing, f"{entry.claude_id} has no pricing rows"
        # ADR-5: Codex TOML must never carry a claude-* string.
        assert not entry.codex_id.startswith("claude-")
        dates = []
        for row in entry.pricing:
            assert isinstance(row.effective_from, date)
            dates.append(row.effective_from)
        assert len(dates) == len(set(dates)), f"{entry.claude_id} has duplicate effective_from"

    index = registry_by_claude_id()
    assert set(index) == {entry.claude_id for entry in REGISTRY}
    assert len(index) == len(REGISTRY)

    # Content pin: the canonical haiku id is haiku-4-5-20251001 (the 3-5 drift is gone).
    assert "claude-haiku-4-5-20251001" in index
    assert "claude-haiku-3-5" not in index
    haiku_pricing = current_pricing(index["claude-haiku-4-5-20251001"])
    assert haiku_pricing.input_per_mtok == 0.80
    assert haiku_pricing.output_per_mtok == 4.00

    # Content pin (FR6/D-2, v0.1.65; codex id remapped by the operator codex remap):
    # claude-sonnet-5 -> gpt-5.6-terra, tier 'standard' (forced cost-axis label, sonnet
    # cost class), pricing 3.00/15.00/3.75/0.30 from 2026-07-01.
    assert "claude-sonnet-5" in index
    sonnet5 = index["claude-sonnet-5"]
    assert sonnet5.codex_id == "gpt-5.6-terra"
    assert sonnet5.tier == "standard"
    sonnet_pricing = current_pricing(sonnet5)
    assert (
        sonnet_pricing.input_per_mtok,
        sonnet_pricing.output_per_mtok,
        sonnet_pricing.cache_creation_per_mtok,
        sonnet_pricing.cache_read_per_mtok,
        sonnet_pricing.effective_from,
    ) == (3.00, 15.00, 3.75, 0.30, date(2026, 7, 1))

    # Content pin: claude-fable-5 pricing.
    assert "claude-fable-5" in index
    fable = index["claude-fable-5"]
    fable_pricing = current_pricing(fable)
    assert (
        fable_pricing.input_per_mtok,
        fable_pricing.output_per_mtok,
        fable_pricing.cache_creation_per_mtok,
        fable_pricing.cache_read_per_mtok,
        fable_pricing.effective_from,
    ) == (10.00, 50.00, 12.50, 1.00, date(2026, 6, 1))
    assert fable.tier == "deep"


def test_registry_by_claude_id_raises_on_duplicate() -> None:
    dup = (
        ModelEntry("claude-x", "gpt-x", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "fast"),
        ModelEntry("claude-x", "gpt-y", (ModelPricing(2, 2, 2, 2, date(2025, 1, 1)),), "fast"),
    )
    import dadaia_workspace.core.model_registry as mr

    original = mr.REGISTRY
    mr.REGISTRY = dup
    try:
        with pytest.raises(ValueError, match="Duplicate claude_id"):
            registry_by_claude_id()
    finally:
        mr.REGISTRY = original


def test_current_pricing_empty_rows_raises() -> None:
    entry = ModelEntry("claude-empty", "gpt-empty", (), "fast")
    with pytest.raises(ValueError, match="no pricing rows"):
        current_pricing(entry)


def test_current_pricing_picks_most_recent_row() -> None:
    entry = ModelEntry(
        claude_id="claude-test",
        codex_id="gpt-test",
        pricing=(
            ModelPricing(1.00, 2.00, 0.50, 0.10, date(2025, 1, 1)),
            ModelPricing(2.00, 4.00, 1.00, 0.20, date(2026, 1, 1)),
            ModelPricing(1.50, 3.00, 0.75, 0.15, date(2025, 6, 1)),
        ),
        tier="fast",
    )
    current = current_pricing(entry)
    assert current.effective_from == date(2026, 1, 1)
    assert current.input_per_mtok == 2.00


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
        ModelEntry(
            "claude-a", "gpt-collide", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "deep"
        ),
        ModelEntry(
            "claude-b", "gpt-collide", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "dispatch"
        ),
        ModelEntry("claude-c", "gpt-fast", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "fast"),
        ModelEntry(
            "claude-d", "gpt-plg", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "standard"
        ),
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
        ModelEntry("claude-a", "gpt-x", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "deep"),
        ModelEntry("claude-b", "gpt-y", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "deep"),
        ModelEntry("claude-c", "gpt-d", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "dispatch"),
        ModelEntry("claude-e", "gpt-f", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "fast"),
        ModelEntry("claude-g", "gpt-p", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "standard"),
    )
    original = mr.REGISTRY
    mr.REGISTRY = ambiguous
    try:
        with pytest.raises(ValueError, match="multiple Codex ids"):
            codex_tier_views()
    finally:
        mr.REGISTRY = original
