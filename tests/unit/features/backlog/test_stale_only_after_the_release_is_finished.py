"""A backlog item is not stale while the release consuming it is still in flight.

Bug ``r25-release-definition-leaves-consumed-backlog-stale`` (validator R25 / R-02). After
``release-definition`` completes, ``backlog doctor`` fails:

    [ERROR] BL-STALE [<slug>] slug is recorded as consumed in an archived release's
    consumed_backlog ledger but still exists in specs/backlog/

So between definition and closure the tree fails the product's own validator, for a state
the product itself just created. An operator running the doctor at that point is told their
workspace is broken when it is exactly where the workflow left it.

The contradiction is in the model, not the operator's tree: ``release-definition`` writes
``_archive/<id>/consumed_backlog.json`` at DEFINITION time, while the item is only removed
at CLOSURE. The doctor reads "any archived release's ledger" and concludes the slug is
consumed-but-present — which is true, and not yet a problem. The ledger records intent when
it is written and completion only once closure has archived the item body.

The regression this check exists for is preserved and pinned below: bug
``r18-closure-leaves-consumed-backlog-item``, where a CLOSED release left its item behind,
still reports BL-STALE. That is the case the operator must hear about.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.backlog.ledger import read_consumed

pytestmark = pytest.mark.unit

_SLUG = "an-authored-item"


def _tree(tmp_path: Path, *, closed: bool) -> tuple[Path, Path]:
    specs = tmp_path / "specs"
    release = specs / "releases" / "v0.1.0"
    release.mkdir(parents=True)
    (release / "SPEC.md").write_text("# SPEC\n", encoding="utf-8")
    if closed:
        (release / "CLOSURE.md").write_text("# CLOSURE\n", encoding="utf-8")
    archive = specs / "_archive"
    (archive / "v0.1.0").mkdir(parents=True)
    (archive / "v0.1.0" / "consumed_backlog.json").write_text(
        json.dumps({"release": "v0.1.0", "consumed": [{"slug": _SLUG, "shipped_anchors": []}]}),
        encoding="utf-8",
    )
    return specs, archive


def test_an_in_flight_release_does_not_make_its_pick_stale(tmp_path: Path) -> None:
    specs, archive = _tree(tmp_path, closed=False)

    consumed = read_consumed(archive, specs_dir=specs)

    assert consumed == {}, (
        "the release is still open — its item is where the workflow left it, and calling "
        f"that stale tells the operator their tree is broken when it is not: {consumed}"
    )


def test_a_closed_release_still_reports_its_leftover(tmp_path: Path) -> None:
    """The regression BL-STALE exists for (r18-closure-leaves-consumed-backlog-item)."""
    specs, archive = _tree(tmp_path, closed=True)

    consumed = read_consumed(archive, specs_dir=specs)

    assert _SLUG in consumed, (
        "a CLOSED release that left its consumed item behind is exactly what this check "
        "was built to catch; relaxing it must not silence that"
    )


def test_a_release_whose_directory_is_gone_still_counts(tmp_path: Path) -> None:
    """An archived-away release has no live directory; its ledger is final."""
    specs, archive = _tree(tmp_path, closed=False)
    for path in sorted((specs / "releases" / "v0.1.0").iterdir()):
        path.unlink()
    (specs / "releases" / "v0.1.0").rmdir()

    assert _SLUG in read_consumed(archive, specs_dir=specs)


def test_without_a_specs_dir_the_reader_is_unchanged(tmp_path: Path) -> None:
    """Back-compat: every existing caller that passes only the archive root still works."""
    _, archive = _tree(tmp_path, closed=False)

    assert _SLUG in read_consumed(archive)
