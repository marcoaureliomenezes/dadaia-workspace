"""Unit tests for features/telemetry/budget.py (T-AM-08).

Verifies all constants are positive integers within sensible bounds.
"""

from __future__ import annotations

import dadaia_workspace.features.telemetry.budget as budget


class TestBudgetConstants:
    def test_all_constants_are_int(self) -> None:
        assert isinstance(budget.MAX_BYTES_PER_FILE_PER_CYCLE, int)
        assert isinstance(budget.MAX_LINE_LENGTH, int)
        assert isinstance(budget.MAX_EVENTS_PER_CYCLE, int)
        assert isinstance(budget.CACHE_TTL_SECONDS, int)
        assert isinstance(budget.PRICING_STALENESS_THRESHOLD_DAYS, int)
        assert isinstance(budget.MAX_TOKEN_COUNT_PER_EVENT, int)

    def test_all_constants_are_positive(self) -> None:
        assert budget.MAX_BYTES_PER_FILE_PER_CYCLE > 0
        assert budget.MAX_LINE_LENGTH > 0
        assert budget.MAX_EVENTS_PER_CYCLE > 0
        assert budget.CACHE_TTL_SECONDS > 0
        assert budget.PRICING_STALENESS_THRESHOLD_DAYS > 0
        assert budget.MAX_TOKEN_COUNT_PER_EVENT > 0

    def test_max_bytes_per_file_per_cycle_bounds(self) -> None:
        """Between 1 MB and 100 MB."""
        one_mb = 1 * 1024 * 1024
        hundred_mb = 100 * 1024 * 1024
        assert one_mb <= budget.MAX_BYTES_PER_FILE_PER_CYCLE <= hundred_mb

    def test_max_line_length_bounds(self) -> None:
        """Between 1 KB and 1 MB."""
        one_kb = 1 * 1024
        one_mb = 1 * 1024 * 1024
        assert one_kb <= budget.MAX_LINE_LENGTH <= one_mb

    def test_max_events_per_cycle_bounds(self) -> None:
        """Between 100 and 1_000_000."""
        assert 100 <= budget.MAX_EVENTS_PER_CYCLE <= 1_000_000

    def test_cache_ttl_seconds_bounds(self) -> None:
        """Between 1 and 600 seconds."""
        assert 1 <= budget.CACHE_TTL_SECONDS <= 600

    def test_pricing_staleness_threshold_days_bounds(self) -> None:
        """Between 1 and 365 days."""
        assert 1 <= budget.PRICING_STALENESS_THRESHOLD_DAYS <= 365

    def test_max_token_count_per_event_bounds(self) -> None:
        """Between 100_000 and 100_000_000."""
        assert 100_000 <= budget.MAX_TOKEN_COUNT_PER_EVENT <= 100_000_000
