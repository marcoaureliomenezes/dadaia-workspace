"""A7.4 (SPEC v0.4.5 FR7, T-045-20) + v0.5.0 T-050-08/T-050-10 (FR2/FR3, A2.5/A3.7),
amended by the S1 FR23 firing (A1,
`specs/releases/0.5.0/reviews/S1-FR23-firing.md`): the whole LIVE
``specs/bugs/BUGS.jsonl`` ledger still parses through the ONE production read seam
(``JsonlRecordStore.iter_records()``, injected via ``container.build_bug_record_store``
— the SAME seam ``BugService``/``dadaia bugs status``/``bugs stats`` use), and no
historical record is rewritten.

Intent: CONTRACT — SPEC v0.4.5 FR7/A7.4, carried forward at v0.5.0 T-050-08 (the store
this file exercised, ``JsonlBugStore``, is deleted), T-050-10/A3.7 (FR3 physically
migrated ``bugs.jsonl`` -> ``BUGS.jsonl``, one native v6 :class:`BugRecord` line per
bug id), and the S1 FR23 firing A1 (the deletable ``migrate_v5.read_ledger`` this file
used to exercise is gone — the permanent record store is the one seam left standing).
Reads the real on-disk ledger this repository ships (never a ``tmp_path`` fixture),
and proves every non-blank physical line still contributes to one
:class:`~dadaia_workspace.core.models.bugs.BugRecord` (zero WARN-level "skipping ..."
log records — A3.7's "skipped: 0").

Size: SMALL (directory-tiered ``integration`` — real file I/O over an on-disk file this
repo already tracks, no subprocess/network).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from dadaia_workspace import container

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SPECS_DIR = _REPO_ROOT / "specs"
_LEDGER = _SPECS_DIR / "bugs" / "BUGS.jsonl"


def test_live_ledger_exists_and_is_non_empty() -> None:
    """Sanity: the sentinel below is meaningless if the ledger this repo tracks moved."""
    assert _LEDGER.is_file(), f"expected the live ledger at {_LEDGER}"
    assert _LEDGER.stat().st_size > 0


def test_live_ledger_fully_parses_with_no_skipped_lines(caplog: pytest.LogCaptureFixture) -> None:
    """A7.4: every non-blank physical line in the live ledger parses as ONE native v6
    :class:`~dadaia_workspace.core.models.bugs.BugRecord` — zero "skipping ..." WARN
    records, proving the store's reader-split (``split("\\n")`` instead of
    ``str.splitlines()``) does not newly break, or newly "fix" by silent
    reinterpretation, a single historical row."""
    non_blank_lines = [
        line for line in _LEDGER.read_text(encoding="utf-8").split("\n") if line.strip()
    ]

    store = container.build_bug_record_store(_SPECS_DIR)
    with caplog.at_level(
        logging.WARNING, logger="dadaia_workspace.infrastructure.jsonl_record_store"
    ):
        records = list(store.iter_records())

    skip_warnings = [
        r
        for r in caplog.records
        if "malformed" in r.getMessage()
        or "invalid" in r.getMessage()
        or "skipping" in r.getMessage()
    ]
    assert skip_warnings == [], (
        f"live ledger rows were skipped: {[r.getMessage() for r in skip_warnings]}"
    )
    assert len(records) > 0, "the live ledger folded to zero records"
    assert len(non_blank_lines) == len(records), (
        "one physical line per native v6 record — a mismatch means either a skipped "
        "line or a stray v5-shaped line the store's tolerant parser silently dropped"
    )


def test_live_ledger_content_is_byte_identical_after_a_read(tmp_path: Path) -> None:
    """No historical record is rewritten (A7.4): reading through the production seam
    never mutates the file — compare a snapshot copy against a fresh read of the real
    path, byte for byte."""
    before = _LEDGER.read_bytes()
    store = container.build_bug_record_store(_SPECS_DIR)
    list(store.iter_records())
    after = _LEDGER.read_bytes()
    assert before == after
