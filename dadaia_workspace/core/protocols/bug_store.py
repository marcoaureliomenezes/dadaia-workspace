"""Bug-event store port (v0.1.46 — features→infrastructure DI seam).

``BugService`` (features layer) folds an append-only bug-event stream but must not depend
on the concrete ``infrastructure.jsonl_bug_store.JsonlBugStore`` — the
``features-no-infrastructure`` import-linter contract forbids that edge. This Protocol is
the narrow port the service annotates against; the concrete ``JsonlBugStore`` satisfies it
structurally and is injected at the composition root (the ``dadaia bugs`` CLI).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from dadaia_workspace.core.models.bugs import BugEvent

__all__ = ["BugStore"]


class BugStore(Protocol):
    """Port for an append-only bug-event store."""

    def append_event(self, event: BugEvent) -> object:
        """Append one event to the stream (append-only, never rewrites history)."""

    def iter_events(self) -> Iterator[BugEvent]:
        """Yield every stored event in chronological order."""
