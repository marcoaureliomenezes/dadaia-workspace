"""The ONE history-record shape and the ONE terminal vocabulary (0.4.7 FR7, T-047-03).

Three ``_histo.jsonl`` files carry the terminal record of everything that leaves a
live governance document — ``backlog/_archive/backlog_histo.jsonl``,
``audits/_archive/audits_histo.jsonl``, ``releases/_archive/releases_histo.jsonl`` —
and each was written by its own writer, in its own shape, with no schema and no
reader: two of them are event streams wrapping a free-form ``data`` object, the third
is a record with two snapshot fields nothing ever read. That is the structural cause
the 2026-09-12 lifecycle audit named: schemas existed for live documents only.

:class:`HistoRecord` is that one shape — seven fields, the same seven for all three
files — and :data:`TERMINAL_DISPOSITIONS` is the one lowercase vocabulary every
ledger's subset is drawn from. A subset is a validator PARAMETER (which words this
ledger may use), never a second schema file.

Pure domain module: stdlib only, no I/O — ``core`` reads no schema file itself
(``tests/contract/test_core_file_io_purity.py``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from dataclasses import fields as dc_fields
from typing import Any

from dadaia_workspace.core.redaction import redact_text

__all__ = [
    "AUDITS_HISTO_DISPOSITIONS",
    "BACKLOG_HISTO_DISPOSITIONS",
    "BUGS_DISPOSITIONS",
    "FINDINGS_DISPOSITIONS",
    "RELEASES_HISTO_DISPOSITIONS",
    "TERMINAL_DISPOSITIONS",
    "HistoRecord",
    "is_terminal_disposition",
]

#: The one terminal vocabulary (SPEC 0.4.7 FR7), lowercase. Every per-ledger subset
#: below is a slice of THIS tuple, in this order.
TERMINAL_DISPOSITIONS: tuple[str, ...] = (
    "delivered",
    "resolved",
    "superseded",
    "deferred",
    "rejected",
)

#: A backlog item is delivered, superseded or rejected — it is never "resolved" (that
#: is a bug's word) and a deferred item returns to ``active[]`` rather than exiting.
BACKLOG_HISTO_DISPOSITIONS: tuple[str, ...] = ("delivered", "superseded", "rejected")

#: A bug's four terminal statuses — the same four words
#: ``core.models.bugs.TERMINAL_EVENTS`` is built from, so there is one constant, not two.
BUGS_DISPOSITIONS: tuple[str, ...] = ("resolved", "superseded", "deferred", "rejected")

#: An audit finding's terminal dispositions — the ONE finding vocabulary (0.4.7 FR4):
#: ``finding-record-v1.schema.json``'s ``disposition`` enum is ``open`` plus exactly
#: these words, ``features/specs/audit.py`` validates against them, and
#: ``doctor_closure_audit`` folds them. The historical ``fixed`` was renamed
#: ``resolved`` with zero committed ``FINDINGS.jsonl`` to migrate.
FINDINGS_DISPOSITIONS: tuple[str, ...] = ("resolved", "superseded", "deferred", "rejected")

#: An archived audit's histo record uses the findings subset.
AUDITS_HISTO_DISPOSITIONS: tuple[str, ...] = FINDINGS_DISPOSITIONS

#: A release exits exactly once, by being shipped.
RELEASES_HISTO_DISPOSITIONS: tuple[str, ...] = ("delivered",)

_TERMINAL_DISPOSITION_SET = frozenset(TERMINAL_DISPOSITIONS)


def is_terminal_disposition(token: str | None) -> bool:
    """True iff *token* is (case-insensitively) one of :data:`TERMINAL_DISPOSITIONS`.

    The backlog doctor's BL-STALE condition (b) — "this live ``active[]`` entry's own
    status is already a terminal verdict" — is the one caller; it asks the SAME
    vocabulary every ``_histo.jsonl`` record is validated against, so the words live
    here and nowhere else.
    """
    return token is not None and token.strip().lower() in _TERMINAL_DISPOSITION_SET


def _scrub(value: Any, denylist_terms: Sequence[tuple[str, str]]) -> Any:
    """Mask every string reachable from *value* — ``entry`` is an arbitrary JSON tree,
    so the walk recurses through dicts and lists; keys are masked too, since a
    denylisted term can name a field as easily as fill one."""
    if isinstance(value, str):
        return redact_text(value, denylist_terms)
    if isinstance(value, dict):
        return {
            _scrub(key, denylist_terms): _scrub(item, denylist_terms) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item, denylist_terms) for item in value]
    return value


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

    ``id``/``ts``/``disposition`` carry ``metadata={"identity": True}`` — the
    record's identity and its controlled terminal verdict, the only fields
    :meth:`redact` never scrubs. Every other field is free text (or, for ``entry``,
    a free-text tree) a committed exit snapshot must never carry a denylisted term
    in (bug ``backlog-histo-writer-skips-write-time-denylist-redaction``).
    """

    id: str = field(metadata={"identity": True})
    ts: str = field(metadata={"identity": True})
    disposition: str = field(metadata={"identity": True})
    release: str | None
    reason: str | None
    summary: str | None
    entry: dict[str, Any] | None

    def redact(self, denylist_terms: Sequence[tuple[str, str]] = ()) -> HistoRecord:
        """Return a copy with every free-text field — including every string nested
        anywhere inside ``entry`` — scrubbed via
        :func:`~dadaia_workspace.core.redaction.redact_text`, the SAME primitive
        :meth:`~dadaia_workspace.core.models.bugs.BugRecord.redact` calls.

        The field set is derived from THIS dataclass's own ``metadata`` (A2.10),
        never a hand-kept name list: a field added below is redacted by default with
        no code edited here.
        """
        updates: dict[str, Any] = {
            name: _scrub(getattr(self, name), denylist_terms)
            for name in _HISTO_RECORD_REDACTABLE_FIELDS
        }
        return replace(self, **updates)

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape (``"id"`` present so the generic
        ``JsonlRecordStore.update`` seam can locate this record)."""
        return {
            "id": self.id,
            "ts": self.ts,
            "disposition": self.disposition,
            "release": self.release,
            "reason": self.reason,
            "summary": self.summary,
            "entry": self.entry,
        }

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


#: Derived (A2.10) — never hand-kept — from :class:`HistoRecord`'s own field metadata:
#: every field except the three identity fields (``id``/``ts``/``disposition``).
_HISTO_RECORD_REDACTABLE_FIELDS: tuple[str, ...] = tuple(
    f.name for f in dc_fields(HistoRecord) if not f.metadata.get("identity")
)
