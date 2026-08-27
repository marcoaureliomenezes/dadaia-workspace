"""Self-scan proving the ``consumed_backlog.json`` sidecar relocation is complete and
lossless (v0.5.0 T-050-13A, SPEC A5.5).

Intent: SCAFFOLD — T-050-13A — expires: 0.6.0 (retired at T-050-14, which deletes the root
``specs/_archive/`` source files this test's own live count depends on — the very next
task in the same release, sequenced by TASKS.md's ``T-050-13A`` precondition on
``T-050-14``)

FR6/T-050-14 deletes root ``specs/_archive/`` — the tree the 18 per-release
``consumed_backlog.json`` sidecars lived under. T-050-13A relocated their data into one
append-only file, ``specs/backlog/_archive/consumed_backlog_histo.jsonl``, **before**
that deletion, so BL-STALE's condition (a) does not go permanently quiet without ever
failing (FR13's "documented convention with no data behind it" shape).

This module drives the SAME production seam the real CLI/doctor path resolves
(``container.build_consumed_backlog_histo_store`` + ``ledger.read_consumed``) over this
repository's OWN ``specs/`` tree — a genuine self-scan, not a ``tmp_path`` fixture — and
counts the source files LIVE (``find``-equivalent glob), never a frozen ``18``, so the
assertion stays honest for as long as both sides of the migration still exist on disk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.features.backlog.ledger import read_consumed

pytestmark = pytest.mark.integration

#: This file lives at ``tests/integration/test_consumed_backlog_relocation.py`` — three
#: parents up is the repository root (mirrors ``tests/integration/test_repo_self_scan.
#: py``'s ``_REPO_ROOT`` resolution).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SPECS_DIR = _REPO_ROOT / "specs"
_ARCHIVE_ROOT = _SPECS_DIR / "_archive"
_HISTO_PATH = _SPECS_DIR / "backlog" / "_archive" / "consumed_backlog_histo.jsonl"


def _source_sidecar_count() -> int:
    """Every ``consumed_backlog.json`` still reachable under the root archive tree,
    counted live at test time (never a frozen literal)."""
    return len(list(_ARCHIVE_ROOT.glob("**/consumed_backlog.json")))


def test_relocated_record_count_matches_the_live_source_file_count() -> None:
    """A5.5: the relocated store carries exactly one record per surviving
    ``consumed_backlog.json`` sidecar — counted from the source files THIS SAME run
    finds, not a hardcoded 18."""
    source_count = _source_sidecar_count()
    assert source_count > 0, (
        "no consumed_backlog.json sidecars found under specs/_archive/ — either "
        "T-050-14 already ran (this SCAFFOLD test is due for deletion, see its module "
        "docstring) or the repo layout changed"
    )

    store = container.build_consumed_backlog_histo_store(_SPECS_DIR)
    assert store.path == _HISTO_PATH
    records = list(store.iter_records())
    assert len(records) == source_count, (
        f"expected {source_count} relocated records (one per live source sidecar), "
        f"found {len(records)}"
    )


def test_every_source_release_id_has_exactly_one_relocated_record() -> None:
    """Every source sidecar's release id (its own directory name, or nested under a
    ``consumed-backlog/`` subdirectory) resolves to exactly one relocated record — no
    release dropped, none duplicated (``RecordStore`` keys by ``id``, so a duplicate
    would have collapsed to one record and failed the count assertion above; this
    checks identity, not just cardinality)."""
    expected_ids: set[str] = set()
    for sidecar in _ARCHIVE_ROOT.glob("**/consumed_backlog.json"):
        parent = sidecar.parent
        release = parent.parent.name if parent.name == "consumed-backlog" else parent.name
        expected_ids.add(release)

    store = container.build_consumed_backlog_histo_store(_SPECS_DIR)
    actual_ids = {record.id for record in store.iter_records()}
    assert actual_ids == expected_ids


def test_bl_stale_condition_a_still_fires_through_the_real_relocated_store() -> None:
    """A5.5's fixture requirement, driven against the REAL relocated store (not a
    fake): a slug this repository's actual relocated ledger records as consumed still
    surfaces through :func:`read_consumed` — BL-STALE's data feed survived the
    relocation, proven over real data rather than only a synthetic fixture (the
    synthetic fixture equivalents live in ``tests/unit/test_backlog_ledger.py`` and
    ``tests/integration/test_backlog_doctor.py``)."""
    store = container.build_consumed_backlog_histo_store(_SPECS_DIR)
    consumed = read_consumed(store)
    assert consumed, "the relocated store yielded zero consumed slugs — read_consumed regressed"
    # Every slug real consumed_backlog.json content ever recorded is keyed and
    # non-None (an absent entry is skipped, never surfaced as a phantom key).
    for slug, anchors in consumed.items():
        assert isinstance(slug, str) and slug
        assert isinstance(anchors, set)
