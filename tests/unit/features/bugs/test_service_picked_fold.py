"""``BugState.picked_by`` — the fold half of the ``picked`` event (v0.4.3 T-043-18/FR14).

Intent: CONTRACT — v0.4.3 A14.1, A14.2 (fold half); I1, I2, I5, I6 (fold half). The
core-model coherence invariants (I1-I4, I7-I9) are covered in
``tests/unit/core/models/test_bugs_picked_event.py`` — this file is the
``BugService._fold``/``BugState`` contract only: what ``status()`` reports once a
``picked`` event has folded through.

Size: SMALL — pure in-memory fold over a fake store, no real filesystem I/O.
"""

from __future__ import annotations

from dadaia_workspace.core.models.bugs import BugEvent
from dadaia_workspace.core.protocols.bug_store import BugStore
from dadaia_workspace.features.bugs.service import BugService


class _FakeBugStore:
    """In-memory :class:`BugStore` — append-only, iteration order preserved."""

    def __init__(self, events: list[BugEvent] | None = None) -> None:
        self._events = list(events or [])

    def iter_events(self) -> list[BugEvent]:
        return list(self._events)

    def append_event(self, event: BugEvent) -> object:
        self._events.append(event)
        return event


def _reported(bug_id: str, *, title: str = "t") -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="reported",
        ts="2026-08-17T10:00:00Z",
        reported_by="product-engineer",
        title=title,
        severity="MEDIUM",
        surface="s",
        component="c",
        context="dadaia-workspace",
        tags=(),
        symptom="x",
        repro="y",
        expected="z",
        notes="n",
    )


def _picked(bug_id: str, *, actor: str, release: str = "v0.4.3") -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="picked",
        ts="2026-08-17T10:05:00Z",
        reported_by=actor,
        release=release,
    )


def _resolved(bug_id: str) -> BugEvent:
    return BugEvent(
        bug_id=bug_id,
        event="resolved",
        ts="2026-08-17T10:10:00Z",
        reported_by="software-engineer",
        release="v0.4.3",
        evidence="repro + fix + green suite result, over 20 chars",
    )


def _service(events: list[BugEvent]) -> BugService:
    store: BugStore = _FakeBugStore(events)  # type: ignore[assignment]
    return BugService(store)


def test_i1_pick_carries_the_actor_in_picked_by() -> None:
    events = [_reported("b1"), _picked("b1", actor="software-engineer")]
    states = _service(events).status(include_closed=True)

    assert len(states) == 1
    assert states[0].picked_by == ("software-engineer",)


def test_i2_repeated_picks_accumulate_in_order_including_duplicates() -> None:
    """A repeated pick is the sanctioned race outcome — SURFACED, not deduplicated."""
    events = [
        _reported("b1"),
        _picked("b1", actor="agent-a"),
        _picked("b1", actor="agent-b"),
        _picked("b1", actor="agent-a"),  # same actor picks again — still visible
    ]
    states = _service(events).status(include_closed=True)

    assert states[0].picked_by == ("agent-a", "agent-b", "agent-a")


def test_i6_a_picked_only_tail_leaves_status_open() -> None:
    events = [_reported("b1"), _picked("b1", actor="agent-a")]
    states = _service(events).status(include_closed=False)

    assert len(states) == 1  # visible in the OPEN-only default view
    assert states[0].status == "open"


def test_i5_a_reopen_clears_stale_picked_by_from_the_reopened_stream() -> None:
    """No stale pre-terminal pick leaks into the reopened stream."""
    events = [
        _reported("b1"),
        _picked("b1", actor="agent-a"),
        _resolved("b1"),
        _reported("b1"),  # reopen
    ]
    states = _service(events).status(include_closed=True)

    assert states[0].status == "open"
    assert states[0].picked_by == (), "a reopen must clear the prior stream's picked_by"


def test_i5_post_reopen_pick_accumulates_fresh() -> None:
    events = [
        _reported("b1"),
        _picked("b1", actor="agent-a"),
        _resolved("b1"),
        _reported("b1"),  # reopen — clears picked_by
        _picked("b1", actor="agent-b"),  # fresh pick on the reopened stream
    ]
    states = _service(events).status(include_closed=True)

    assert states[0].picked_by == ("agent-b",)


def test_picked_never_changes_status_from_terminal() -> None:
    """A pick after a terminal event is incoherent at the coherence-fold layer
    (core.models.bugs.advance_coherence — covered elsewhere); the STATE fold itself
    (BugService._fold, used for status()/stats() reporting) is tolerant of whatever
    history is already on disk and simply carries the picked_by forward without ever
    reverting a terminal status."""
    events = [_reported("b1"), _resolved("b1"), _picked("b1", actor="agent-a")]
    states = _service(events).status(include_closed=True)

    assert states[0].status == "resolved"
    assert states[0].picked_by == ("agent-a",)


def test_bug_with_no_picked_events_has_empty_picked_by() -> None:
    """A14.4: a ledger with zero picked events folds identically to today."""
    events = [_reported("b1")]
    states = _service(events).status(include_closed=True)

    assert states[0].picked_by == ()
