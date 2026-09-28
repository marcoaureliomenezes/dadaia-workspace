"""Unit tests for the deterministic conflict classifier (T-25-04, SPEC §3.3, ADR-B).

Python disposes the UNRELATED/DUPLICATE/DIVERGENT_CONFLICT boundary via canonical-anchor
**set-intersection**. The model never decides UNRELATED-vs-not. The dangerous twin
(``C->D`` then ``C->E``) is classified ``DIVERGENT_CONFLICT`` with the model **OFFLINE** —
the acceptance §3.7.3 hermetic test. Fixtures are plain in-memory ``BoundItem`` objects (no
live repo, no I/O).

Fail-closed conflict default (model offline => DIVERGENT_CONFLICT) is the safety property —
kept verbatim below.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.backlog.classifier import (
    BoundItem,
    Verdict,
    classify,
)

pytestmark = pytest.mark.unit


def _item(slug: str, anchor_changes: dict[str, str]) -> BoundItem:
    return BoundItem(slug=slug, anchor_changes=dict(anchor_changes))


def test_unrelated_when_no_shared_anchor_or_empty_backlog() -> None:
    new = _item("new", {"a#X": "do X"})
    existing = [_item("old", {"b#Y": "do Y"})]
    results = classify(new, existing)
    assert len(results) == 1
    assert results[0].verdict is Verdict.UNRELATED
    assert results[0].other_slug == "old"

    assert classify(new, []) == []


def test_duplicate_when_all_shared_anchors_equal() -> None:
    new = _item("new", {"a#X": "remove X"})
    existing = [_item("old", {"a#X": "remove X"})]
    results = classify(new, existing)
    assert results[0].verdict is Verdict.DUPLICATE

    # Shares two anchors; both changes identical → DUPLICATE.
    multi_new = _item("new", {"a#X": "rm X", "b#Y": "rm Y"})
    multi_existing = [_item("old", {"a#X": "rm X", "b#Y": "rm Y"})]
    assert classify(multi_new, multi_existing)[0].verdict is Verdict.DUPLICATE


def test_divergent_conflict_c_to_d_then_c_to_e_model_offline() -> None:
    """The C->D / C->E divergent twin classifies DIVERGENT_CONFLICT with ZERO model calls.

    Python
    set-intersection alone must catch it (fail-closed default) — the safety property.
    """
    c_to_d = _item("c-to-d", {"subject_C#anchor": "change to D"})
    c_to_e = _item("c-to-e", {"subject_C#anchor": "change to E"})
    results = classify(c_to_e, [c_to_d])  # model offline
    assert results[0].verdict is Verdict.DIVERGENT_CONFLICT
    assert results[0].other_slug == "c-to-d"


def test_divergent_when_one_of_many_shared_anchors_differs() -> None:
    partial_new = _item("new", {"a#X": "rm X", "c#Z": "change to E"})
    partial_existing = [_item("old", {"a#X": "rm X", "c#Z": "change to D"})]
    assert classify(partial_new, partial_existing)[0].verdict is Verdict.DIVERGENT_CONFLICT
