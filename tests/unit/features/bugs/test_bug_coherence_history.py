"""Unit tests for the whole-history bug-coherence diagnosis (v0.5.0 T-50-09 / FR2).

``diagnose_bug_coherence_history`` is the ONE place the "healing rule" lives: a
coherence violation (SPEC-DOC-033's per-event fold, :func:`advance_coherence`) is
reported by the doctor only while no LATER ``reported`` event exists for the same
``bug_id`` — the store's own append-only compensation vocabulary. Enforcement
(``BugService.append_event``, covered by ``test_append_coherence.py``) is untouched and
stays green; this file covers the DIAGNOSIS half only.
"""

from __future__ import annotations

from dadaia_workspace.core.models.bugs import (
    BugCoherenceRecord,
    BugCoherenceViolation,
    advance_coherence,
    diagnose_bug_coherence_history,
)


def _record(bug_id: str, event: str, position: object) -> BugCoherenceRecord[object]:
    return BugCoherenceRecord(bug_id=bug_id, event=event, position=position)


def test_empty_history_has_no_violations() -> None:
    assert diagnose_bug_coherence_history([]) == []


def test_coherent_history_has_no_violations() -> None:
    records = [
        _record("bug-a", "reported", ("f1.jsonl", 1)),
        _record("bug-a", "resolved", ("f1.jsonl", 2)),
    ]
    assert diagnose_bug_coherence_history(records) == []


def test_later_reported_heals_the_violation_row() -> None:
    """A violation row followed by a LATER `reported` for the same bug_id is healed —
    the diagnosis reports NOTHING for it."""
    records = [
        _record("ghost", "reported", ("f1.jsonl", 1)),
        _record("ghost", "resolved", ("f1.jsonl", 2)),
        _record("ghost", "resolved", ("f1.jsonl", 3)),  # second terminal -> violation
        _record("ghost", "reported", ("f1.jsonl", 4)),  # compensation: heals line 3
    ]
    assert diagnose_bug_coherence_history(records) == []


def test_uncompensated_violation_stays_unhealed_with_todays_clause() -> None:
    """A violation with no later `reported` anywhere after it still surfaces — the
    healing rule heals history, it never disables the check — and its clause text
    matches `advance_coherence` exactly (one authority, no drift)."""
    records = [
        _record("orphan", "resolved", ("f1.jsonl", 7)),
    ]
    expected_clause = advance_coherence("orphan", "resolved", set(), set())

    violations = diagnose_bug_coherence_history(records)

    assert len(violations) == 1
    violation = violations[0]
    assert violation == BugCoherenceViolation(
        bug_id="orphan",
        event="resolved",
        clause=expected_clause,
        position=("f1.jsonl", 7),
    )


def test_healed_then_reviolated_stream_errors_only_on_the_new_row() -> None:
    """A `reported` heals an earlier violation; a fresh second-terminal AFTER that
    healing `reported` is a NEW, still-unhealed violation and must still ERROR."""
    records = [
        _record("bug-x", "reported", ("f1.jsonl", 1)),
        _record("bug-x", "resolved", ("f1.jsonl", 2)),
        _record("bug-x", "resolved", ("f1.jsonl", 3)),  # V1: second terminal
        _record("bug-x", "reported", ("f1.jsonl", 4)),  # heals V1 (reopen)
        _record("bug-x", "resolved", ("f1.jsonl", 5)),
        _record("bug-x", "resolved", ("f1.jsonl", 6)),  # V2: NEW second terminal
    ]

    violations = diagnose_bug_coherence_history(records)

    assert [(v.bug_id, v.position) for v in violations] == [("bug-x", ("f1.jsonl", 6))]


def test_terminal_without_reported_healed_by_documented_compensation() -> None:
    """The exact FR2 compensation shape: a historical terminal-without-reported row,
    healed by a later (`reported`, `resolved`) pair for the same bug_id — the
    resolved-re-affirmation never re-triggers the rule because the reopened stream now
    carries a `reported`."""
    records = [
        _record("closure-catalog-references-missing-memory-atom", "resolved", ("bugs.jsonl", 719)),
        _record("closure-catalog-references-missing-memory-atom", "reported", ("bugs.jsonl", 900)),
        _record("closure-catalog-references-missing-memory-atom", "resolved", ("bugs.jsonl", 901)),
    ]
    assert diagnose_bug_coherence_history(records) == []


def test_unrelated_bug_ids_do_not_heal_each_other() -> None:
    """A `reported` for one bug_id never heals a violation belonging to a different
    bug_id."""
    records = [
        _record("orphan-a", "resolved", ("f1.jsonl", 1)),  # violation, stays unhealed
        _record("orphan-b", "reported", ("f1.jsonl", 2)),  # unrelated bug_id
    ]
    violations = diagnose_bug_coherence_history(records)
    assert [v.bug_id for v in violations] == ["orphan-a"]


def test_violations_preserve_input_order() -> None:
    records = [
        _record("bug-a", "resolved", ("f1.jsonl", 1)),  # unhealed violation #1
        _record("bug-b", "resolved", ("f1.jsonl", 2)),  # unhealed violation #2
    ]
    violations = diagnose_bug_coherence_history(records)
    assert [v.bug_id for v in violations] == ["bug-a", "bug-b"]
