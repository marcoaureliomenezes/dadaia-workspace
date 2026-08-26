"""Bug-event service — fold event streams into current state and aggregates (v0.1.46 AC-1).

Pure fold over the append-only JSONL store. ``append_event`` redacts every free-text
field (IP/home-path, and — v0.4.5 FR6, T-045-19 — any injected operator denylist term)
before handing the event to the store; ``status`` and ``stats`` reduce the event stream
the same way the doctor coherence check does — event sourcing, one reduce.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field, replace

from dadaia_workspace.core.models.bugs import (
    TERMINAL_EVENTS,
    BugEvent,
    BugEventKind,
    advance_coherence,
)

# The store is an infrastructure concern; the service holds it behind the ``BugStore``
# core Protocol (DI seam) — the concrete ``JsonlBugStore`` is injected at the CLI
# composition root, so features never imports infrastructure (features-no-infrastructure).
from dadaia_workspace.core.protocols.bug_store import BugStore

__all__ = ["BugService", "BugState", "BugStats"]

#: Fold status for a bug whose stream has a `reported` but no terminal event yet.
_OPEN = "open"


@dataclass(frozen=True)
class BugState:
    """Current folded state of one ``bug_id``."""

    bug_id: str
    status: str
    severity: str | None = None
    title: str | None = None
    component: str | None = None
    #: v0.4.3 T-043-18/FR14 — every actor that has ``picked`` this bug's CURRENT
    #: (post-latest-``reported``) stream, in event order, duplicates preserved (a
    #: repeated pick is the sanctioned NO-LOCKS race outcome, surfaced not deduped).
    #: Reset to ``()`` on every ``reported`` (including a reopen) — never carries a
    #: prior stream's picks forward. Never terminal-gated: a picked-only tail leaves
    #: ``status`` at ``"open"`` (I6); a pick after a terminal event still folds here
    #: (the STATE fold is tolerant of on-disk history — see :meth:`_fold`'s docstring
    #: — coherence is `core.models.bugs.advance_coherence`'s job, enforced at append).
    picked_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class BugStats:
    """Aggregate counts across all folded bugs."""

    total: int
    by_status: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)


class BugService:
    """Append + fold operations over an append-only :class:`BugStore`."""

    def __init__(self, store: BugStore, denylist_terms: Sequence[tuple[str, str]] = ()) -> None:
        self._store = store
        # v0.4.5 FR6: the SAME operator-denylist source the push scan already refuses
        # on, DI'd in via the CLI/container seam (features-no-infrastructure).
        self._denylist_terms = tuple(denylist_terms)

    def append_event(self, event: BugEvent) -> object:
        """Refuse an incoherent event, then redact and append (never rewrites history).

        Coherence is judged by the SAME core fold the specs doctor diagnoses with
        (:func:`advance_coherence`) — before this, the one-terminal invariant lived only
        in the doctor, so the CLI happily wrote what the doctor then flagged (bugs
        bugs-append-accepts-second-terminal-event /
        bugs-append-allows-terminal-event-without-reported). History is folded
        tolerantly: an existing incoherent row is the doctor's finding, never an append
        blocker — only the NEW event is refused. Returns the store's append result.

        v0.4.5 FR6: also the enforced write-time redaction seam — ``event.redact()``
        carries ``self._denylist_terms`` so a leak the push scan would refuse is
        masked here first.
        """
        seen_reported: set[str] = set()
        terminated: set[str] = set()
        for prior in self._store.iter_events():
            advance_coherence(prior.bug_id, prior.event, seen_reported, terminated)
        violation = advance_coherence(event.bug_id, event.event, seen_reported, terminated)
        if violation is not None:
            raise ValueError(violation)
        return self._store.append_event(event.redact(self._denylist_terms))

    def _fold(self) -> dict[str, BugState]:
        """Reduce the event stream to current per-``bug_id`` state.

        ``reported`` (re)opens with metadata AND resets ``picked_by`` to ``()`` — a
        reopen never carries a prior stream's picks forward (v0.4.3 T-043-18/FR14,
        I5); a terminal event sets the status to that terminal kind; ``archived`` is a
        non-terminal annotation and never changes state; ``picked`` (v0.4.3 FR14)
        APPENDS the actor to ``picked_by`` (order and duplicates preserved — a
        repeated pick is the sanctioned NO-LOCKS race outcome, surfaced not deduped,
        I2) and never otherwise changes state — a picked-only tail leaves ``status``
        at ``"open"`` (I6). This fold is tolerant of on-disk history exactly like the
        terminal-event branch already is: coherence (pick-after-terminal,
        pick-before-reported) is enforced once, at append time, by
        ``core.models.bugs.advance_coherence`` — never re-checked here.
        """
        states: dict[str, BugState] = {}
        for event in self._store.iter_events():
            if event.event == BugEventKind.REPORTED.value:
                states[event.bug_id] = BugState(
                    bug_id=event.bug_id,
                    status=_OPEN,
                    severity=event.severity,
                    title=event.title,
                    component=event.component,
                )
            elif event.event in TERMINAL_EVENTS:
                current = states.get(event.bug_id) or BugState(event.bug_id, _OPEN)
                states[event.bug_id] = replace(current, status=event.event)
            elif event.event == BugEventKind.PICKED.value:
                current = states.get(event.bug_id) or BugState(event.bug_id, _OPEN)
                states[event.bug_id] = replace(
                    current, picked_by=(*current.picked_by, event.reported_by)
                )
            # BugEventKind.ARCHIVED: annotation only — leaves folded state untouched.
        return states

    def status(self, *, include_closed: bool = False) -> list[BugState]:
        """Return folded bug states, open-only by default, sorted by ``bug_id``."""
        folded = self._fold().values()
        selected = [s for s in folded if include_closed or s.status == _OPEN]
        return sorted(selected, key=lambda s: s.bug_id)

    def stats(self) -> BugStats:
        """Aggregate folded bugs by status and by severity."""
        folded = list(self._fold().values())
        by_status: Counter[str] = Counter(s.status for s in folded)
        by_severity: Counter[str] = Counter(s.severity for s in folded if s.severity is not None)
        return BugStats(
            total=len(folded),
            by_status=dict(by_status),
            by_severity=dict(by_severity),
        )
