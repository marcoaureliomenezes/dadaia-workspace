"""The non-terminal ``picked`` bug-ledger event (v0.4.3 T-043-18/FR14).

Intent: CONTRACT — v0.4.3 A14.1-A14.4, invariants I1-I9 (software-architect ruling,
handoff 2026-08-17T161500Z-software-architect-v0.4.3-fr13-fr14, HIGH finding #3).

``picked`` is an OBSERVABLE RESERVATION MARKER, never a lease (NO-LOCKS DOCTRINE): it
grants nothing, expires never, blocks nothing. A repeated pick on the SAME open stream
is allowed and surfaced (the sanctioned race outcome — two visible picks, mirroring
advisory presence), never refused. The only refusals are STREAM-INTEGRITY refusals
(pick-after-terminal, pick-before-reported) — never concurrency refusals.

Size: SMALL — pure-function unit tests over ``advance_coherence`` and ``BugEvent``/
``BugEventKind``, no I/O. The fold (``BugService``/``BugState.picked_by``) and the CLI
wiring get their own dedicated test coverage in ``tests/unit/features/bugs/`` and
``tests/integration/cli/`` respectively — this file is the core-model contract only.
"""

from __future__ import annotations

from dadaia_workspace.core.models.bugs import (
    TERMINAL_EVENTS,
    BugCoherenceRecord,
    BugEvent,
    BugEventKind,
    advance_coherence,
    diagnose_bug_coherence_history,
)


def test_picked_event_kind_exists_and_is_never_terminal() -> None:
    """The schema/model half of A14.4: ``picked`` is a real event kind, deliberately
    NOT in :data:`TERMINAL_EVENTS` (I6 — a picked-only stream stays 'open')."""
    assert BugEventKind.PICKED == "picked"
    assert BugEventKind.PICKED.value not in TERMINAL_EVENTS


def test_picked_event_is_terminal_property_is_false() -> None:
    event = BugEvent(
        bug_id="b1",
        event=BugEventKind.PICKED.value,
        ts="2026-08-17T00:00:00Z",
        reported_by="software-engineer",
        release="v0.4.3",
    )
    assert event.is_terminal is False


# ── I1 — pick on an open stream is accepted, picked_by carries the actor (A14.1) ─────


def test_i1_pick_on_open_stream_is_coherent() -> None:
    seen: set[str] = set()
    terminated: set[str] = set()
    assert advance_coherence("b1", "reported", seen, terminated) is None

    assert advance_coherence("b1", "picked", seen, terminated) is None


# ── I2 — a second pick on the SAME open stream is accepted and visible (A14.2) ───────


def test_i2_repeated_pick_on_open_stream_is_never_refused() -> None:
    """NO-LOCKS: a repeated pick is the sanctioned race outcome — allowed, not blocked."""
    seen: set[str] = set()
    terminated: set[str] = set()
    advance_coherence("b1", "reported", seen, terminated)

    assert advance_coherence("b1", "picked", seen, terminated) is None
    assert advance_coherence("b1", "picked", seen, terminated) is None
    assert advance_coherence("b1", "picked", seen, terminated) is None


# ── I3 — a pick AFTER a terminal event is refused, and diagnosed with the SAME clause
#         (A14.3 + the v0.1.72 same-fold law: the enforced gate and the diagnostic gate
#         can never diverge) ─────────────────────────────────────────────────────────


def test_i3_pick_after_terminal_is_refused_by_the_append_fold() -> None:
    seen: set[str] = set()
    terminated: set[str] = set()
    advance_coherence("b1", "reported", seen, terminated)
    advance_coherence("b1", "resolved", seen, terminated)

    clause = advance_coherence("b1", "picked", seen, terminated)

    assert clause is not None
    assert "b1" in clause
    assert "picked" in clause


def test_i3_pick_after_terminal_is_diagnosed_with_the_same_clause_the_append_fold_uses() -> None:
    """The v0.1.72 law: the diagnostic gate (``diagnose_bug_coherence_history``) and
    the enforced gate (``advance_coherence``, folded by ``BugService.append_event``)
    must never diverge — the SAME clause text either way."""
    expected_clause = advance_coherence("b1", "picked", {"b1"}, {"b1"})

    records = [
        BugCoherenceRecord(bug_id="b1", event="reported", position=1),
        BugCoherenceRecord(bug_id="b1", event="resolved", position=2),
        BugCoherenceRecord(bug_id="b1", event="picked", position=3),
    ]
    violations = diagnose_bug_coherence_history(records)

    assert len(violations) == 1
    assert violations[0].clause == expected_clause
    assert violations[0].event == "picked"
    assert violations[0].position == 3


# ── I4 — a pick BEFORE any 'reported' is refused/diagnosed ───────────────────────────


def test_i4_pick_on_an_unopened_stream_is_refused() -> None:
    seen: set[str] = set()
    terminated: set[str] = set()

    clause = advance_coherence("never-reported", "picked", seen, terminated)

    assert clause is not None
    assert "never-reported" in clause


def test_i4_pick_on_an_unopened_stream_is_diagnosed() -> None:
    records = [BugCoherenceRecord(bug_id="ghost", event="picked", position=1)]

    violations = diagnose_bug_coherence_history(records)

    assert len(violations) == 1
    assert violations[0].bug_id == "ghost"
    assert violations[0].event == "picked"


# ── I5 — a reopen ('reported') clears BOTH terminal state and any pre-terminal pick
#         residue — no stale pre-terminal pick leaks into the reopened stream ────────


def test_i5_reopen_clears_terminal_state_so_a_post_reopen_pick_is_coherent() -> None:
    seen: set[str] = set()
    terminated: set[str] = set()
    advance_coherence("b1", "reported", seen, terminated)
    advance_coherence("b1", "picked", seen, terminated)
    advance_coherence("b1", "resolved", seen, terminated)

    advance_coherence("b1", "reported", seen, terminated)  # reopen
    clause = advance_coherence("b1", "picked", seen, terminated)  # post-reopen pick

    assert clause is None, "a pick after a legitimate reopen must be coherent"


def test_i5_reopen_healing_covers_a_pick_after_terminal_violation_too() -> None:
    """The SAME append-only compensation vocabulary (a later 'reported') that heals
    every other violation class also heals a pick-after-terminal violation — no
    special case (this IS I7, exercised here at the reopen level)."""
    records = [
        BugCoherenceRecord(bug_id="b1", event="reported", position=1),
        BugCoherenceRecord(bug_id="b1", event="resolved", position=2),
        BugCoherenceRecord(bug_id="b1", event="picked", position=3),  # violation
        BugCoherenceRecord(bug_id="b1", event="reported", position=4),  # heals it
    ]
    assert diagnose_bug_coherence_history(records) == []


# ── I6 — a picked-only tail leaves status 'open' — picked is never terminal ──────────


def test_i6_picked_only_tail_never_advances_the_terminated_set() -> None:
    seen: set[str] = set()
    terminated: set[str] = set()
    advance_coherence("b1", "reported", seen, terminated)
    advance_coherence("b1", "picked", seen, terminated)
    advance_coherence("b1", "picked", seen, terminated)

    assert "b1" not in terminated


# ── I7 — healing uniformity: a historical pick-after-terminal violation heals under a
#         later 'reported' exactly like every OTHER violation class, with NO special
#         case in diagnose_bug_coherence_history (the function itself needs zero
#         changes — this is a property of advance_coherence + the existing generic
#         healing rule) ──────────────────────────────────────────────────────────────


def test_i7_pick_after_terminal_healing_is_identical_in_shape_to_a_second_terminal_healing() -> (
    None
):
    """Same healing SHAPE (violation, then a later 'reported' compensates it) proven
    side-by-side for a pick-after-terminal violation and an ordinary second-terminal
    violation — one generic rule, not two."""
    pick_after_terminal = [
        BugCoherenceRecord(bug_id="pick-bug", event="reported", position=1),
        BugCoherenceRecord(bug_id="pick-bug", event="resolved", position=2),
        BugCoherenceRecord(bug_id="pick-bug", event="picked", position=3),
        BugCoherenceRecord(bug_id="pick-bug", event="reported", position=4),
    ]
    second_terminal = [
        BugCoherenceRecord(bug_id="term-bug", event="reported", position=1),
        BugCoherenceRecord(bug_id="term-bug", event="resolved", position=2),
        BugCoherenceRecord(bug_id="term-bug", event="rejected", position=3),
        BugCoherenceRecord(bug_id="term-bug", event="reported", position=4),
    ]
    assert diagnose_bug_coherence_history(pick_after_terminal) == []
    assert diagnose_bug_coherence_history(second_terminal) == []


def test_i7_a_fresh_pick_after_terminal_violation_after_the_healing_reopen_still_errors() -> None:
    """Mirrors ``test_healed_then_reviolated_stream_errors_only_on_the_new_row``: a
    reopen heals the earlier violation, but a FRESH pick-after-terminal violation after
    that reopen is a NEW, still-unhealed violation and must still surface."""
    records = [
        BugCoherenceRecord(bug_id="b1", event="reported", position=1),
        BugCoherenceRecord(bug_id="b1", event="resolved", position=2),
        BugCoherenceRecord(bug_id="b1", event="picked", position=3),  # heals via position 4
        BugCoherenceRecord(bug_id="b1", event="reported", position=4),
        BugCoherenceRecord(bug_id="b1", event="deferred", position=5),
        BugCoherenceRecord(bug_id="b1", event="picked", position=6),  # NEW violation
    ]

    violations = diagnose_bug_coherence_history(records)

    assert [(v.bug_id, v.position) for v in violations] == [("b1", 6)]


# ── I8 — a ledger with zero picked events folds identically to today (A14.4) ─────────


def test_i8_a_history_with_no_picked_events_is_completely_unaffected() -> None:
    records = [
        BugCoherenceRecord(bug_id="a", event="reported", position=1),
        BugCoherenceRecord(bug_id="a", event="resolved", position=2),
        BugCoherenceRecord(bug_id="b", event="reported", position=3),
    ]
    assert diagnose_bug_coherence_history(records) == []

    seen: set[str] = set()
    terminated: set[str] = set()
    assert advance_coherence("a", "reported", seen, terminated) is None
    assert advance_coherence("a", "resolved", seen, terminated) is None
    assert seen == {"a"}
    assert terminated == {"a"}


# ── I9 — picked passes through redact() with structured fields untouched and free-text
#         fields still scrubbed ──────────────────────────────────────────────────────


def test_i9_picked_event_redaction_scrubs_free_text_leaves_structured_fields_alone() -> None:
    event = BugEvent(
        bug_id="b1",
        event=BugEventKind.PICKED.value,
        ts="2026-08-17T00:00:00Z",
        reported_by="software-engineer",
        release="v0.4.3",
        # Both literals below are deliberately the DOCUMENTED placeholder/example
        # forms the repo's own privacy-baseline self-scan already carves out
        # (/home/user is the home-abs-path placeholder; 192.0.2.3 is the RFC 5737
        # TEST-NET-1 documentation range) — real IP/path SHAPES, so they still
        # exercise BugEvent.redact()'s own unconditional _IPV4_RE/_POSIX_HOME_RE
        # masking (that regex has no exclusion logic at all), without tripping the
        # baseline's SEPARATE, unrelated self-scan check on this test's own source.
        notes="picked while investigating /home/user/workspace and 192.0.2.3",
    )

    redacted = event.redact()

    # Structured fields untouched.
    assert redacted.bug_id == "b1"
    assert redacted.event == "picked"
    assert redacted.reported_by == "software-engineer"
    assert redacted.release == "v0.4.3"
    # Free-text field still scrubbed exactly as every other event kind.
    assert "/home/user/workspace" not in redacted.notes
    assert "[REDACTED]" in redacted.notes
    assert "192.0.2.3" not in redacted.notes


def test_i9_redaction_scrubs_release_and_reason_fields() -> None:
    """T-043-23 security-review rework (FR14 LOW, CWE-532): ``release`` (grammar-
    described but only CLI-checked-non-empty) and ``reason`` (the schema's own
    description: "the disposition rationale" -- free prose) previously passed through
    ``redact()`` UNTOUCHED, unlike every other prose field. Both DOCUMENTED
    placeholder forms below (same technique as I9 above -- already carved out by the
    baseline self-scan) still exercise the real _IPV4_RE/_POSIX_HOME_RE
    substitution."""
    event = BugEvent(
        bug_id="b1",
        event=BugEventKind.RESOLVED.value,
        ts="2026-08-17T00:00:00Z",
        reported_by="software-engineer",
        release="picked at /home/user/workspace",
        reason="disposition decided while reaching 192.0.2.3",
    )

    redacted = event.redact()

    assert "/home/user/workspace" not in (redacted.release or "")
    assert "[REDACTED]" in (redacted.release or "")
    assert "192.0.2.3" not in (redacted.reason or "")
    assert "[REDACTED-IP]" in (redacted.reason or "")


def test_i9_picked_event_round_trips_through_to_dict_and_from_dict() -> None:
    event = BugEvent(
        bug_id="b1",
        event=BugEventKind.PICKED.value,
        ts="2026-08-17T00:00:00Z",
        reported_by="software-engineer",
        release="v0.4.3",
    )
    payload = event.to_dict()

    assert payload["event"] == "picked"
    assert payload["release"] == "v0.4.3"

    restored = BugEvent.from_dict(payload)
    assert restored == event
