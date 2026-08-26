"""A7.4 (SPEC v0.4.5 FR7, T-045-20): the whole LIVE ``specs/bugs/bugs.jsonl`` ledger
still parses after the ``str.splitlines()`` -> ``str.split("\\n")`` reader fix, and no
historical event is rewritten.

Intent: CONTRACT — SPEC v0.4.5 FR7/A7.4. Reads the real on-disk ledger this repository
ships (never a ``tmp_path`` fixture) through the same :class:`JsonlBugStore` production
seam ``dadaia bugs status``/``bugs stats`` use, and proves every non-blank physical line
still yields exactly one folded event (zero WARN-level "skipping ... bug-event ..." log
records) — the read-side fix changed HOW lines are split, never what a well-formed
historical record means.

Size: SMALL (directory-tiered ``integration`` — real file I/O over an on-disk file this
repo already tracks, no subprocess/network).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.jsonl_bug_store import JsonlBugStore

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LEDGER = _REPO_ROOT / "specs" / "bugs" / "bugs.jsonl"


def test_live_ledger_exists_and_is_non_empty() -> None:
    """Sanity: the sentinel below is meaningless if the ledger this repo tracks moved."""
    assert _LEDGER.is_file(), f"expected the live ledger at {_LEDGER}"
    assert _LEDGER.stat().st_size > 0


def test_live_ledger_fully_parses_with_no_skipped_lines(caplog: pytest.LogCaptureFixture) -> None:
    """A7.4: every non-blank physical line in the live ledger folds into exactly one
    :class:`BugEvent` — zero "skipping ... bug-event ..." WARN records, proving the
    reader-split change (``split("\\n")`` instead of ``str.splitlines()``) does not
    newly break, or newly "fix" by silent reinterpretation, a single historical row."""
    non_blank_lines = [
        line for line in _LEDGER.read_text(encoding="utf-8").split("\n") if line.strip()
    ]

    with caplog.at_level(logging.WARNING, logger="dadaia_workspace.infrastructure.jsonl_bug_store"):
        events = list(JsonlBugStore(_LEDGER.parent).iter_events())

    skip_warnings = [
        r for r in caplog.records if "bug-event" in r.getMessage() or "bug log" in r.getMessage()
    ]
    assert skip_warnings == [], (
        f"live ledger rows were skipped: {[r.getMessage() for r in skip_warnings]}"
    )
    assert len(events) == len(non_blank_lines)


def test_live_ledger_content_is_byte_identical_after_a_read(tmp_path: Path) -> None:
    """No historical event is rewritten (A7.4): reading through the production seam
    never mutates the file — compare a snapshot copy against a fresh read of the real
    path, byte for byte."""
    before = _LEDGER.read_bytes()
    list(JsonlBugStore(_LEDGER.parent).iter_events())
    after = _LEDGER.read_bytes()
    assert before == after
