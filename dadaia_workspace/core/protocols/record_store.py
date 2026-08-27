"""RecordStore Protocol — the generic "one record per id, appended once" port.

v0.5.0 FR2, AR-1 ruling answer (b) (`specs/releases/0.5.0/reviews/S1-AR1-ruling.md`
§2). Zero I/O (per the core ring rule): only the Protocol and its two typed failures
live here — the concrete adapter (``infrastructure.jsonl_record_store.JsonlRecordStore``)
is model-agnostic and imports no model (AR-1 (b)(iv)); each feature's own model
(``core.models.bugs.BugRecord`` today; ``findings``/``backlog`` later, per the same
ruling) supplies its own parse/serialise callables and receives its own store instance
from the container, so no module knows more than one record shape (A2.5, A13.4). This
is the port a future ``features/*/service.py`` depends on instead of the concrete
adapter — the same shape ``core/protocols/bug_store.py`` served the event-sourced store
before this release (mirrors ``core/protocols/git_object_reader.py``).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Protocol


class RecordNotFoundError(Exception):
    """Raised by :meth:`RecordStore.update` when no record with the given id exists."""

    def __init__(self, record_id: str) -> None:
        super().__init__(f"no record with id {record_id!r}")
        self.record_id = record_id


class StaleRecordWriteError(Exception):
    """Raised by :meth:`RecordStore.update` when the file changed since it was read.

    The ONE race semantics FR2 states: refuse-stale, never last-write-wins (A2.9). The
    caller re-reads and retries — nothing blocks and nothing is silently lost; the file
    is never left corrupt, because the rewrite is refused before it is ever attempted.
    """

    def __init__(self, record_id: str) -> None:
        super().__init__(
            f"record store changed since it was read while updating {record_id!r} — "
            "re-read and retry"
        )
        self.record_id = record_id


class RecordStore[T](Protocol):
    """Port for a JSONL "one record per id, appended once, rewritten in place" store."""

    @property
    def path(self) -> Path:
        """The ledger file this store is rooted at (v0.5.0 T-050-08 — the seam callers
        that still need file-level access — ``features.bugs.migrate_v5``'s v5 boundary
        adapter, ``BugService.archive``'s live-file rewrite — read the SAME path the
        store itself reads/writes, never a second, independently-resolved one)."""
        ...

    def append(self, record: T) -> None:
        """Append one NEW record as a line (``O_APPEND`` semantics — race-benign)."""

    def iter_records(self) -> Iterator[T]:
        """Yield every stored record, in file order, tolerating malformed lines."""

    def update(self, record_id: str, mutate: Callable[[T], T]) -> T:
        """Read-modify-write the ONE line matching *record_id*, in place.

        Re-reads the file immediately before the rewrite and raises
        :class:`StaleRecordWriteError` when it changed since the record was read,
        rather than clobbering a write it never saw. Raises :class:`RecordNotFoundError`
        when no record matches *record_id*. Every other line is left byte-identical.
        """


__all__ = ["RecordNotFoundError", "RecordStore", "StaleRecordWriteError"]
