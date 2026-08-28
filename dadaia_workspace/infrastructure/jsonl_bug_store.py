"""Append-only JSONL store for event-sourced bug telemetry (v0.1.46 AC-1 / v0.1.73 FR1).

Genuinely **append-only**: each event is one line appended (``O_APPEND`` semantics via
open mode ``"a"``) to the SINGLE canonical ``specs/bugs/bugs.jsonl`` — the operator
contract (bug ``bugs-store-fragments-into-hourly-files``: the v0.1.46 per-hour
``<YYYYMMDDTHH>Z-<n>.jsonl`` rotation was implementation drift that fragmented the
ledger into dozens of files). Reads stream the legacy hourly files first (sorted by
``(hour, n)``) and the canonical file last — chronological in both the pre- and
post-consolidation regimes — tolerating malformed lines with a logged WARN. The
``bugs-single-file`` migration (specs upgrade v3→4) consolidates the legacy files into
``bugs.jsonl``.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugEvent

__all__ = ["CANONICAL_FILENAME", "ROWS_PER_FILE", "JsonlBugStore"]

#: Legacy rotation ceiling — the doctor still ERRORs on a LEGACY hourly file exceeding
#: this row count (the single canonical file has no rotation by operator contract).
ROWS_PER_FILE = 1000

#: The single canonical ledger file (v0.1.73 FR1 — operator contract).
CANONICAL_FILENAME = "bugs.jsonl"

#: Legacy bug-log filename: ``<YYYYMMDDTHH>Z-<n>.jsonl`` (n = decimal counter).
_BUG_LOG_RE = re.compile(r"^(?P<hour>\d{8}T\d{2})Z-(?P<n>\d+)\.jsonl$")

_LOG = logging.getLogger(__name__)


class JsonlBugStore:
    """Append-only JSONL bug-event store rooted at a ``specs/bugs/`` directory."""

    def __init__(self, bugs_dir: Path) -> None:
        self._dir = bugs_dir

    @property
    def root(self) -> Path:
        return self._dir

    # -- writes --------------------------------------------------------------------

    def append_event(self, event: BugEvent) -> Path:
        """Append one event as a JSONL line to the single canonical file (v0.1.73 FR1)."""
        self._dir.mkdir(parents=True, exist_ok=True)
        target = self._dir / CANONICAL_FILENAME
        line = json.dumps(event.to_dict(), sort_keys=True, ensure_ascii=False) + "\n"
        with target.open("a", encoding="utf-8") as handle:
            handle.write(line)
        return target

    # -- reads ---------------------------------------------------------------------

    def iter_events(self) -> Iterator[BugEvent]:
        """Yield every event across all ``*.jsonl`` files sorted by ``(hour, n)``.

        Malformed JSON lines and records failing model parse are skipped with a logged
        WARN — a single corrupt line never breaks the whole stream (mirrors the
        corrupt-record tolerance in ``JsonLifecycleRunStore.list_runs``).

        Splits on ``"\\n"`` only — never ``str.splitlines()`` (v0.4.5 FR7, bug
        ``bug-event-field-with-unicode-line-separator-silently-drops-the-event``).
        JSONL is a strict newline-delimited format: exactly one physical ``"\\n"``
        terminates a record, and JSON permits every code point ``splitlines()``
        additionally treats as a terminator (U+000B/U+000C/U+001C-U+001E/U+0085/
        U+2028/U+2029) to appear unescaped inside a string. ``str.splitlines()`` is a
        general text-processing helper, not a line-delimited-format reader — using it
        here fragmented any record whose field happened to carry one of those bytes
        into two unparseable halves, silently dropping the whole event. Written events
        no longer carry these bytes at all (``core.models.bugs.redact_text`` strips
        them at the write seam), but this read-side fix is the actual root cause: any
        writer, present or future, that ever emits one of these bytes must still be
        read correctly.
        """
        for path in self._sorted_files():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                _LOG.warning("skipping unreadable bug log %s: %s", path, exc)
                continue
            for line in text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    raw = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    _LOG.warning("skipping malformed bug-event line in %s: %s", path, exc)
                    continue
                if not isinstance(raw, dict):
                    _LOG.warning("skipping non-object bug-event line in %s", path)
                    continue
                try:
                    yield BugEvent.from_dict(raw)
                except (ValueError, TypeError) as exc:
                    _LOG.warning("skipping invalid bug-event record in %s: %s", path, exc)
                    continue

    def files(self) -> list[Path]:
        """Return the bug-log files sorted by ``(hour, n)`` (chronological)."""
        return self._sorted_files()

    # -- internals -----------------------------------------------------------------

    def _sorted_files(self) -> list[Path]:
        """Legacy hourly files chronologically, then the canonical ``bugs.jsonl`` last.

        Pre-consolidation workspaces read legacy history + the new canonical tail in
        order; post-consolidation only ``bugs.jsonl`` remains.
        """
        if not self._dir.is_dir():
            return []
        legacy: list[Path] = [
            p for p in self._dir.glob("*.jsonl") if _BUG_LOG_RE.match(p.name) is not None
        ]
        ordered = sorted(legacy, key=self._sort_key)
        canonical = self._dir / CANONICAL_FILENAME
        if canonical.is_file():
            ordered.append(canonical)
        return ordered

    @staticmethod
    def _sort_key(path: Path) -> tuple[str, int]:
        match = _BUG_LOG_RE.match(path.name)
        assert match is not None  # noqa: S101 — only matched files reach here
        return match.group("hour"), int(match.group("n"))
