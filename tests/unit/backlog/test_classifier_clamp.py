"""Unit tests for the ``_classify_pair`` downgrade clamp (v0.1.43 T-43-6b, SPEC §3 WS-3).

The classifier is the boundary owner for the fail-closed ``DIVERGENT_CONFLICT`` verdict. A
model wired into the ``downgrade`` seam may *narrow* a conflict's name to
``OVERLAP``/``SUPERSEDES``/``DEPENDS_ON`` on proven-compatible evidence, but it must never be
able to *mask* a real conflict by returning ``UNRELATED``/``DUPLICATE``/garbage. These tests
prove the clamp accepts a downgrade verdict only when it is in
``{OVERLAP, SUPERSEDES, DEPENDS_ON}`` and otherwise keeps ``DIVERGENT_CONFLICT`` (AC-5
adversarial).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.backlog.classifier import (
    BoundItem,
    Verdict,
    classify,
    no_downgrade,
)

_ANCHOR = "anchor.shared"

# A shared-anchor, differing-change pair — the only branch the model downgrade can touch.
_NEW = BoundItem(slug="new-item", anchor_changes={_ANCHOR: "C becomes E"})
_EXISTING = BoundItem(slug="existing-item", anchor_changes={_ANCHOR: "C becomes D"})


def _classify_one(downgrade) -> Verdict:  # type: ignore[no-untyped-def]
    results = classify(_NEW, [_EXISTING], downgrade=downgrade)
    assert len(results) == 1
    return results[0].verdict


@pytest.mark.parametrize("allowed", [Verdict.OVERLAP, Verdict.SUPERSEDES, Verdict.DEPENDS_ON])
def test_allowed_downgrade_verdicts_are_applied(allowed: Verdict) -> None:
    """OVERLAP / SUPERSEDES / DEPENDS_ON each downgrade the pair correctly."""
    assert _classify_one(lambda _n, _e: allowed) is allowed


@pytest.mark.parametrize(
    "masking",
    [
        Verdict.UNRELATED,
        Verdict.DUPLICATE,
        Verdict.DIVERGENT_CONFLICT,
        None,
    ],
)
def test_conflict_masking_verdicts_are_rejected(masking: Verdict | None) -> None:
    """UNRELATED / DUPLICATE / DIVERGENT_CONFLICT / None can never erase the conflict."""
    assert _classify_one(lambda _n, _e: masking) is Verdict.DIVERGENT_CONFLICT

    if masking is None:
        # The default offline seam (no_downgrade, returns None) is the production
        # instance of this same None-masking branch — pin it directly too.
        assert _classify_one(no_downgrade) is Verdict.DIVERGENT_CONFLICT


@pytest.mark.parametrize("garbage", ["unrelated-typo", "merge?", "OVERLAP ", "", "garbage"])
def test_arbitrary_string_verdicts_are_rejected(garbage: str) -> None:
    """An arbitrary (non-Verdict) string from the seam leaves the pair DIVERGENT_CONFLICT."""
    assert _classify_one(lambda _n, _e: garbage) is Verdict.DIVERGENT_CONFLICT  # type: ignore[arg-type,return-value]


def test_downgrade_only_consulted_on_differing_branch() -> None:
    """UNRELATED (no shared anchor) and DUPLICATE (identical change) never call the seam."""
    calls: list[tuple[str, str]] = []

    def spy(new_change: str, existing_change: str) -> Verdict | None:
        calls.append((new_change, existing_change))
        return Verdict.OVERLAP

    unrelated = BoundItem(slug="u", anchor_changes={"other.anchor": "x"})
    duplicate = BoundItem(slug="d", anchor_changes={_ANCHOR: "C becomes E"})
    results = classify(_NEW, [unrelated, duplicate], downgrade=spy)
    assert results[0].verdict is Verdict.UNRELATED
    assert results[1].verdict is Verdict.DUPLICATE
    assert calls == []  # seam never consulted off the differing-change branch
