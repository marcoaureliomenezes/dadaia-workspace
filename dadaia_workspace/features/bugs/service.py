"""Bug-event service — fold event streams into current state and aggregates (v0.1.46 AC-1).

Pure fold over the append-only JSONL store. ``append_event`` redacts ``notes`` before
handing the event to the store; ``status`` and ``stats`` reduce the event stream the same
way the doctor coherence check does — event sourcing, one reduce.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace

# The store is an infrastructure concern; the service holds it behind the ``BugStore``
# core Protocol (DI seam) — the concrete ``JsonlBugStore`` is injected at the CLI
# composition root, so features never imports infrastructure (features-no-infrastructure).
from dadaia_workspace.core.exceptions import DadaiaError
from dadaia_workspace.core.models.bugs import TERMINAL_EVENTS, BugEvent, BugEventKind
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


@dataclass(frozen=True)
class BugStats:
    """Aggregate counts across all folded bugs."""

    total: int
    by_status: dict[str, int] = field(default_factory=dict)
    by_severity: dict[str, int] = field(default_factory=dict)


class BugService:
    """Append + fold operations over an append-only :class:`BugStore`."""

    def __init__(self, store: BugStore) -> None:
        self._store = store

    def append_event(self, event: BugEvent) -> object:
        """Redact ``notes`` then append the event (append-only, never rewrites history).

        A TERMINAL event over a ``bug_id`` that was never ``reported`` is refused. Bug
        ``r19-bugs-resolved-event-accepted-without-prior-reported``: the ledger accepted a
        stray ``resolved`` and folded it into the resolved count, so a bug nobody ever
        opened could be closed. The ledger exists to be the evidence trail; an entry with
        no opening event is the one shape that cannot be evidence of anything.

        The operator harm is sharper than the accounting: a mistyped ``--bug-id`` on a
        close silently mints a PHANTOM resolved bug instead of saying the id is unknown,
        so the real bug stays open and the typo looks like progress.
        """
        if event.event in TERMINAL_EVENTS:
            known = {state.bug_id for state in self._fold().values()}
            if event.bug_id not in known:
                # Bug r24-bugs-terminal-refusal-blames-a-typo-in-the-wrong-context: this
                # used to assert flatly that no `reported` event opened the bug and send
                # the operator hunting for a typo. Streams are PER CONTEXT, so the far
                # likelier cause — the id was opened in a different one, because
                # `--context` was omitted and a foreign context resolved — went unsaid.
                # Naming the store that was actually read is what makes the refusal true.
                location = getattr(self._store, "root", None)
                where = f" in {location}" if location is not None else " in this context"
                raise DadaiaError(
                    f"cannot append {event.event!r} for {event.bug_id!r}: no `reported` "
                    f"event opened that bug{where}. A stream opens with `reported`. If "
                    "the bug was opened elsewhere, pass the `--context` it belongs to — "
                    "bug streams are per context, and an id opened in another context is "
                    "not visible from this one. Otherwise check the id (`dadaia bugs "
                    "status` lists the open ones), or append its `reported` event first."
                )
        return self._store.append_event(event.redact())

    def _fold(self) -> dict[str, BugState]:
        """Reduce the event stream to current per-``bug_id`` state.

        ``reported`` (re)opens with metadata; a terminal event sets the status to that
        terminal kind; ``archived`` is a non-terminal annotation and never changes state.
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
