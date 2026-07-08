"""Unit tests for features/telemetry/pricing.py (T-AM-10).

``PRICING_TABLE`` is now a DERIVED view over ``core.model_registry``. The two
contradictory haiku pins (``claude-haiku-3-5`` at the old lines 47/212, which
disagreed with the mapping table's ``claude-haiku-4-5-20251001``) are resolved
here to the single canonical id, and a cross-table key-equality contract test
replaces the implicit per-table assumptions.
"""

from __future__ import annotations

from datetime import date

import pytest

from dadaia_workspace.core.model_registry import REGISTRY
from dadaia_workspace.features.telemetry import pricing
from dadaia_workspace.features.telemetry.pricing import (
    PRICING_TABLE,
    ModelPricing,
    compute_cost,
    pricing_age_days,
)
from dadaia_workspace.infrastructure.runtime_transforms.model_mapping import MODEL_MAP

# ---------------------------------------------------------------------------
# compute_cost
# ---------------------------------------------------------------------------


class TestComputeCost:
    def test_known_model_current_window(self) -> None:
        """claude-opus-4-7: 1M input + 500k output at 2026-01-01.

        Cost = (1_000_000 * 15.00 + 500_000 * 75.00) / 1_000_000
             = (15_000_000 + 37_500_000) / 1_000_000
             = 52.50 USD = 52_500_000 micro-USD.
        """
        usage = {"input_tokens": 1_000_000, "output_tokens": 500_000}
        result = compute_cost(usage, "claude-opus-4-7", date(2026, 1, 1))
        assert result == 52_500_000

    @pytest.mark.parametrize(
        "model,usage,when,expected",
        [
            # claude-sonnet-4-6: 1M input, 1M output at 2026-01-01
            # = (3.00 + 15.00) = $18.00 = 18_000_000 micro-USD
            (
                "claude-sonnet-4-6",
                {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
                date(2026, 1, 1),
                18_000_000,
            ),
            # claude-haiku-4-5-20251001 (drift resolved): 1M input only at
            # 2026-01-01 = 0.80 USD = 800_000 micro-USD (haiku-tier pricing
            # preserved under the canonical 4-5 id).
            (
                "claude-haiku-4-5-20251001",
                {"input_tokens": 1_000_000},
                date(2026, 1, 1),
                800_000,
            ),
        ],
    )
    def test_known_models_parametrized(
        self,
        model: str,
        usage: dict,
        when: date,
        expected: int,
    ) -> None:
        assert compute_cost(usage, model, when) == expected

    def test_known_model_historical_effective_from(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Historical events use the price vigent at their occurrence date.

        Patch PRICING_TABLE to add a future row at 2027-01-01 with doubled prices.
        An event from 2026-01-01 must still use the 2025 prices.
        """
        patched: dict[str, list[ModelPricing]] = {
            "claude-opus-4-7": [
                ModelPricing(15.00, 75.00, 18.75, 1.50, date(2025, 1, 1)),
                ModelPricing(30.00, 150.00, 37.50, 3.00, date(2027, 1, 1)),
            ],
        }
        monkeypatch.setattr(pricing, "PRICING_TABLE", patched)

        usage = {"input_tokens": 1_000_000, "output_tokens": 0}

        # 2026-01-01 is before 2027 row → must use 2025 prices (15.00/MTok)
        result_2026 = compute_cost(usage, "claude-opus-4-7", date(2026, 1, 1))
        assert result_2026 == 15_000_000

        # 2027-06-01 is after 2027 row → must use 2027 prices (30.00/MTok)
        result_2027 = compute_cost(usage, "claude-opus-4-7", date(2027, 6, 1))
        assert result_2027 == 30_000_000

    def test_unknown_model_returns_none(self) -> None:
        result = compute_cost({"input_tokens": 1_000_000}, "unknown-model-x", date(2026, 1, 1))
        assert result is None

    def test_usage_zero_returns_zero(self) -> None:
        result = compute_cost(
            {"input_tokens": 0, "output_tokens": 0}, "claude-opus-4-7", date(2026, 1, 1)
        )
        assert result == 0

    def test_missing_usage_keys_default_to_zero(self) -> None:
        result = compute_cost({}, "claude-opus-4-7", date(2026, 1, 1))
        assert result == 0

    def test_negative_values_clamped_to_zero(self) -> None:
        """Negative input_tokens are clamped; only the valid output is priced.

        output_tokens=1_000_000 at claude-opus-4-7 (75.00/MTok) = $75 = 75_000_000 µUSD.
        """
        usage = {"input_tokens": -100, "output_tokens": 1_000_000}
        result = compute_cost(usage, "claude-opus-4-7", date(2026, 1, 1))
        assert result == 75_000_000

    def test_cache_tokens_priced_correctly(self) -> None:
        """claude-opus-4-7: 1M cache_creation only.

        cache_creation_per_mtok = 18.75 → 18.75 USD = 18_750_000 micro-USD.
        """
        usage = {"cache_creation_input_tokens": 1_000_000}
        result = compute_cost(usage, "claude-opus-4-7", date(2026, 1, 1))
        assert result == 18_750_000

    def test_cache_read_tokens_priced_correctly(self) -> None:
        """claude-opus-4-7: 1M cache_read only.

        cache_read_per_mtok = 1.50 → 1.50 USD = 1_500_000 micro-USD.
        """
        usage = {"cache_read_input_tokens": 1_000_000}
        result = compute_cost(usage, "claude-opus-4-7", date(2026, 1, 1))
        assert result == 1_500_000

    def test_result_is_int_not_float(self) -> None:
        usage = {"input_tokens": 1_000_000}
        result = compute_cost(usage, "claude-sonnet-4-6", date(2026, 1, 1))
        assert isinstance(result, int)

    def test_result_never_negative(self) -> None:
        # Even with extreme negative clamping, result must be >= 0.
        usage = {"input_tokens": -999_999_999, "output_tokens": -999_999_999}
        result = compute_cost(usage, "claude-opus-4-7", date(2026, 1, 1))
        assert result is not None
        assert result >= 0

    def test_no_applicable_row_before_effective_from(self) -> None:
        """When event date is before all effective_from rows, return None."""
        result = compute_cost(
            {"input_tokens": 1_000_000},
            "claude-opus-4-7",
            date(2024, 12, 31),  # before 2025-01-01 row
        )
        assert result is None


# ---------------------------------------------------------------------------
# pricing_age_days
# ---------------------------------------------------------------------------


class TestPricingAgeDays:
    def test_pricing_age_days_basic(self) -> None:
        """Single model, explicit when — should be 181 days from 2025-01-01 to 2025-07-01."""
        result = pricing_age_days(["claude-opus-4-7"], when=date(2025, 7, 1))
        assert result == 181

    def test_pricing_age_days_default_today(self) -> None:
        """Without explicit when, defaults to today — must be >= 0."""
        result = pricing_age_days(["claude-opus-4-7"])
        assert result is not None
        assert isinstance(result, int)
        assert result >= 0

    def test_pricing_age_days_empty_returns_none(self) -> None:
        result = pricing_age_days([])
        assert result is None

    def test_pricing_age_days_unknown_only_returns_none(self) -> None:
        result = pricing_age_days(["unknown-x"], when=date(2026, 1, 1))
        assert result is None

    def test_pricing_age_days_picks_newest_across_models(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When multiple models are used, picks the latest effective_from among them.

        Model A has newest row at 2025-01-01 (old).
        Model B has newest row at 2025-06-01 (newer).
        With when=2026-01-01, age should be based on 2025-06-01 → 214 days.
        """
        patched: dict[str, list[ModelPricing]] = {
            "model-a": [
                ModelPricing(1.00, 2.00, 0.50, 0.10, date(2025, 1, 1)),
            ],
            "model-b": [
                ModelPricing(1.00, 2.00, 0.50, 0.10, date(2025, 1, 1)),
                ModelPricing(1.50, 2.50, 0.75, 0.15, date(2025, 6, 1)),
            ],
        }
        monkeypatch.setattr(pricing, "PRICING_TABLE", patched)

        result = pricing_age_days(["model-a", "model-b"], when=date(2026, 1, 1))
        # 2026-01-01 - 2025-06-01 = 214 days
        assert result == 214

    def test_pricing_age_days_mixed_known_unknown(self) -> None:
        """Unknown models are ignored; known models still contribute."""
        result = pricing_age_days(
            ["claude-opus-4-7", "totally-unknown-llm"],
            when=date(2025, 7, 1),
        )
        # Only claude-opus-4-7 is known (2025-01-01); 2025-07-01 - 2025-01-01 = 181 days
        assert result == 181

    def test_pricing_age_days_all_models_same_effective_from(self) -> None:
        """All three baseline models have 2025-01-01; from 2026-01-01 = 365 days."""
        result = pricing_age_days(
            ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
            when=date(2026, 1, 1),
        )
        assert result == 365


# ---------------------------------------------------------------------------
# Cross-table contract + derived-view correctness (registry single source).
# ---------------------------------------------------------------------------


class TestRegistryDerivedView:
    def test_pricing_table_keys_equal_registry_claude_ids(self) -> None:
        assert set(PRICING_TABLE) == {entry.claude_id for entry in REGISTRY}

    def test_model_map_and_pricing_table_key_sets_identical(self) -> None:
        """The contract that closes the drift bug: both derived views share an
        identical key-set (== the registry claude_ids)."""
        assert set(MODEL_MAP) == set(PRICING_TABLE)
        assert set(PRICING_TABLE) == {entry.claude_id for entry in REGISTRY}

    def test_pricing_rows_are_ascending_by_effective_from(self) -> None:
        """Derived view preserves dated rows ascending (newest last) so the
        most-recent row wins in compute_cost."""
        for rows in PRICING_TABLE.values():
            dates = [r.effective_from for r in rows]
            assert dates == sorted(dates)

    def test_derived_rows_match_registry_pricing(self) -> None:
        index = {e.claude_id: e for e in REGISTRY}
        for claude_id, rows in PRICING_TABLE.items():
            assert set(rows) == set(index[claude_id].pricing)

    def test_sonnet_5_priced_via_derived_view(self) -> None:
        """FR6/D-2 (v0.1.65): sonnet-5 costs at the sonnet cost class from 2026-07-01."""
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
        # 3.00 + 15.00 = $18.00 = 18_000_000 micro-USD.
        assert compute_cost(usage, "claude-sonnet-5", date(2026, 7, 1)) == 18_000_000
        # Before the effective date there is no applicable row.
        assert compute_cost(usage, "claude-sonnet-5", date(2026, 6, 30)) is None

    def test_fable_5_priced_via_derived_view(self) -> None:
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
        # 10.00 + 50.00 = $60.00 = 60_000_000 micro-USD.
        assert compute_cost(usage, "claude-fable-5", date(2026, 6, 1)) == 60_000_000
