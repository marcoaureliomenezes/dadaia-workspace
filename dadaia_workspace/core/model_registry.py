"""Single source of truth for AI model identity, Codex mapping and tier —
``core/model_registry.py``.

``MODEL_MAP`` (``infrastructure/runtime_transforms/model_mapping.py``, Claude id ->
Codex id, so Codex TOML never contains a ``claude-*`` string — ADR-5) is a derived
view over :data:`REGISTRY`; adding a model is one entry here (bug
``model-catalog-modelmap-pricing-drift-no-registry``).

Layering: pure data, zero I/O, stdlib-only imports, so both ``infrastructure`` and
``features`` may import it (import-linter ``core-no-os-primitives`` holds).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# Tier names. ``deep`` = deep-reasoning leaves (spec/QA/arch/audit/harness),
# ``dispatch`` = dispatchers + gate leaves, ``fast`` = high-volume mechanical,
# ``standard`` = the mid-cost general implementation tier.
Tier = Literal["deep", "dispatch", "fast", "standard"]


@dataclass(frozen=True)
class ModelEntry:
    """A single model's identity, Codex mapping, and tier.

    Attributes:
        claude_id: The canonical Claude model id as it appears in agent
            frontmatter (e.g. ``"claude-sonnet-4-6"``).
        codex_id: The Codex model id this maps to (Codex TOML must never contain
            a ``claude-*`` string — ADR-5).
        tier: The model's assignment tier.
    """

    claude_id: str
    codex_id: str
    tier: Tier = "dispatch"


# ---------------------------------------------------------------------------
# THE REGISTRY — single source of truth.
#
# Every Claude model id used anywhere in the fleet appears exactly once here.
# MODEL_MAP is derived from this tuple; never maintain it by hand.
# ---------------------------------------------------------------------------
REGISTRY: tuple[ModelEntry, ...] = (
    ModelEntry(
        claude_id="claude-fable-5",
        codex_id="gpt-5.6-sol",
        tier="deep",
    ),
    ModelEntry(
        claude_id="claude-fable-5-1",
        codex_id="gpt-5.6-sol",
        tier="deep",
    ),
    ModelEntry(
        claude_id="claude-opus-4-7",
        codex_id="gpt-5.6-sol",
        tier="dispatch",
    ),
    ModelEntry(
        claude_id="claude-opus-4-8",
        codex_id="gpt-5.6-sol",
        tier="dispatch",
    ),
    ModelEntry(
        # Claude Opus 5 (operator remap). Shares the
        # dispatch tier with 4.7/4.8, so it MUST carry their codex_id: a tier
        # resolving to two Codex ids raises in ``_codex_id_for_tier``.
        claude_id="claude-opus-5",
        codex_id="gpt-5.6-sol",
        tier="dispatch",
    ),
    ModelEntry(
        # Claude Opus 5.5 — the current Opus (ADR 0022); dispatch tier, so opus-5's codex_id.
        claude_id="claude-opus-5-5",
        codex_id="gpt-5.6-sol",
        tier="dispatch",
    ),
    ModelEntry(
        claude_id="claude-sonnet-4-6",
        codex_id="gpt-5.6-terra",
        tier="standard",
    ),
    ModelEntry(
        # v0.1.65 FR6/D-2: sonnet-5 shares sonnet-4-6's codex mapping.
        # ``tier="standard"`` is a FORCED label (decoupled from
        # dispatch-band/agent behavior — D-2 addendum, F-4); any other tier
        # violates the _codex_id_for_tier / codex_tier_views invariants.
        claude_id="claude-sonnet-5",
        codex_id="gpt-5.6-terra",
        tier="standard",
    ),
    ModelEntry(
        claude_id="claude-haiku-4-5-20251001",
        codex_id="gpt-5.3-codex-spark",
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


def fable_model_ids() -> frozenset[str]:
    """The Fable family — every registered ``claude-fable-*`` id. The G-1 ruling
    ("Fable is never assigned to dd-code-reviewer") is a FAMILY rule; both guards
    (template import, policy-store parse) derive it from here, never from one literal
    id that goes stale at the next Fable release (bug
    g1-fable-guard-matches-only-claude-fable-5-so-fable-5-1-lands-on-security-reviewer)."""
    return frozenset(e.claude_id for e in REGISTRY if e.claude_id.startswith("claude-fable-"))


def is_fable_model(claude_id: str) -> bool:
    return claude_id in fable_model_ids()


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
    "standard": "medium",
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
_CODEX_TIER_ORDER: tuple[Tier, ...] = ("deep", "dispatch", "standard", "fast")


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
