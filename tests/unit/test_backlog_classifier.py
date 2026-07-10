"""Unit tests for the deterministic conflict classifier (T-25-04, SPEC §3.3, ADR-B).

Python disposes the UNRELATED/DUPLICATE/DIVERGENT_CONFLICT boundary via canonical-anchor
**set-intersection**. The model never decides UNRELATED-vs-not. The dangerous twin
(``C->D`` then ``C->E``) is classified ``DIVERGENT_CONFLICT`` with the model **OFFLINE** —
the acceptance §3.7.3 hermetic test. Fixtures are plain in-memory ``BoundItem`` objects (no
live repo, no I/O).

Fail-closed conflict default (model offline => DIVERGENT_CONFLICT) is the safety property —
kept verbatim below, alongside the never-downgrades-UNRELATED-or-DUPLICATE guard.
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

    The classifier is called WITHOUT a downgrade callable — the model is OFFLINE. Python
    set-intersection alone must catch it (fail-closed default) — the safety property.
    """
    c_to_d = _item("c-to-d", {"subject_C#anchor": "change to D"})
    c_to_e = _item("c-to-e", {"subject_C#anchor": "change to E"})
    results = classify(c_to_e, [c_to_d])  # model offline (no downgrade arg)
    assert results[0].verdict is Verdict.DIVERGENT_CONFLICT
    assert results[0].other_slug == "c-to-d"


def test_divergent_when_one_anchor_differs_no_default_model_call_and_downgrade_seam() -> None:
    """Divergent verdict when only ONE of many shared anchors differs; the default
    (no-downgrade) path never invokes a model (proven with a spy); and the downgrade
    seam, when explicitly wired, may downgrade the same pair to OVERLAP."""
    partial_new = _item("new", {"a#X": "rm X", "c#Z": "change to E"})
    partial_existing = [_item("old", {"a#X": "rm X", "c#Z": "change to D"})]
    assert classify(partial_new, partial_existing)[0].verdict is Verdict.DIVERGENT_CONFLICT

    calls: list[tuple[str, str]] = []

    def spy_downgrade(a: str, b: str) -> Verdict | None:
        calls.append((a, b))
        return None

    new = _item("new", {"a#X": "to E"})
    existing = [_item("old", {"a#X": "to D"})]
    # Even WITH a downgrade callable wired, the fail-closed default stands unless the
    # model actively downgrades. The spy records that it WAS consulted but returned
    # None.
    results = classify(new, existing, downgrade=spy_downgrade)
    assert results[0].verdict is Verdict.DIVERGENT_CONFLICT
    # Default (no-downgrade) path used in the offline acceptance test must NOT call any
    # model.
    classify(new, existing)
    assert len(calls) == 1  # only the explicit spy run consulted the model, once.

    def downgrade(_a: str, _b: str) -> Verdict:
        return Verdict.OVERLAP

    assert classify(new, existing, downgrade=downgrade)[0].verdict is Verdict.OVERLAP


def test_model_cannot_downgrade_unrelated_or_duplicate() -> None:
    """The downgrade seam only fires for the conflict default — never overrides Python."""

    def downgrade(_a: str, _b: str) -> Verdict:
        return Verdict.OVERLAP  # would be wrong for an UNRELATED/DUPLICATE pair

    # UNRELATED stays UNRELATED (no shared anchor → never consults the model).
    unrelated = classify(_item("n", {"a#X": "c"}), [_item("o", {"b#Y": "c"})], downgrade=downgrade)
    assert unrelated[0].verdict is Verdict.UNRELATED
    # DUPLICATE stays DUPLICATE.
    dup = classify(_item("n", {"a#X": "c"}), [_item("o", {"a#X": "c"})], downgrade=downgrade)
    assert dup[0].verdict is Verdict.DUPLICATE


# ---------------------------------------------------------------------------
# Relocated from tests/integration/test_backlog_conflict_scan_consult.py (T-7, v0.1.75):
# _parse_downgrade_verdict is a pure function — no fs/subprocess/model call.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("overlap", Verdict.OVERLAP),
        ("OVERLAP", Verdict.OVERLAP),
        (" supersedes ", Verdict.SUPERSEDES),
        ("depends_on", None),  # wrapper is stricter than the clamp on purpose
        ("divergent_conflict", None),
        ("unrelated", None),
        ("duplicate", None),
        ("garbage", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_downgrade_verdict(raw: str | None, expected: Verdict | None) -> None:
    from dadaia_workspace.features.lifecycle.workflows.backlog_definition import (
        _parse_downgrade_verdict,
    )

    assert _parse_downgrade_verdict(raw) is expected
