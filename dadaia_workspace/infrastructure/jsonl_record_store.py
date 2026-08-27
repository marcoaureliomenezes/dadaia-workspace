"""Generic JSONL "one record per id" store (v0.5.0 FR2, AR-1 ruling answer (b)).

Model-agnostic: it knows the ledger's file mechanics only — append, iterate, atomic
in-place rewrite, refuse-stale — and imports no model (`core/protocols/record_store.py`
docstring, AR-1 (b)(iv)). Takes a file ``Path`` directly, never a directory plus a
filename constant — the ledger's actual name (``BUGS.jsonl`` today) is the
feature/container's concern, this module knows no ledger (AR-1 (b)(i)). Reads split on
``"\\n"`` only, never ``str.splitlines()`` — carrying forward the T-045-20 root-cause fix
at the one reader this release leaves standing (AR-1 (b)(ii); bug
``bug-event-field-with-unicode-line-separator-silently-drops-the-event``).

``update`` re-reads the file immediately before ``atomic_write`` and refuses a stale
rewrite by comparing the RE-READ BYTES to the snapshot read at the top of the call —
never mtime (sub-second granularity, Windows; AR-1 (b)(iii)) — raising
:class:`~dadaia_workspace.core.protocols.record_store.StaleRecordWriteError` the caller
retries (A2.9, one race semantics: refuse-stale, never last-write-wins). Every line
OTHER than the one being updated is copied through verbatim (never re-serialized), so a
governance update leaves every other byte of the file identical (A2.2c).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

from dadaia_workspace.core.atomic_write import atomic_write
from dadaia_workspace.core.protocols.record_store import (
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
        after_reread = self._read_text()
        if after_reread != before:
            raise StaleRecordWriteError(record_id)
        atomic_write(self._path, "\n".join(new_lines), newline="")
        return updated

    # -- reads ---------------------------------------------------------------------

    def iter_records(self) -> Iterator[T]:
        """Yield every stored record in file order.

        Malformed JSON, a non-object line, or a model-parse failure is skipped with a
        logged WARN — a single corrupt line never breaks the whole stream (mirrors the
        tolerance ``infrastructure.jsonl_bug_store.JsonlBugStore.iter_events`` already
        has). Splits on ``"\\n"`` ONLY (never ``str.splitlines()``) — the T-045-20 fix,
        carried forward at the one reader this release leaves standing.
        """
        for line in self._read_text().split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            record = self._parse_line(stripped)
            if record is not None:
                yield record

    # -- internals -------------------------------------------------------------------

    def _read_text(self) -> str:
        if not self._path.is_file():
            return ""
        return self._path.read_text(encoding="utf-8")

    def _parse_line(self, stripped: str) -> T | None:
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            _LOG.warning("skipping malformed record line in %s: %s", self._path, exc)
            return None
        if not isinstance(raw, dict):
            _LOG.warning("skipping non-object record line in %s", self._path)
            return None
        try:
            return self._from_dict(raw)
        except (ValueError, TypeError) as exc:
            _LOG.warning("skipping invalid record in %s: %s", self._path, exc)
            return None
