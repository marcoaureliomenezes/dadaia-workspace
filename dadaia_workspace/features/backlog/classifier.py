"""Deterministic conflict classifier — Python disposes, fail-closed (SPEC §3.3, ADR-B).

Python owns the UNRELATED/DUPLICATE/DIVERGENT_CONFLICT boundary via canonical-anchor
**set-intersection**; the model never decides UNRELATED-vs-not:

1. Python computes the canonical-anchor set intersection between a new item and every existing
   item. **Empty intersection → ``UNRELATED``** (final, no model call).
2. For each shared-anchor pair, Python checks change-equality → **``DUPLICATE``** if every
   shared anchor carries an identical change.
3. A shared-anchor pair with **differing** change is **``DIVERGENT_CONFLICT``** — no model
   call (acceptance §3.7.3).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "BoundItem",
    "Classification",
    "Verdict",
    "classify",
]


class Verdict(StrEnum):
    """The relationship class between a new backlog item and an existing one (SPEC §3.3)."""

    UNRELATED = "unrelated"
    DUPLICATE = "duplicate"
    DIVERGENT_CONFLICT = "divergent_conflict"


@dataclass(frozen=True)
class BoundItem:
    """A backlog item reduced to its bound canonical anchors and their changes.

    ``anchor_changes`` maps a canonical anchor id → the ``change`` string declared against it.
    Both the new item and every existing item are pre-bound (the registry already resolved
    each subject to an anchor) before the classifier runs — the classifier is pure arithmetic
    over anchor sets, never resolution.
    """

    slug: str
    anchor_changes: dict[str, str] = field(default_factory=dict)

    @property
    def anchors(self) -> set[str]:
        return set(self.anchor_changes)


@dataclass(frozen=True)
class Classification:
    """One pairwise verdict between the new item and an existing item."""

    other_slug: str
    verdict: Verdict
    shared_anchors: tuple[str, ...] = ()


def _classify_pair(
    new: BoundItem,
    existing: BoundItem,
) -> Classification:
    shared = sorted(new.anchors & existing.anchors)

    # (1) Empty intersection → UNRELATED (Python only, never consults the model).
    if not shared:
        return Classification(other_slug=existing.slug, verdict=Verdict.UNRELATED)

    # Partition shared anchors into same-change vs differing-change.
    differing = [a for a in shared if new.anchor_changes[a] != existing.anchor_changes[a]]

    # (2) Every shared anchor carries an identical change → DUPLICATE.
    if not differing:
        return Classification(
            other_slug=existing.slug, verdict=Verdict.DUPLICATE, shared_anchors=tuple(shared)
        )

    # (3) At least one shared anchor differs → DIVERGENT_CONFLICT.
    return Classification(
        other_slug=existing.slug,
        verdict=Verdict.DIVERGENT_CONFLICT,
        shared_anchors=tuple(shared),
    )


def classify(
    new: BoundItem,
    existing: Sequence[BoundItem],
) -> list[Classification]:
    """Classify ``new`` against every item in ``existing``.

    Returns one :class:`Classification` per existing item, in input order.
    """
    return [_classify_pair(new, item) for item in existing]
