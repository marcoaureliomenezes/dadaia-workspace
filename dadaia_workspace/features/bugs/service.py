"""Bug-event service — fold event streams into current state and aggregates (v0.1.46 AC-1).

Pure fold over the append-only JSONL store. ``append_event`` redacts ``notes`` before
handing the event to the store; ``status`` and ``stats`` reduce the event stream the same
way the doctor coherence check does — event sourcing, one reduce.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace

from dadaia_workspace.core.models.bugs import TERMINAL_EVENTS, BugEvent, BugEventKind

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

    def append_event(self, event: BugEvent) -> None:
        """Redact ``notes`` then append the event (append-only, never rewrites history)."""
        self._store.append_event(event.redact())

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
