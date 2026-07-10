"""Unit tests for features/telemetry/pricing.py (T-AM-10).

``PRICING_TABLE`` is now a DERIVED view over ``core.model_registry``. The two
contradictory haiku pins (``claude-haiku-3-5`` at the old lines 47/212, which
disagreed with the mapping table's ``claude-haiku-4-5-20251001``) are resolved
here to the single canonical id, and a cross-table key-equality contract test
replaces the implicit per-table assumptions — the drift-closing registry-derived
contract is the surviving keyset test, kept named.
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
# Known-model costs, cache tokens, sonnet-5/fable-5 derived rows — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model", "usage", "when", "expected"),
    [
        pytest.param(
            "claude-opus-4-7",
            {"input_tokens": 1_000_000, "output_tokens": 500_000},
            date(2026, 1, 1),
            52_500_000,
            id="opus-4-7-input-plus-output",
        ),
        pytest.param(
            "claude-sonnet-4-6",
            {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
            date(2026, 1, 1),
            18_000_000,
            id="sonnet-4-6-input-plus-output",
        ),
        pytest.param(
            "claude-haiku-4-5-20251001",
            {"input_tokens": 1_000_000},
            date(2026, 1, 1),
            800_000,
            id="haiku-4-5-drift-resolved",
        ),
        pytest.param(
            "claude-opus-4-7",
            {"cache_creation_input_tokens": 1_000_000},
            date(2026, 1, 1),
            18_750_000,
            id="cache-creation-priced",
        ),
        pytest.param(
            "claude-opus-4-7",
            {"cache_read_input_tokens": 1_000_000},
            date(2026, 1, 1),
            1_500_000,
            id="cache-read-priced",
        ),
        pytest.param(
            "claude-sonnet-5",
            {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
            date(2026, 7, 1),
            18_000_000,
            id="sonnet-5-derived-view",
        ),
        pytest.param(
            "claude-fable-5",
            {"input_tokens": 1_000_000, "output_tokens": 1_000_000},
            date(2026, 6, 1),
            60_000_000,
            id="fable-5-derived-view",
        ),
    ],
)
def test_known_model_costs_matrix(
    model: str, usage: dict[str, int], when: date, expected: int
) -> None:
    assert compute_cost(usage, model, when) == expected


def test_known_model_historical_effective_from_windowing(monkeypatch: pytest.MonkeyPatch) -> None:
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

    # sonnet-5 (real registry data): no applicable row before the effective date.
    sonnet_usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert compute_cost(sonnet_usage, "claude-sonnet-5", date(2026, 6, 30)) is None


# ---------------------------------------------------------------------------
# Edge cases: unknown/zero/missing/negative/int/never-negative/before-effective
# + pricing_age_days variants — 1 param + 1 test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("usage", "model", "when", "expected"),
    [
        pytest.param({"input_tokens": 1_000_000}, "unknown-model-x", date(2026, 1, 1), None, id="unknown-model-none"),
        pytest.param({"input_tokens": 0, "output_tokens": 0}, "claude-opus-4-7", date(2026, 1, 1), 0, id="zero-usage-zero-cost"),
        pytest.param({}, "claude-opus-4-7", date(2026, 1, 1), 0, id="missing-keys-default-zero"),
        pytest.param(
            {"input_tokens": -100, "output_tokens": 1_000_000},
            "claude-opus-4-7",
            date(2026, 1, 1),
            75_000_000,
            id="negative-input-clamped",
        ),
        pytest.param(
            {"input_tokens": -999_999_999, "output_tokens": -999_999_999},
            "claude-opus-4-7",
            date(2026, 1, 1),
            0,
            id="extreme-negative-never-negative-result",
        ),
        pytest.param(
            {"input_tokens": 1_000_000},
            "claude-opus-4-7",
            date(2024, 12, 31),
            None,
            id="before-all-effective-from-rows",
        ),
    ],
)
def test_compute_cost_edge_cases(
    usage: dict[str, int], model: str, when: date, expected: int | None
) -> None:
    result = compute_cost(usage, model, when)
    assert result == expected
    if expected is not None:
        assert isinstance(result, int)


def test_pricing_age_days_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    # basic explicit-when.
    assert pricing_age_days(["claude-opus-4-7"], when=date(2025, 7, 1)) == 181
    # default today: must be >= 0.
    default_result = pricing_age_days(["claude-opus-4-7"])
    assert default_result is not None and isinstance(default_result, int) and default_result >= 0
    # empty models -> None.
    assert pricing_age_days([]) is None
    # unknown-only -> None.
    assert pricing_age_days(["unknown-x"], when=date(2026, 1, 1)) is None
    # mixed known/unknown: unknown ignored.
    assert pricing_age_days(["claude-opus-4-7", "totally-unknown-llm"], when=date(2025, 7, 1)) == 181
    # all baseline models same effective_from.
    assert (
        pricing_age_days(
            ["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
            when=date(2026, 1, 1),
        )
        == 365
    )

    # picks the NEWEST effective_from across multiple models (not the oldest).
    patched: dict[str, list[ModelPricing]] = {
        "model-a": [ModelPricing(1.00, 2.00, 0.50, 0.10, date(2025, 1, 1))],
        "model-b": [
            ModelPricing(1.00, 2.00, 0.50, 0.10, date(2025, 1, 1)),
            ModelPricing(1.50, 2.50, 0.75, 0.15, date(2025, 6, 1)),
        ],
    }
    monkeypatch.setattr(pricing, "PRICING_TABLE", patched)
    assert pricing_age_days(["model-a", "model-b"], when=date(2026, 1, 1)) == 214


# ---------------------------------------------------------------------------
# Cross-table contract — the drift-closing registry-derived keyset (kept named)
# ---------------------------------------------------------------------------


def test_model_map_and_pricing_table_keyset_identical_to_registry() -> None:
    """The contract that closes the drift bug: MODEL_MAP, PRICING_TABLE, and
    core.model_registry.REGISTRY all share an identical claude_id key-set."""
    registry_ids = {entry.claude_id for entry in REGISTRY}
    assert set(PRICING_TABLE) == registry_ids
    assert set(MODEL_MAP) == set(PRICING_TABLE)

    # Derived view correctness: PRICING_TABLE rows must exactly mirror the registry's
    # own pricing rows for every claude_id.
    index = {e.claude_id: e for e in REGISTRY}
    for claude_id, rows in PRICING_TABLE.items():
        assert set(rows) == set(index[claude_id].pricing)
