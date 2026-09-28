"""The ONE history-record shape and the ONE terminal vocabulary (0.4.7 FR7, T-047-03).

Three ``_histo.jsonl`` files carry the terminal record of everything that leaves a
live governance document — ``backlog/_archive/backlog_histo.jsonl``,
``audits/_archive/audits_histo.jsonl``, ``releases/_archive/releases_histo.jsonl`` —
and each was written by its own writer, in its own shape, with no schema and no
reader: two of them are event streams wrapping a free-form ``data`` object, the third
is a record with two snapshot fields nothing ever read. That is the structural cause
the 2026-09-12 lifecycle audit named: schemas existed for live documents only.

:class:`HistoRecord` is that one shape — seven fields, the same seven for all three
files — and :data:`TERMINAL_DISPOSITIONS` is the one lowercase vocabulary. Each
ledger's own subset and required evidence live in its script, the one reader
(sa-ledger-vocabulary-and-atomic-write-duplicated-in-scripts).

Pure domain module: stdlib only, no I/O — ``core`` reads no schema file itself
(``tests/contract/test_core_file_io_purity.py``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

__all__ = [
    "TERMINAL_DISPOSITIONS",
    "HistoRecord",
    "is_terminal_disposition",
]

#: The one terminal vocabulary (SPEC 0.4.7 FR7), lowercase. Each ledger script's own
#: subset is a slice of THIS tuple.
TERMINAL_DISPOSITIONS: tuple[str, ...] = (
    "delivered",
    "resolved",
    "superseded",
    "deferred",
    "rejected",
)

_TERMINAL_DISPOSITION_SET = frozenset(TERMINAL_DISPOSITIONS)


def is_terminal_disposition(token: str | None) -> bool:
    """True iff *token* is (case-insensitively) one of :data:`TERMINAL_DISPOSITIONS`.

    The backlog doctor's BL-STALE condition (b) — "this live ``active[]`` entry's own
    status is already a terminal verdict" — is the one caller; it asks the SAME
    vocabulary every ``_histo.jsonl`` record is validated against, so the words live
    here and nowhere else.
    """
    return token is not None and token.strip().lower() in _TERMINAL_DISPOSITION_SET


def _require_str(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"histo record field {key!r} must be a non-empty string, got {value!r}")
    return value


def _optional_str(raw: Mapping[str, Any], key: str) -> str | None:
    if key not in raw:
        raise ValueError(f"histo record is missing required field {key!r}")
    value = raw[key]
    if value is None or isinstance(value, str):
        return value
    raise ValueError(f"histo record field {key!r} must be a string or null, got {value!r}")


@dataclass(frozen=True)
class HistoRecord:
    """One terminal record of one exit, in any ``_histo.jsonl``.

    ``id``/``ts``/``disposition`` are the immutable core (the record's identity and
    its terminal verdict); ``release``/``reason``/``summary`` are nullable free text;
    ``entry`` is the removed object itself (a backlog entry, an audit's counts) or
    ``None`` when the exit had nothing to snapshot.

    A private term never reaches a record: the ledger script refuses the write
    (sa-ledger-write-seam-redacts-less-than-push-refuses).
    """

    id: str
    ts: str
    disposition: str
    release: str | None
    reason: str | None
    summary: str | None
    entry: dict[str, Any] | None

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> HistoRecord:
        """Parse one JSONL object. Raises ``ValueError`` on a malformed record, so a
        tolerant reader can skip it (mirrors ``BugRecord``)."""
        if "entry" not in raw:
            raise ValueError("histo record is missing required field 'entry'")
        entry = raw["entry"]
        if entry is not None and not isinstance(entry, dict):
            raise ValueError(f"histo record field 'entry' must be an object or null, got {entry!r}")
        return cls(
            id=_require_str(raw, "id"),
            ts=_require_str(raw, "ts"),
            disposition=_require_str(raw, "disposition"),
            release=_optional_str(raw, "release"),
            reason=_optional_str(raw, "reason"),
            summary=_optional_str(raw, "summary"),
            entry=entry,
        )
