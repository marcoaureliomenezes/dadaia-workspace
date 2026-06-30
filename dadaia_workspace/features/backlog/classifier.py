"""Deterministic conflict classifier — Python disposes, fail-closed (SPEC §3.3, ADR-B).

Python owns the UNRELATED/DUPLICATE/DIVERGENT_CONFLICT boundary via canonical-anchor
**set-intersection**; the model never decides UNRELATED-vs-not:

1. Python computes the canonical-anchor set intersection between a new item and every existing
   item. **Empty intersection → ``UNRELATED``** (final, no model call).
2. For each shared-anchor pair, Python checks change-equality → **``DUPLICATE``** if every
   shared anchor carries an identical change.
3. A shared-anchor pair with **differing** change defaults **fail-closed** to
   **``DIVERGENT_CONFLICT``**. A model may only **downgrade** it (to ``OVERLAP``/``SUPERSEDES``)
   with an explicit, structured, proven-compatible merge — it can never *miss* a conflict.

R1 ships the deterministic core (steps 1–2 + the fail-closed default of step 3). The model
downgrade is a ``Callable`` seam, **offline by default** (``no_downgrade``): the
``C->D``/``C->E`` divergent twin is classified with ZERO model calls (acceptance §3.7.3).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "BoundItem",
    "Classification",
    "Downgrade",
    "Verdict",
    "classify",
    "no_downgrade",
]


class Verdict(StrEnum):
    """The relationship class between a new backlog item and an existing one (SPEC §3.3)."""

    UNRELATED = "unrelated"
    DUPLICATE = "duplicate"
    OVERLAP = "overlap"
    SUPERSEDES = "supersedes"
    DIVERGENT_CONFLICT = "divergent_conflict"
    DEPENDS_ON = "depends_on"


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


#: A model-downgrade seam: given two change strings (new, existing) it MAY return a downgraded
#: verdict (``OVERLAP``/``SUPERSEDES``/``DEPENDS_ON``) when it can prove compatibility, else
#: ``None`` to keep the fail-closed ``DIVERGENT_CONFLICT``. Offline in R1.
Downgrade = Callable[[str, str], "Verdict | None"]


def no_downgrade(_new_change: str, _existing_change: str) -> Verdict | None:
    """The default downgrade seam: never downgrade (model OFFLINE — fail-closed)."""
    return None


#: The ONLY verdicts a ``downgrade`` callable may use to narrow a fail-closed
#: ``DIVERGENT_CONFLICT``. The clamp accepts a downgrade verdict only if it is in this set;
#: any other value (``UNRELATED``, ``DUPLICATE``, ``DIVERGENT_CONFLICT`` itself, garbage, or
#: ``None``) keeps the pair ``DIVERGENT_CONFLICT``. This is the boundary guard that prevents a
#: wired-in model from *masking* a real conflict — the model can narrow the conflict's name
#: but can never erase it (SPEC §3 WS-3 boundary clamp; CRITICAL fail-open fix).
_ALLOWED_DOWNGRADE_VERDICTS: frozenset[Verdict] = frozenset(
    {Verdict.OVERLAP, Verdict.SUPERSEDES, Verdict.DEPENDS_ON}
)


def _classify_pair(
    new: BoundItem,
    existing: BoundItem,
    downgrade: Downgrade,
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

    # (3) At least one shared anchor differs → fail-closed DIVERGENT_CONFLICT by default.
    # The model downgrade seam may override ONLY this branch, and only with a verdict in the
    # clamp set {OVERLAP, SUPERSEDES, DEPENDS_ON}. Any other value the callable returns
    # (UNRELATED, DUPLICATE, DIVERGENT_CONFLICT, garbage, or None) is rejected here and the
    # pair stays DIVERGENT_CONFLICT — a model can narrow the conflict's name, never erase it.
    first = differing[0]
    downgraded = downgrade(new.anchor_changes[first], existing.anchor_changes[first])
    if downgraded in _ALLOWED_DOWNGRADE_VERDICTS:
        return Classification(
            other_slug=existing.slug, verdict=downgraded, shared_anchors=tuple(shared)
        )
    return Classification(
        other_slug=existing.slug,
        verdict=Verdict.DIVERGENT_CONFLICT,
        shared_anchors=tuple(shared),
    )


def classify(
    new: BoundItem,
    existing: Sequence[BoundItem],
    *,
    downgrade: Downgrade = no_downgrade,
) -> list[Classification]:
    """Classify ``new`` against every item in ``existing``.

    Returns one :class:`Classification` per existing item, in input order. With the default
    ``no_downgrade`` seam the model is OFFLINE: a shared-anchor + differing-change pair is
    ``DIVERGENT_CONFLICT`` with zero model calls (acceptance §3.7.3). The model is consulted
    ONLY on the differing-change branch — never for an UNRELATED or DUPLICATE pair.
    """
    return [_classify_pair(new, item, downgrade) for item in existing]
