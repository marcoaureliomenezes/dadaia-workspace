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
        codex_id="gpt-5.6-sol",
        pricing=(ModelPricing(10.00, 50.00, 12.50, 1.00, date(2026, 6, 1)),),
        tier="deep",
    ),
    ModelEntry(
        claude_id="claude-opus-4-7",
        codex_id="gpt-5.6-sol",
        pricing=(ModelPricing(15.00, 75.00, 18.75, 1.50, date(2025, 1, 1)),),
        tier="dispatch",
    ),
    ModelEntry(
        claude_id="claude-opus-4-8",
        codex_id="gpt-5.6-sol",
        pricing=(ModelPricing(15.00, 75.00, 18.75, 1.50, date(2025, 1, 1)),),
        tier="dispatch",
    ),
    ModelEntry(
        # Claude Opus 5 — the current Opus-tier model (operator remap). Shares the
        # dispatch tier with 4.7/4.8, so it MUST carry their codex_id: a tier
        # resolving to two Codex ids raises in ``_codex_id_for_tier``.
        claude_id="claude-opus-5",
        codex_id="gpt-5.6-sol",
        pricing=(ModelPricing(5.00, 25.00, 6.25, 0.50, date(2026, 7, 1)),),
        tier="dispatch",
    ),
    ModelEntry(
        claude_id="claude-sonnet-4-6",
        codex_id="gpt-5.6-terra",
        pricing=(ModelPricing(3.00, 15.00, 3.75, 0.30, date(2025, 1, 1)),),
        tier="plugin",
    ),
    ModelEntry(
        # v0.1.65 FR6/D-2: sonnet-5 shares sonnet-4-6's cost class and codex
        # mapping. ``tier="plugin"`` is a FORCED cost-axis label (decoupled from
        # dispatch-band/agent behavior — D-2 addendum, F-4); any other tier
        # violates the _codex_id_for_tier / codex_tier_views invariants. The
        # 'plugin' tier-NAME mismatch is a tracked backlog return.
        claude_id="claude-sonnet-5",
        codex_id="gpt-5.6-terra",
        pricing=(ModelPricing(3.00, 15.00, 3.75, 0.30, date(2026, 7, 1)),),
        tier="plugin",
    ),
    ModelEntry(
        # Haiku drift resolved: canonical id is haiku-4-5; the historical
        # haiku-tier pricing (was keyed under the dropped ``claude-haiku-3-5``)
        # is preserved here so past telemetry costed at the haiku tier resolves.
        claude_id="claude-haiku-4-5-20251001",
        codex_id="gpt-5.3-codex-spark",
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


# ---------------------------------------------------------------------------
# Per-runtime tier view (bug codex-personas-claude-model-tiering-leak).
#
# On Codex a tier's identity is the PAIR (model id, model_reasoning_effort).
# ``deep`` and ``dispatch`` legitimately share the same Codex model id
# (``gpt-5.5`` today); they are kept DISTINCT by their reasoning effort
# (``deep`` -> high, ``dispatch`` -> medium). This view is the single source of
# truth for both the Codex agent-TOML ``model_reasoning_effort`` field and the
# per-runtime tier table rendered into Codex persona bodies, so neither is a
# string-mapped shadow of the Anthropic-only registry.
# ---------------------------------------------------------------------------

# Codex reasoning effort. ``deep`` reasoning leaves run at ``high``; everything
# else runs at ``medium`` (Codex's mid profile). This is the native Codex tiering
# axis that the persona prose must teach instead of Anthropic tier names.
CodexEffort = Literal["high", "medium", "low"]

_CODEX_TIER_EFFORT: dict[Tier, CodexEffort] = {
    "deep": "high",
    "dispatch": "medium",
    "plugin": "medium",
    "fast": "medium",
}


@dataclass(frozen=True)
class CodexTierView:
    """The Codex-native rendering of a registry tier: a (model id, effort) PAIR.

    Two distinct registry tiers may share ``codex_id`` only when their
    ``reasoning_effort`` differs — otherwise the tier distinction collapses and
    projection must fail loudly (see :func:`codex_tier_views`).
    """

    tier: Tier
    codex_id: str
    reasoning_effort: CodexEffort


# Ordered tier presentation for the rendered Codex tier table (most → least
# capable). Every registry ``Tier`` literal MUST appear exactly once.
_CODEX_TIER_ORDER: tuple[Tier, ...] = ("deep", "dispatch", "plugin", "fast")


def _codex_id_for_tier(tier: Tier) -> str:
    """Return the Codex model id assigned to *tier* by the registry.

    Resolves the tier's Codex id from the registry entries carrying that tier.

    Raises:
        ValueError: if no registry entry carries *tier*, or if entries carrying
            *tier* disagree on their ``codex_id`` (an ambiguous tier → id map).
    """
    codex_ids = {entry.codex_id for entry in REGISTRY if entry.tier == tier}
    if not codex_ids:
        raise ValueError(f"No REGISTRY entry carries tier {tier!r}")
    if len(codex_ids) > 1:
        raise ValueError(
            f"Tier {tier!r} maps to multiple Codex ids {sorted(codex_ids)!r}; "
            "a tier must resolve to a single Codex model id"
        )
    return codex_ids.pop()


def codex_tier_views() -> tuple[CodexTierView, ...]:
    """Return the per-runtime Codex tier views, in presentation order.

    Each registry tier resolves to a :class:`CodexTierView` carrying its Codex
    model id and reasoning effort. This is the single source of truth consumed
    by both the agent-TOML ``model_reasoning_effort`` field and the persona tier
    table.

    Raises:
        ValueError: if two DISTINCT tiers collapse to an IDENTICAL
            (codex_id, reasoning_effort) PAIR — that erases the very distinction
            the tier table exists to teach. The error names both colliding
            tiers. (Also propagates the ambiguity errors of
            :func:`_codex_id_for_tier`.)
    """
    views: list[CodexTierView] = []
    seen: dict[tuple[str, CodexEffort], Tier] = {}
    for tier in _CODEX_TIER_ORDER:
        codex_id = _codex_id_for_tier(tier)
        effort = _CODEX_TIER_EFFORT[tier]
        key = (codex_id, effort)
        if key in seen:
            other = seen[key]
            raise ValueError(
                f"Codex tier collapse: tiers {other!r} and {tier!r} both resolve "
                f"to the identical (model={codex_id!r}, "
                f"model_reasoning_effort={effort!r}) pair; differentiate their "
                "reasoning effort in _CODEX_TIER_EFFORT or their model id"
            )
        seen[key] = tier
        views.append(CodexTierView(tier=tier, codex_id=codex_id, reasoning_effort=effort))
    return tuple(views)


def codex_effort_for_tier(tier: Tier) -> CodexEffort:
    """Return the Codex ``model_reasoning_effort`` assigned to *tier*."""
    return _CODEX_TIER_EFFORT[tier]
