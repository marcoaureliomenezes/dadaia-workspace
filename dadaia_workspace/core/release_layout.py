"""The ONE place that knows the RULES of how a release is laid out.

Why this module exists
----------------------
A release has two shapes: flat (``releases/<id>/SPEC.md``, what ``release new`` writes)
and segmented (``releases/<id>/<segment>/SPEC.md``, what ``specs release open`` writes and
what every real release actually uses, maturing ``alpha-1 → alpha-2 → rc-1``).

That fact was re-derived independently in a dozen modules, and the copies drifted. The
same segment-nesting defect was then found THREE separate times, in three modules:

* ``build_release_spec_path`` looked only at the flat SPEC, so ``backlog consume`` never
  found a real release's SPEC and silently reported "nothing to consume";
* ``_release_still_in_flight`` looked only at the flat CLOSURE, so ``read_consumed``
  returned ``{}`` forever and BL-STALE could never fire on any real release;
* segment ORDERING was written twice, with two different implementations.

Patching each copy where it is found is the failure mode that made the deleted workflow
engine unusable: a fix that lands on one copy leaves the others wrong, so the same bug
reappears wearing a different name and the surface grows with every patch.

Why this module is PURE
-----------------------
``core`` is file-I/O-free by ratchet (architect A9), and that boundary is worth more than
the convenience of putting a ``Path.iterdir`` here. So this module owns the **rules** —
ordering, precedence, which filename means closed — and the caller supplies the directory
listing. Listing a directory is one line that cannot drift in meaning; the rules are what
drifted, and they now have exactly one definition.
"""

from __future__ import annotations

from collections.abc import Iterable

#: The artifact that marks a release (or one of its segments) as closed.
CLOSURE_ARTIFACT = "CLOSURE.md"

#: The segment kinds, in maturation order. A release matures alpha-N then rc-N.
SEGMENT_KINDS: tuple[str, ...] = ("alpha", "rc")


def segment_sort_key(name: str) -> tuple[int, int, str]:
    """Order segments the way they mature: ``alpha-1 < alpha-2 < alpha-10 < rc-1``.

    Numeric, not lexicographic — plain string ordering puts ``alpha-10`` before
    ``alpha-2`` and would resolve a matured release to a stale artifact.
    """
    kind, _, number = name.partition("-")
    rank = SEGMENT_KINDS.index(kind) if kind in SEGMENT_KINDS else len(SEGMENT_KINDS)
    try:
        return (rank, int(number), name)
    except ValueError:
        return (rank, 0, name)


def ordered_segments(names: Iterable[str]) -> list[str]:
    """The given segment names in maturation order; the last one is the current segment."""
    return sorted(names, key=segment_sort_key)


def next_segment_name(existing: Iterable[str]) -> str:
    """The segment that should be opened next, given the ones that exist.

    A release still in alpha advances its alpha; one that has reached rc advances its rc.
    """
    highest = dict.fromkeys(SEGMENT_KINDS, 0)
    for name in existing:
        kind, _, number = name.partition("-")
        if kind in highest and number.isdigit():
            highest[kind] = max(highest[kind], int(number))
    kind = "rc" if highest["rc"] else "alpha"
    return f"{kind}-{highest[kind] + 1}"
