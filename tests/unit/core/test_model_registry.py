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
