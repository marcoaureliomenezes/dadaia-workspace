"""Claude-to-Codex model identifier mapping (ADR-5) — derived view.

The canonical agent frontmatter uses Claude model identifiers (e.g.
``claude-sonnet-4-6``).  Codex TOML files must not contain any ``claude-*``
strings (AC3).  This module provides the authoritative translation table and a
helper that raises explicitly on unknown identifiers so that ``dadaia public
install --target codex`` fails loudly rather than silently emitting a bad model
field.

``MODEL_MAP`` is no longer hand-maintained: it is **derived** from the single
source of truth in :mod:`dadaia_workspace.core.model_registry` (claude_id →
codex_id). This guarantees its key-set is identical to ``PRICING_TABLE``'s
(also derived from the same registry) — closing the drift documented in bug
``model-catalog-modelmap-pricing-drift-no-registry``. (infrastructure → core
imports are permitted by the layering contracts.)
"""

from __future__ import annotations

from dadaia_workspace.core.model_registry import REGISTRY

# Derived view: claude_id -> codex_id, in registry order.
MODEL_MAP: dict[str, str] = {entry.claude_id: entry.codex_id for entry in REGISTRY}


def map_model(claude_id: str) -> str:
    """Return the Codex model identifier for *claude_id*.

    Args:
        claude_id: A Claude model identifier as it appears in agent frontmatter
            (e.g. ``"claude-sonnet-4-6"``).

    Returns:
        The corresponding Codex model identifier string.

    Raises:
        ValueError: If *claude_id* is not present in :data:`MODEL_MAP`.
    """
    if claude_id not in MODEL_MAP:
        raise ValueError(f"No Codex mapping for model: {claude_id!r}")
    return MODEL_MAP[claude_id]
