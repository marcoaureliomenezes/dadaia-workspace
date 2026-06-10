"""Single source of truth for AI model identity, mapping, pricing, and tier —
``core/model_registry.py``.

Historically two hand-maintained tables drifted apart (bug
``model-catalog-modelmap-pricing-drift-no-registry``):

- ``MODEL_MAP`` (``infrastructure/runtime_transforms/model_mapping.py``) — Claude
  id → Codex id, used so Codex TOML never contains a ``claude-*`` string (ADR-5).
- ``PRICING_TABLE`` (``features/telemetry/pricing.py``) — Claude id → dated
  pricing rows, used to cost telemetry events.

They had no shared registry, so adding/changing a model required editing both by
hand and nothing detected a desync — which is how the haiku id drifted
(``haiku-4-5-20251001`` in the mapping vs ``haiku-3-5`` in pricing).

This module is the **single registry**: one ``REGISTRY`` tuple of
:class:`ModelEntry`, each carrying the Codex id, the dated (append-only) pricing
history, and the tier. ``MODEL_MAP`` and ``PRICING_TABLE`` become *derived views*
over this registry (see the consuming modules), so both are guaranteed to share
an identical key-set and a single source of truth.

Layering: this is pure data with zero I/O and no OS-primitive imports, so it
lives in ``core`` where both ``infrastructure`` and ``features`` may import it
(import-linter ``core-no-os-primitives`` contract holds — this module imports
only ``dataclasses``/``datetime``/``typing`` stdlib).

Pricing history is **append-only and dated**: to change a price, append a new
:class:`ModelPricing` row with a later ``effective_from`` — never mutate or drop
an existing row. The "current" price for a model is the row with the most-recent
``effective_from`` (see :func:`current_pricing`).

Haiku resolution (bug fix): the canonical haiku id is
``claude-haiku-4-5-20251001`` (matching the live mapping and agent frontmatter).
The historical haiku-tier pricing (0.80 / 4.00 / 1.00 / 0.08, effective
2025-01-01) is preserved under that id so past telemetry costed at the haiku tier
still resolves. The standalone ``claude-haiku-3-5`` pricing key is dropped — it
never had a ``MODEL_MAP`` entry and only survives as a malformed-line reader
fixture (not cost-asserted).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

# Tier names. ``deep`` = deep-reasoning leaves (spec/QA/arch/audit/harness),
# ``dispatch`` = dispatchers + gate leaves, ``fast`` = high-volume mechanical,
# ``plugin`` = plugin-stub agents (no behavior until the plugin is installed).
Tier = Literal["deep", "dispatch", "fast", "plugin"]


@dataclass(frozen=True)
class ModelPricing:
    """Prices per million tokens (USD/MTok) effective from a given date.

    Append-only: a price change is a *new* row with a later ``effective_from``;
    existing rows are never mutated, so historical telemetry stays reproducible.
    """

    input_per_mtok: float
    output_per_mtok: float
    cache_creation_per_mtok: float
    cache_read_per_mtok: float
    effective_from: date


@dataclass(frozen=True)
class ModelEntry:
    """A single model's identity, Codex mapping, pricing history, and tier.

    Attributes:
        claude_id: The canonical Claude model id as it appears in agent
            frontmatter (e.g. ``"claude-sonnet-4-6"``).
        codex_id: The Codex model id this maps to (Codex TOML must never contain
            a ``claude-*`` string — ADR-5).
        pricing: Dated pricing rows, append-only. MUST be non-empty.
        tier: The model's assignment tier.
    """

    claude_id: str
    codex_id: str
    pricing: tuple[ModelPricing, ...] = field(default=())
    tier: Tier = "dispatch"


def current_pricing(entry: ModelEntry) -> ModelPricing:
    """Return the most-recent (largest ``effective_from``) pricing row.

    Raises:
        ValueError: if the entry has no pricing rows (registry invariant
            violation — every entry MUST carry at least one row).
    """
    if not entry.pricing:
        raise ValueError(f"ModelEntry {entry.claude_id!r} has no pricing rows")
    return max(entry.pricing, key=lambda r: r.effective_from)


# ---------------------------------------------------------------------------
# THE REGISTRY — single source of truth.
#
# Every Claude model id used anywhere in the fleet appears exactly once here.
# MODEL_MAP and PRICING_TABLE are derived from this tuple; do not maintain those
# tables by hand.
# ---------------------------------------------------------------------------
REGISTRY: tuple[ModelEntry, ...] = (
    ModelEntry(
        claude_id="claude-fable-5",
        codex_id="gpt-5.5",
        pricing=(ModelPricing(10.00, 50.00, 12.50, 1.00, date(2026, 6, 1)),),
        tier="deep",
    ),
    ModelEntry(
        claude_id="claude-opus-4-7",
        codex_id="gpt-5.5",
        pricing=(ModelPricing(15.00, 75.00, 18.75, 1.50, date(2025, 1, 1)),),
        tier="dispatch",
    ),
    ModelEntry(
        claude_id="claude-opus-4-8",
        codex_id="gpt-5.5",
        pricing=(ModelPricing(15.00, 75.00, 18.75, 1.50, date(2025, 1, 1)),),
        tier="dispatch",
    ),
    ModelEntry(
        claude_id="claude-sonnet-4-6",
        codex_id="gpt-5.3-codex",
        pricing=(ModelPricing(3.00, 15.00, 3.75, 0.30, date(2025, 1, 1)),),
        tier="plugin",
    ),
    ModelEntry(
        # Haiku drift resolved: canonical id is haiku-4-5; the historical
        # haiku-tier pricing (was keyed under the dropped ``claude-haiku-3-5``)
        # is preserved here so past telemetry costed at the haiku tier resolves.
        claude_id="claude-haiku-4-5-20251001",
        codex_id="gpt-5.4-mini",
        pricing=(ModelPricing(0.80, 4.00, 1.00, 0.08, date(2025, 1, 1)),),
        tier="fast",
    ),
)


def registry_by_claude_id() -> dict[str, ModelEntry]:
    """Return the registry indexed by ``claude_id`` (insertion order preserved).

    Raises:
        ValueError: on a duplicate ``claude_id`` (registry invariant violation).
    """
    index: dict[str, ModelEntry] = {}
    for entry in REGISTRY:
        if entry.claude_id in index:
            raise ValueError(f"Duplicate claude_id in REGISTRY: {entry.claude_id!r}")
        index[entry.claude_id] = entry
    return index
