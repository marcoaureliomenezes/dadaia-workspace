"""Unit tests for features/telemetry/pricing.py (T-AM-10)."""
from __future__ import annotations

from datetime import date

import pytest

from dadaia_workspace.features.telemetry import pricing
from dadaia_workspace.features.telemetry.pricing import (
    ModelPricing,
    compute_cost,
    pricing_age_days,
)


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
            # claude-haiku-3-5: 1M input only at 2026-01-01
            # = 0.80 USD = 800_000 micro-USD
            (
                "claude-haiku-3-5",
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

    def test_known_model_historical_effective_from(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
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
        result = compute_cost(
            {"input_tokens": 1_000_000}, "unknown-model-x", date(2026, 1, 1)
        )
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
            ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-3-5"],
            when=date(2026, 1, 1),
        )
        assert result == 365
