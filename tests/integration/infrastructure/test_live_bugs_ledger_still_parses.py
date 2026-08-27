"""A7.4 (SPEC v0.4.5 FR7, T-045-20) + v0.5.0 T-050-08/T-050-10 (FR2/FR3, A2.5/A3.7):
the whole LIVE ``specs/bugs/BUGS.jsonl`` ledger still parses through
``features.bugs.migrate_v5.read_ledger``, and no historical record is rewritten.

Intent: CONTRACT — SPEC v0.4.5 FR7/A7.4, carried forward at v0.5.0 T-050-08 (the store
this file exercised, ``JsonlBugStore``, is deleted) and T-050-10/A3.7 (FR3 physically
migrated ``bugs.jsonl`` -> ``BUGS.jsonl``, one native v6 :class:`BugRecord` line per
bug id — ``read_ledger`` keeps its v5-tolerant path so a foreign/pre-migration write
never crashes the read, but every LIVE row is now native v6 shape). Reads the real
on-disk ledger this repository ships (never a ``tmp_path`` fixture) through the SAME
production seam ``dadaia bugs status``/``bugs stats`` use, and proves every non-blank
physical line still contributes to a folded
:class:`~dadaia_workspace.core.models.bugs.BugRecord` (zero WARN-level "skipping ..."
log records — A3.7's "skipped: 0").

Size: SMALL (directory-tiered ``integration`` — real file I/O over an on-disk file this
repo already tracks, no subprocess/network).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from dadaia_workspace.features.bugs import migrate_v5

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LEDGER = _REPO_ROOT / "specs" / "bugs" / "BUGS.jsonl"


def test_live_ledger_exists_and_is_non_empty() -> None:
    """Sanity: the sentinel below is meaningless if the ledger this repo tracks moved."""
    assert _LEDGER.is_file(), f"expected the live ledger at {_LEDGER}"
    assert _LEDGER.stat().st_size > 0


def test_live_ledger_fully_parses_with_no_skipped_lines(caplog: pytest.LogCaptureFixture) -> None:
    """A7.4: every non-blank physical line in the live ledger is EITHER folded into a
    :class:`~dadaia_workspace.core.models.bugs.BugRecord` (v5 event lines, grouped by
    ``bug_id``) OR parsed directly as one (a native v6 line) — zero "skipping ..." WARN
    records, proving the reader-split change (``split("\\n")`` instead of
    ``str.splitlines()``) does not newly break, or newly "fix" by silent
    reinterpretation, a single historical row."""
    non_blank_lines = [
        line for line in _LEDGER.read_text(encoding="utf-8").split("\n") if line.strip()
    ]

    with caplog.at_level(logging.WARNING, logger="dadaia_workspace.features.bugs.migrate_v5"):
        records = migrate_v5.read_ledger(_LEDGER)

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
    assert len(non_blank_lines) >= len(records), (
        "at least one physical line per record — a v5-folded record spans >=1 line"
    )


def test_live_ledger_content_is_byte_identical_after_a_read(tmp_path: Path) -> None:
    """No historical event is rewritten (A7.4): reading through the production seam
    never mutates the file — compare a snapshot copy against a fresh read of the real
    path, byte for byte."""
    before = _LEDGER.read_bytes()
    migrate_v5.read_ledger(_LEDGER)
    after = _LEDGER.read_bytes()
    assert before == after
