"""Append-only JSONL store for event-sourced bug telemetry (v0.1.46 AC-1).

Unlike ``JsonLifecycleRunStore`` (mkstemp + ``os.replace``, replace-on-save), this store
is genuinely **append-only**: each event is one line appended (``O_APPEND`` semantics via
open mode ``"a"``) to ``specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl`` where ``<n>`` is a
zero-padded rotation counter. When the current ``(hour, n)`` file reaches
:data:`ROWS_PER_FILE` rows, appends roll to ``<same-hour>Z-<n+1>.jsonl`` (the within-hour
disambiguator is mandatory because >1000 rows is a hard doctor ERROR and a bare
``<hour>Z.jsonl`` name has no rotation room). Reads stream all matching files sorted by
``(hour, n)`` — chronological — tolerating malformed lines with a logged WARN.

The store is time-injection-free: the hour bucket is derived from each event's own ``ts``,
so behaviour is deterministic without an argless ``datetime.now`` call.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from dadaia_workspace.core.models.bugs import BugEvent

__all__ = ["ROWS_PER_FILE", "JsonlBugStore"]

#: Rotation ceiling — the doctor ERRORs on any file exceeding this row count.
ROWS_PER_FILE = 1000

#: Canonical bug-log filename: ``<YYYYMMDDTHH>Z-<n>.jsonl`` (n = decimal counter).
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
        """Append one event as a JSONL line, rotating on the row ceiling. Returns the file."""
        self._dir.mkdir(parents=True, exist_ok=True)
        hour = self._hour_bucket(event.ts)
        target = self._target_file(hour)
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
        """
        for path in self._sorted_files():
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                _LOG.warning("skipping unreadable bug log %s: %s", path, exc)
                continue
            for line in text.splitlines():
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

    @staticmethod
    def _hour_bucket(ts: str) -> str:
        """Derive the compact ``YYYYMMDDTHH`` hour bucket from an ISO-8601 ``ts``."""
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return parsed.strftime("%Y%m%dT%H")

    def _target_file(self, hour: str) -> Path:
        """Return the file to append to for ``hour`` — rolling to ``n+1`` at the ceiling."""
        existing = sorted(self._files_for_hour(hour), key=self._counter)
        if not existing:
            return self._dir / f"{hour}Z-00.jsonl"
        last = existing[-1]
        if self._row_count(last) >= ROWS_PER_FILE:
            return self._dir / f"{hour}Z-{self._counter(last) + 1:02d}.jsonl"
        return last

    def _files_for_hour(self, hour: str) -> list[Path]:
        if not self._dir.is_dir():
            return []
        out: list[Path] = []
        for path in self._dir.glob(f"{hour}Z-*.jsonl"):
            match = _BUG_LOG_RE.match(path.name)
            if match is not None and match.group("hour") == hour:
                out.append(path)
        return out

    def _sorted_files(self) -> list[Path]:
        if not self._dir.is_dir():
            return []
        matched: list[Path] = [
            p for p in self._dir.glob("*.jsonl") if _BUG_LOG_RE.match(p.name) is not None
        ]
        return sorted(matched, key=self._sort_key)

    @staticmethod
    def _sort_key(path: Path) -> tuple[str, int]:
        match = _BUG_LOG_RE.match(path.name)
        assert match is not None  # noqa: S101 — only matched files reach here
        return match.group("hour"), int(match.group("n"))

    @staticmethod
    def _counter(path: Path) -> int:
        match = _BUG_LOG_RE.match(path.name)
        assert match is not None  # noqa: S101 — only matched files reach here
        return int(match.group("n"))

    @staticmethod
    def _row_count(path: Path) -> int:
        with path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
