"""Read-only, model-agnostic JSONL store; every ledger's ONE writer is its skill script.

Splits on ``"\\n"`` only: ``str.splitlines()`` would break a record on U+2028.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

__all__ = ["JsonlRecordStore", "MalformedLine"]

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class MalformedLine:
    """A line that is not JSON, not an object, or refused by ``from_dict``; ``lineno`` 1-based."""

    lineno: int
    raw: str
    reason: str


class JsonlRecordStore[T]:
    """Parses each non-blank line of *path* with *from_dict*."""

    def __init__(self, path: Path, *, from_dict: Callable[[Mapping[str, object]], T]) -> None:
        self._path = path
        self._from_dict = from_dict

    def scan(self) -> Iterator[T | MalformedLine]:
        """Every record OR :class:`MalformedLine`, in file order."""
        text = self._path.read_text(encoding="utf-8") if self._path.is_file() else ""
        for lineno, line in enumerate(text.split("\n"), start=1):
            stripped = line.strip()
            if stripped:
                yield self._parse_line(lineno, stripped)

    def iter_records(self) -> Iterator[T]:
        """Every record in file order; a malformed line is skipped with a logged WARN."""
        for parsed in self.scan():
            if isinstance(parsed, MalformedLine):
                _LOG.warning("skipping malformed record line in %s: %s", self._path, parsed.reason)
                continue
            yield parsed

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
