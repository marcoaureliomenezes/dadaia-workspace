"""Pricing table for AI models — derived view. Versioned via effective_from
date: historical events use the price vigent at their occurrence date,
preserving reproducibility.

Per SPEC § "Tabela de preços" (D-AM-07). ``PRICING_TABLE`` is no longer
hand-maintained here: it is **derived** from the single source of truth in
:mod:`dadaia_workspace.core.model_registry` (claude_id → dated pricing rows).
This guarantees its key-set is identical to ``MODEL_MAP``'s (also derived from
the same registry) — closing bug ``model-catalog-modelmap-pricing-drift-no-registry``.
To change a price, append a new dated row to the registry — NEVER replace an
existing row. (features → core imports are permitted by the layering contracts.)

``ModelPricing`` is re-exported from the registry for backward compatibility:
existing consumers (``from ...telemetry.pricing import ModelPricing``) and the
unit tests keep working unchanged.

Cost arithmetic:
    total_usd = (
        input * input_per_mtok
        + output * output_per_mtok
        + cache_creation * cache_creation_per_mtok
        + cache_read * cache_read_per_mtok
    ) / 1_000_000

Convert to micro-USD: int(round(total_usd * 1_000_000)).
Rounding uses Python built-in round() — banker's rounding (round-half-to-even).
For the micro-USD precision required here, float arithmetic is adequate.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from dadaia_workspace.core.model_registry import REGISTRY, ModelPricing

__all__ = ["ModelPricing", "PRICING_TABLE", "compute_cost", "pricing_age_days"]


# Derived view — key: model_id; value: dated rows ascending by effective_from
# (NEWEST LAST), matching the historical contract consumers rely on.
PRICING_TABLE: dict[str, list[ModelPricing]] = {
    entry.claude_id: sorted(entry.pricing, key=lambda r: r.effective_from) for entry in REGISTRY
}
# Unknown models: compute_cost returns None → cost_micro_usd NULL.


def compute_cost(usage: dict[str, Any], model: str, when: date) -> int | None:
    """Return cost in micro-USD (10^-6 USD) for the event, or None if model unknown.

    Args:
        usage: dict with keys input_tokens, output_tokens,
               cache_creation_input_tokens, cache_read_input_tokens.
               Missing keys default to 0. Negative values are clamped to 0.
        model: model identifier (key in PRICING_TABLE).
        when:  event date — selects the pricing row with the latest
               effective_from that is <= when.

    Returns:
        Cost as a non-negative int (micro-USD), or None when:
        - model not in PRICING_TABLE, or
        - no row has effective_from <= when (model "didn't exist" at that date).

        Returns 0 (not None) when usage is empty or all-zero — zero cost is valid.
    """
    rows = PRICING_TABLE.get(model)
    if rows is None:
        return None

    # Select all rows applicable at `when`, then pick the newest.
    applicable = [r for r in rows if r.effective_from <= when]
    if not applicable:
        return None

    pricing = max(applicable, key=lambda r: r.effective_from)

    # Clamp negative token counts to 0 (defensive).
    input_tok = max(0, usage.get("input_tokens", 0))
    output_tok = max(0, usage.get("output_tokens", 0))
    cache_creation_tok = max(0, usage.get("cache_creation_input_tokens", 0))
    cache_read_tok = max(0, usage.get("cache_read_input_tokens", 0))

    total_usd = (
        input_tok * pricing.input_per_mtok
        + output_tok * pricing.output_per_mtok
        + cache_creation_tok * pricing.cache_creation_per_mtok
        + cache_read_tok * pricing.cache_read_per_mtok
    ) / 1_000_000

    return int(round(total_usd * 1_000_000))


def pricing_age_days(
    models_used: list[str],
    when: date | None = None,
) -> int | None:
    """Return age in days of the newest pricing row across all models used.

    Used by the frontend to render a staleness banner when the result exceeds
    PRICING_STALENESS_THRESHOLD_DAYS (budget.py).

    Args:
        models_used: list of model identifiers to inspect.
        when:        reference date; defaults to date.today() when None.

    Returns:
        Age as a non-negative int (days), or None when:
        - models_used is empty, or
        - none of the models appear in PRICING_TABLE.

        "Newest" means the latest effective_from across the newest row of each
        known model — measures freshness of the source of truth.
    """
    if when is None:
        when = date.today()

    newest: date | None = None
    for model in models_used:
        rows = PRICING_TABLE.get(model)
        if not rows:
            continue
        # Newest row for this model.
        model_newest = max(rows, key=lambda r: r.effective_from).effective_from
        if newest is None or model_newest > newest:
            newest = model_newest

    if newest is None:
        return None

    return (when - newest).days
