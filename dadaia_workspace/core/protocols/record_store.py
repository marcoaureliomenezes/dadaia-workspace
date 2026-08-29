"""RecordStore Protocol — the generic "one record per id, appended once" port.

v0.5.0 FR2, AR-1 ruling answer (b) (`specs/releases/0.5.0/reviews/S1-AR1-ruling.md`
§2), amended by the S1 FR23 firing (`specs/releases/0.5.0/reviews/S1-FR23-firing.md`
A1). Zero I/O (per the core ring rule): only the Protocol and its two typed failures
live here — the concrete adapter (``infrastructure.jsonl_record_store.JsonlRecordStore``)
is model-agnostic and imports no model (AR-1 (b)(iv)); each feature's own model
(``core.models.bugs.BugRecord`` today; ``findings``/``backlog`` later, per the same
ruling) supplies its own parse/serialise callables and receives its own store instance
from the container, so no module knows more than one record shape (A2.5, A13.4). This
is the port a future ``features/*/service.py`` depends on instead of the concrete
adapter — the same shape ``core/protocols/bug_store.py`` served the event-sourced store
before this release (mirrors ``core/protocols/git_object_reader.py``).

**No file-level escape hatch.** The Protocol exposes no ``path`` — the ONE seam that
let a caller reach through the store and rewrite the ledger's bytes directly was the
reader/writer-count leak the S1 firing ruling closed. Every removal goes through
:meth:`remove`, which carries the SAME refuse-stale race semantics :meth:`update`
already has.

**``MalformedLine`` / two read methods.** :meth:`scan` yields a :class:`MalformedLine`
in place of skipping a line that fails to parse — the ONE malformed-line diagnosis a
diagnostic caller (``specs doctor``) uses instead of writing a second reader.
:meth:`iter_records` is the tolerant view: the SAME classification, skipped with a
WARN log instead of surfaced. The split rule (a literal ``"\\n"``, never
``str.splitlines()``) and the "what counts as parseable" rule (the model's own
``from_dict``) are each stated in exactly one place, shared by both methods.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MalformedLine:
    """One ledger line a :class:`RecordStore` could not parse as its record type —
    the ONE malformed-line diagnosis :meth:`RecordStore.scan` yields, covering every
    way a line can fail: not valid JSON, not a JSON
    object, or refused by the model's own ``from_dict`` (a missing required field,
    an invalid closed-enum value, or — historically — a v5-shaped event line that
    never carried the v6 required field set). ``lineno`` is 1-based, counted over a
    literal ``"\\n"`` split (never ``str.splitlines()``, which corrupts the count on
    a line carrying a U+2028/U+2029/U+0085 unicode line separator)."""

    lineno: int
    raw: str
    reason: str


class RecordNotFoundError(Exception):
    """Raised by :meth:`RecordStore.update` when no record with the given id exists."""

    def __init__(self, record_id: str) -> None:
        super().__init__(f"no record with id {record_id!r}")
        self.record_id = record_id


class StaleRecordWriteError(Exception):
    """Raised by :meth:`RecordStore.update`/:meth:`RecordStore.remove` when the file
    changed since it was read.

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

    def append(self, record: T) -> None:
        """Append one NEW record as a line (``O_APPEND`` semantics — race-benign)."""

    def scan(self) -> Iterator[T | MalformedLine]:
        """Yield every stored record OR :class:`MalformedLine` diagnosis, in file
        order — the ONE malformed-line diagnosis every diagnostic caller (``specs
        doctor``) reads through, never a second, hand-rolled parser."""

    def iter_records(self) -> Iterator[T]:
        """Yield every stored record, in file order — the tolerant view: a line
        :meth:`scan` would diagnose as :class:`MalformedLine` is skipped instead,
        WARN-logged, never breaking the whole stream."""

    def update(self, record_id: str, mutate: Callable[[T], T]) -> T:
        """Read-modify-write the ONE line matching *record_id*, in place.

        Re-reads the file immediately before the rewrite and raises
        :class:`StaleRecordWriteError` when it changed since the record was read,
        rather than clobbering a write it never saw. Raises :class:`RecordNotFoundError`
        when no record matches *record_id*. Every other line is left byte-identical.
        """

    def remove(self, record_ids: Iterable[str]) -> list[T]:
        """Drop every record whose id is in *record_ids*, returning the removed
        records in file order (v0.5.0 S1 FR23 firing, A1).

        The store's OWN removal seam — the caller that used to read the ledger's raw
        bytes to build an archive rewrite (``BugService.archive``) now goes through
        this method instead, with the SAME refuse-stale race semantics :meth:`update`
        already has: re-reads the file immediately before the atomic rewrite and raises
        :class:`StaleRecordWriteError` when it changed since the snapshot was read.
        Empty *record_ids*, or none matching, is a no-op returning ``[]`` without
        touching the file.
        """


__all__ = ["MalformedLine", "RecordNotFoundError", "RecordStore", "StaleRecordWriteError"]
