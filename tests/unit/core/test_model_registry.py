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


def test_no_duplicate_claude_ids() -> None:
    ids = [entry.claude_id for entry in REGISTRY]
    assert len(ids) == len(set(ids)), f"duplicate claude_id in REGISTRY: {ids}"


def test_every_entry_has_tier_codex_id_and_pricing() -> None:
    for entry in REGISTRY:
        assert entry.codex_id, f"{entry.claude_id} has empty codex_id"
        assert entry.tier in ("deep", "dispatch", "fast", "plugin")
        assert entry.pricing, f"{entry.claude_id} has no pricing rows"


def test_codex_id_never_contains_claude_prefix() -> None:
    """ADR-5: Codex TOML must never carry a claude-* string."""
    for entry in REGISTRY:
        assert not entry.codex_id.startswith("claude-")


def test_pricing_rows_carry_effective_date() -> None:
    for entry in REGISTRY:
        for row in entry.pricing:
            assert isinstance(row.effective_from, date)


def test_pricing_history_is_append_only_distinct_dates() -> None:
    """Append-only history: each model's rows have strictly distinct dates so a
    'current' row is unambiguous."""
    for entry in REGISTRY:
        dates = [row.effective_from for row in entry.pricing]
        assert len(dates) == len(set(dates)), f"{entry.claude_id} has duplicate effective_from"


def test_registry_by_claude_id_indexes_all_entries() -> None:
    index = registry_by_claude_id()
    assert set(index) == {entry.claude_id for entry in REGISTRY}
    assert len(index) == len(REGISTRY)


def test_registry_by_claude_id_raises_on_duplicate() -> None:
    dup = (
        ModelEntry("claude-x", "gpt-x", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "fast"),
        ModelEntry("claude-x", "gpt-y", (ModelPricing(2, 2, 2, 2, date(2025, 1, 1)),), "fast"),
    )
    import dadaia_workspace.core.model_registry as mr

    original = mr.REGISTRY
    mr.REGISTRY = dup  # type: ignore[misc]
    try:
        with pytest.raises(ValueError, match="Duplicate claude_id"):
            registry_by_claude_id()
    finally:
        mr.REGISTRY = original  # type: ignore[misc]


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


def test_current_pricing_raises_when_no_rows() -> None:
    entry = ModelEntry("claude-empty", "gpt-empty", (), "fast")
    with pytest.raises(ValueError, match="no pricing rows"):
        current_pricing(entry)


# ---------------------------------------------------------------------------
# Content invariants resolving the documented bug.
# ---------------------------------------------------------------------------


def test_haiku_id_resolved_to_4_5() -> None:
    """Bug fix: the canonical haiku id is haiku-4-5-20251001 (the 3-5 drift is gone)."""
    index = registry_by_claude_id()
    assert "claude-haiku-4-5-20251001" in index
    assert "claude-haiku-3-5" not in index
    haiku = index["claude-haiku-4-5-20251001"]
    # Historical haiku-tier pricing preserved under the 4-5 id.
    current = current_pricing(haiku)
    assert current.input_per_mtok == 0.80
    assert current.output_per_mtok == 4.00


# ---------------------------------------------------------------------------
# Per-runtime Codex tier view (bug codex-personas-claude-model-tiering-leak).
# ---------------------------------------------------------------------------


def test_codex_tier_views_yield_id_and_effort_for_every_tier() -> None:
    """Each registry tier renders to a Codex (model id, reasoning effort) pair."""
    views = codex_tier_views()
    tiers = {v.tier for v in views}
    assert tiers == {"deep", "dispatch", "fast", "plugin"}
    for view in views:
        assert view.codex_id, f"{view.tier} has empty codex_id"
        assert not view.codex_id.startswith("claude-")
        assert view.reasoning_effort in ("high", "medium", "low")


def test_current_registry_is_collapse_free() -> None:
    """The LIVE registry must not collapse two distinct tiers into one
    (model id, reasoning effort) pair — proves the live values are valid."""
    views = codex_tier_views()  # raises on collapse
    pairs = [(v.codex_id, v.reasoning_effort) for v in views]
    assert len(pairs) == len(set(pairs)), f"tier collapse in live registry: {pairs}"


def test_deep_and_dispatch_share_id_but_differ_on_effort() -> None:
    """deep and dispatch share gpt-5.5 today; their effort keeps them distinct."""
    by_tier = {v.tier: v for v in codex_tier_views()}
    assert by_tier["deep"].codex_id == by_tier["dispatch"].codex_id
    assert by_tier["deep"].reasoning_effort == "high"
    assert by_tier["dispatch"].reasoning_effort == "medium"


def test_codex_effort_for_tier_mapping() -> None:
    assert codex_effort_for_tier("deep") == "high"
    assert codex_effort_for_tier("dispatch") == "medium"
    assert codex_effort_for_tier("fast") == "medium"
    assert codex_effort_for_tier("plugin") == "medium"


def test_codex_tier_views_raises_on_synthetic_collapse() -> None:
    """A synthetic registry whose deep and dispatch tiers resolve to the IDENTICAL
    (model id, effort) pair must raise, naming both tiers."""
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
        ModelEntry("claude-d", "gpt-plg", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "plugin"),
    )
    original_reg = mr.REGISTRY
    original_effort = dict(mr._CODEX_TIER_EFFORT)
    mr.REGISTRY = colliding  # type: ignore[misc]
    mr._CODEX_TIER_EFFORT["dispatch"] = "high"  # collapse: deep & dispatch both high
    try:
        with pytest.raises(ValueError, match="Codex tier collapse.*deep.*dispatch|dispatch.*deep"):
            codex_tier_views()
    finally:
        mr.REGISTRY = original_reg  # type: ignore[misc]
        mr._CODEX_TIER_EFFORT.clear()
        mr._CODEX_TIER_EFFORT.update(original_effort)


def test_codex_tier_views_raises_when_tier_maps_to_multiple_ids() -> None:
    """A tier carried by entries with disagreeing codex_ids is ambiguous → raise."""
    import dadaia_workspace.core.model_registry as mr

    ambiguous = (
        ModelEntry("claude-a", "gpt-x", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "deep"),
        ModelEntry("claude-b", "gpt-y", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "deep"),
        ModelEntry("claude-c", "gpt-d", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "dispatch"),
        ModelEntry("claude-e", "gpt-f", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "fast"),
        ModelEntry("claude-g", "gpt-p", (ModelPricing(1, 1, 1, 1, date(2025, 1, 1)),), "plugin"),
    )
    original = mr.REGISTRY
    mr.REGISTRY = ambiguous  # type: ignore[misc]
    try:
        with pytest.raises(ValueError, match="multiple Codex ids"):
            codex_tier_views()
    finally:
        mr.REGISTRY = original  # type: ignore[misc]


def test_sonnet_5_entry_present_with_expected_mapping_tier_and_pricing() -> None:
    """FR6/D-2 (v0.1.65): claude-sonnet-5 → gpt-5.3-codex, tier 'plugin' (forced
    cost-axis label, sonnet cost class), pricing 3.00/15.00/3.75/0.30 from 2026-07-01."""
    index = registry_by_claude_id()
    assert "claude-sonnet-5" in index
    sonnet5 = index["claude-sonnet-5"]
    assert sonnet5.codex_id == "gpt-5.3-codex"
    assert sonnet5.tier == "plugin"
    current = current_pricing(sonnet5)
    assert (
        current.input_per_mtok,
        current.output_per_mtok,
        current.cache_creation_per_mtok,
        current.cache_read_per_mtok,
        current.effective_from,
    ) == (3.00, 15.00, 3.75, 0.30, date(2026, 7, 1))


def test_fable_5_entry_present_with_expected_pricing() -> None:
    index = registry_by_claude_id()
    assert "claude-fable-5" in index
    fable = index["claude-fable-5"]
    current = current_pricing(fable)
    assert (
        current.input_per_mtok,
        current.output_per_mtok,
        current.cache_creation_per_mtok,
        current.cache_read_per_mtok,
        current.effective_from,
    ) == (10.00, 50.00, 12.50, 1.00, date(2026, 6, 1))
    assert fable.tier == "deep"
