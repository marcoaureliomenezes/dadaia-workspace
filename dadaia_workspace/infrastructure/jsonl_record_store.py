"""Generic JSONL "one record per id" store (v0.5.0 FR2, AR-1 ruling answer (b)).

Model-agnostic: it knows the ledger's file mechanics only — append, iterate, atomic
in-place rewrite, refuse-stale — and imports no model (`core/protocols/record_store.py`
docstring, AR-1 (b)(iv)). Takes a file ``Path`` directly, never a directory plus a
filename constant — the ledger's actual name (``BUGS.jsonl`` today) is the
feature/container's concern, this module knows no ledger (AR-1 (b)(i)). Reads split on
``"\\n"`` only, never ``str.splitlines()`` — carrying forward the T-045-20 root-cause fix
at the one reader this release leaves standing (AR-1 (b)(ii); bug
``bug-event-field-with-unicode-line-separator-silently-drops-the-event``).

``update``/``remove`` refuse a stale rewrite by comparing the ledger's LIVE bytes,
re-read as ``atomic_write``'s very last step before ``os.replace`` (``expected_previous``,
bug ``bugs-record-store-append-clobbers-concurrent-update-batch``), to the snapshot read
at the top of the call — never mtime (sub-second granularity, Windows; AR-1 (b)(iii)) —
raising :class:`~dadaia_workspace.core.protocols.record_store.StaleRecordWriteError` the
caller retries (A2.9, one race semantics: refuse-stale, never last-write-wins). A
staleness check performed by the CALLER before invoking a separate, unconditional write
call leaves a gap for exactly this: a concurrent write landing while that write call is
still serializing content is invisible to the caller's own check and gets silently
discarded by the swap that follows — the symptom the bug above reports (a concurrent
``append`` erasing an in-flight ``update`` batch, every command exiting 0). Every line
OTHER than the one being updated is copied through verbatim (never re-serialized), so a
governance update leaves every other byte of the file identical (A2.2c).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable, Iterator, Mapping
from pathlib import Path

from dadaia_workspace.core.atomic_write import ConcurrentModificationError, atomic_write
from dadaia_workspace.core.protocols.record_store import (
    MalformedLine,
    RecordNotFoundError,
    StaleRecordWriteError,
)

__all__ = ["JsonlRecordStore"]

_LOG = logging.getLogger(__name__)


class JsonlRecordStore[T]:
    """Model-agnostic JSONL store keyed by each record's ``"id"`` field.

    *to_dict* / *from_dict* are plain callables (never a hand-imported model type —
    this module stays generic across bugs/findings/backlog) that serialize a record to
    its JSONL object shape and parse one back. Structurally satisfies
    :class:`~dadaia_workspace.core.protocols.record_store.RecordStore`.
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

        NOT part of the :class:`~dadaia_workspace.core.protocols.record_store.RecordStore`
        Protocol (v0.5.0 S1 FR23 firing, A1) — a caller typed to the Protocol can never
        reach through it to the raw file; this remains a plain implementation-detail
        attribute of the concrete adapter, for a test that builds one directly (never
        for a feature-layer consumer holding the Protocol type).
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
