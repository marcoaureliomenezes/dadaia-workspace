"""Generic JSONL "one record per id" store (v0.5.0 FR2, AR-1 ruling answer (b)).

ADR-0001 (accepted, "the ring rule stays but the PORT requirement is dropped"):
:class:`JsonlRecordStore` was the ONLY production adapter behind the retired
``core/protocols/record_store.py`` Protocol — a single-adapter port is pure interface
tax (measured: 23 Protocol classes workspace-wide, only 4 with >= 2 adapters), so every
consumer now types against this concrete class directly
(``tests/contract/test_protocols_have_two_adapters.py`` polices the Protocol set that
remains). :class:`MalformedLine`, :class:`RecordNotFoundError` and
:class:`StaleRecordWriteError` move here with it — they are this store's own
diagnostics/exceptions, never shared by a second adapter, so they have no reason to
live in a separate ``core/protocols`` module either.

Model-agnostic: it knows the ledger's file mechanics only — append, iterate, atomic
in-place rewrite, refuse-stale — and imports no model (AR-1 (b)(iv)). Takes a file
``Path`` directly, never a directory plus a filename constant — the ledger's actual name
(``BUGS.jsonl`` today) is the feature/CLI caller's concern, this module knows no ledger
(AR-1 (b)(i)). Reads split on ``"\\n"`` only, never ``str.splitlines()`` — carrying
forward the T-045-20 root-cause fix at the one reader this release leaves standing
(AR-1 (b)(ii); bug ``bug-event-field-with-unicode-line-separator-silently-drops-the-event``).

``update``/``remove`` refuse a stale rewrite by comparing the ledger's LIVE bytes,
re-read as ``atomic_write``'s very last step before ``os.replace`` (``expected_previous``,
bug ``bugs-record-store-append-clobbers-concurrent-update-batch``), to the snapshot read
at the top of the call — never mtime (sub-second granularity, Windows; AR-1 (b)(iii)) —
raising :class:`StaleRecordWriteError` the caller retries (A2.9, one race semantics:
refuse-stale, never last-write-wins). A staleness check performed by the CALLER before
invoking a separate, unconditional write call leaves a gap for exactly this: a
concurrent write landing while that write call is still serializing content is
invisible to the caller's own check and gets silently discarded by the swap that
follows — the symptom the bug above reports (a concurrent ``append`` erasing an
in-flight ``update`` batch, every command exiting 0). Every line OTHER than the one
being updated is copied through verbatim (never re-serialized), so a governance update
leaves every other byte of the file identical (A2.2c).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.atomic_write import ConcurrentModificationError, atomic_write

__all__ = ["JsonlRecordStore", "MalformedLine", "RecordNotFoundError", "StaleRecordWriteError"]

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class MalformedLine:
    """One ledger line a :class:`JsonlRecordStore` could not parse as its record type —
    the ONE malformed-line diagnosis :meth:`JsonlRecordStore.scan` yields, covering
    every way a line can fail: not valid JSON, not a JSON object, or refused by the
    model's own ``from_dict`` (a missing required field, an invalid closed-enum value,
    or — historically — a v5-shaped event line that never carried the v6 required field
    set). ``lineno`` is 1-based, counted over a literal ``"\\n"`` split (never
    ``str.splitlines()``, which corrupts the count on a line carrying a
    U+2028/U+2029/U+0085 unicode line separator)."""

    lineno: int
    raw: str
    reason: str


class RecordNotFoundError(Exception):
    """Raised by :meth:`JsonlRecordStore.update` when no record with the given id exists."""

    def __init__(self, record_id: str) -> None:
        super().__init__(f"no record with id {record_id!r}")
        self.record_id = record_id


class StaleRecordWriteError(Exception):
    """Raised by :meth:`JsonlRecordStore.update`/:meth:`JsonlRecordStore.remove` when the
    file changed since it was read.

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


class JsonlRecordStore[T]:
    """Model-agnostic JSONL store keyed by each record's ``"id"`` field.

    *to_dict* / *from_dict* are plain callables (never a hand-imported model type —
    this module stays generic across bugs/findings/backlog) that serialize a record to
    its JSONL object shape and parse one back — the sole production adapter
    (ADR-0001; the port it used to satisfy, ``core/protocols/record_store.py``, is
    retired).
    """

    def __init__(
        self,
        path: Path,
        *,
        to_dict: Callable[[T], dict[str, object]],
        from_dict: Callable[[Mapping[str, object]], T],
    ) -> None:
        self._path = path
        self._to_dict = to_dict
        self._from_dict = from_dict

    @property
    def path(self) -> Path:
        """The ledger file this concrete store instance is rooted at.

        Never surfaced through a typed seam a caller could reach through to rewrite the
        ledger's raw bytes directly (v0.5.0 S1 FR23 firing, A1) — this remains a plain
        implementation-detail attribute, for a test that builds one directly.
        """
        return self._path

    # -- writes --------------------------------------------------------------------

    def append(self, record: T) -> None:
        """Append one record as a JSONL line (``O_APPEND`` semantics — race-benign)."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(self._to_dict(record), sort_keys=True, ensure_ascii=False) + "\n"
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def update(self, record_id: str, mutate: Callable[[T], T]) -> T:
        """Read-modify-write the ONE line whose ``"id"`` is *record_id*, in place."""
        before = self._read_text()
        lines = before.split("\n")
        new_lines: list[str] = []
        updated: T | None = None
        found = False
        for line in lines:
            if found:
                new_lines.append(line)
                continue
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue
            if isinstance(raw, dict) and raw.get("id") == record_id:
                found = True
                updated = mutate(self._from_dict(raw))
                new_lines.append(
                    json.dumps(self._to_dict(updated), sort_keys=True, ensure_ascii=False)
                )
            else:
                new_lines.append(line)
        if not found or updated is None:
            raise RecordNotFoundError(record_id)
        try:
            atomic_write(self._path, "\n".join(new_lines), newline="", expected_previous=before)
        except ConcurrentModificationError as exc:
            raise StaleRecordWriteError(record_id) from exc
        return updated

    def remove(self, record_ids: Iterable[str]) -> list[T]:
        """Drop every line whose ``"id"`` is in *record_ids*, returning the removed
        records in file order (v0.5.0 S1 FR23 firing, A1) — the SAME
        read-snapshot / filter / re-read-compare / ``atomic_write`` shape
        :meth:`update` already uses, so a caller that used to rewrite the ledger's raw
        bytes (``BugService.archive``) gets the SAME refuse-stale race guarantee."""
        ids = frozenset(record_ids)
        if not ids:
            return []
        before = self._read_text()
        lines = before.split("\n")
        kept_lines: list[str] = []
        removed: list[T] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                kept_lines.append(line)
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError:
                kept_lines.append(line)
                continue
            if isinstance(raw, dict) and raw.get("id") in ids:
                removed.append(self._from_dict(raw))
                continue
            kept_lines.append(line)
        if not removed:
            return []
        try:
            atomic_write(self._path, "\n".join(kept_lines), newline="", expected_previous=before)
        except ConcurrentModificationError as exc:
            raise StaleRecordWriteError(next(iter(ids))) from exc
        return removed

    # -- reads ---------------------------------------------------------------------

    def scan(self) -> Iterator[T | MalformedLine]:
        """Yield every stored record OR :class:`MalformedLine` diagnosis, in file
        order — the ONE malformed-line diagnosis, so a diagnostic caller (``specs
        doctor``) never needs its own second parser. Splits on ``"\\n"`` ONLY (never
        ``str.splitlines()``) — the T-045-20 fix, carried forward at the one reader
        this release leaves standing.
        """
        for lineno, line in enumerate(self._read_text().split("\n"), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            yield self._parse_line(lineno, stripped)

    def iter_records(self) -> Iterator[T]:
        """Yield every stored record in file order — the tolerant view: a line
        :meth:`scan` would diagnose as :class:`MalformedLine` is skipped instead,
        with a logged WARN, never breaking the whole stream."""
        for parsed in self.scan():
            if isinstance(parsed, MalformedLine):
                _LOG.warning("skipping malformed record line in %s: %s", self._path, parsed.reason)
                continue
            yield parsed

    # -- internals -------------------------------------------------------------------

    def _read_text(self) -> str:
        if not self._path.is_file():
            return ""
        return self._path.read_text(encoding="utf-8")

    def _parse_line(self, lineno: int, stripped: str) -> T | MalformedLine:
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            return MalformedLine(lineno=lineno, raw=stripped, reason=f"not valid JSON: {exc.msg}")
        if not isinstance(raw, dict):
            return MalformedLine(lineno=lineno, raw=stripped, reason="not a JSON object")
        try:
            return self._from_dict(raw)
        except (ValueError, TypeError) as exc:
            return MalformedLine(lineno=lineno, raw=stripped, reason=str(exc))
