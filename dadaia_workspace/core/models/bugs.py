"""Bug-event domain model for the event-sourced JSONL bug telemetry (v0.1.46 AC-1/AC-2).

Pure domain module — no I/O, no internal imports (stdlib only), so it lives in ``core`` as
the bottom layer that both ``infrastructure`` and ``features`` may depend on. A
:class:`BugEvent` is one append-only event in a ``specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl``
stream. The append-only store (``infrastructure/jsonl_bug_store.py``) and the ``dadaia
bugs`` CLI serialize these; the doctor coherence check folds them. Field set mirrors
``public/schemas/bugs/bug-event-v1.schema.json`` exactly.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

__all__ = [
    "TERMINAL_EVENTS",
    "BugEvent",
    "BugEventKind",
    "redact_text",
]


class BugEventKind(StrEnum):
    """The six event kinds. ``reported`` opens a stream; the four in
    :data:`TERMINAL_EVENTS` are terminal (at most one per ``bug_id``); ``archived`` is a
    NON-terminal annotation (defined-but-unemitted in v0.1.46)."""

    REPORTED = "reported"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    ARCHIVED = "archived"


#: The terminal set for event coherence (AC-1 decision). ``archived`` is deliberately NOT
#: here — it is a non-terminal annotation exempt from the double-terminal coherence rule.
TERMINAL_EVENTS: frozenset[str] = frozenset(
    {
        BugEventKind.RESOLVED.value,
        BugEventKind.SUPERSEDED.value,
        BugEventKind.DEFERRED.value,
        BugEventKind.REJECTED.value,
    }
)

#: Optional string payload fields (everything except ``tags``, which is a list).
_OPTIONAL_STR_FIELDS: tuple[str, ...] = (
    "title",
    "severity",
    "surface",
    "component",
    "context",
    "symptom",
    "repro",
    "expected",
    "notes",
    "release",
    "superseded_by",
    "reason",
    "evidence",
)

# Redaction patterns for `notes` (privacy rules): operator-local home paths + IPs never
# land in a committed bug event. The username segment of a home path is scrubbed; the IPv4
# form is masked wholesale. (A version token like v0.1.46 has only three numeric groups and
# is never matched.)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_POSIX_HOME_RE = re.compile(r"(/home/|/Users/)[^/\s:]+")
_WIN_HOME_RE = re.compile(r"([A-Za-z]:\\Users\\)[^\\\s:]+")


def redact_text(text: str) -> str:
    """Return ``text`` with operator-local home-path usernames and IPv4 addresses masked."""
    out = _IPV4_RE.sub("[REDACTED-IP]", text)
    out = _POSIX_HOME_RE.sub(r"\1[REDACTED]", out)
    out = _WIN_HOME_RE.sub(r"\1[REDACTED]", out)
    return out


def _require_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"bug event missing required string field {key!r}")
    return value


def _opt_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"bug event field {key!r} must be a string")
    return value


@dataclass(frozen=True)
class BugEvent:
    """One append-only bug-telemetry event. Field set mirrors ``bug-event-v1.schema.json``."""

    bug_id: str
    event: str
    ts: str
    reported_by: str
    title: str | None = None
    severity: str | None = None
    surface: str | None = None
    component: str | None = None
    context: str | None = None
    tags: tuple[str, ...] = ()
    symptom: str | None = None
    repro: str | None = None
    expected: str | None = None
    notes: str | None = None
    release: str | None = None
    superseded_by: str | None = None
    reason: str | None = None
    evidence: str | None = None

    @property
    def is_terminal(self) -> bool:
        """True iff this event is one of the terminal set (``archived`` is NOT terminal)."""
        return self.event in TERMINAL_EVENTS

    def redact(self) -> BugEvent:
        """Return a copy with every free-text field scrubbed of operator-local paths/IPs.

        ``title``, ``symptom``, ``repro``, ``expected``, ``notes`` and ``evidence`` are all operator-authored
        free text that can carry a home path or IP (CWE-532). Each is passed through
        :func:`redact_text`; unset fields are left as ``None``. Structured/enumerated fields
        (severity, component, release, …) are not free text and are left untouched.
        """

        def _scrub(value: str | None) -> str | None:
            return None if value is None else redact_text(value)

        return replace(
            self,
            title=_scrub(self.title),
            symptom=_scrub(self.symptom),
            repro=_scrub(self.repro),
            expected=_scrub(self.expected),
            notes=_scrub(self.notes),
            evidence=_scrub(self.evidence),
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape — only the set fields are emitted."""
        out: dict[str, object] = {
            "bug_id": self.bug_id,
            "event": self.event,
            "ts": self.ts,
            "reported_by": self.reported_by,
        }
        for name in _OPTIONAL_STR_FIELDS:
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        # `reported` always carries tags (the schema requires the array, even when empty);
        # other events carry it only when non-empty.
        if self.event == BugEventKind.REPORTED.value or self.tags:
            out["tags"] = list(self.tags)
        return out

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> BugEvent:
        """Parse a JSONL object into a :class:`BugEvent`. Raises ``ValueError`` on a
        malformed record (missing/typed-wrong required field) so tolerant readers can skip."""
        tags_raw = raw.get("tags", ())
        if isinstance(tags_raw, list | tuple):
            tags = tuple(str(t) for t in tags_raw)
        else:
            raise ValueError("bug event field 'tags' must be an array")
        return cls(
            bug_id=_require_str(raw, "bug_id"),
            event=_require_str(raw, "event"),
            ts=_require_str(raw, "ts"),
            reported_by=_require_str(raw, "reported_by"),
            title=_opt_str(raw, "title"),
            severity=_opt_str(raw, "severity"),
            surface=_opt_str(raw, "surface"),
            component=_opt_str(raw, "component"),
            context=_opt_str(raw, "context"),
            tags=tags,
            symptom=_opt_str(raw, "symptom"),
            repro=_opt_str(raw, "repro"),
            expected=_opt_str(raw, "expected"),
            notes=_opt_str(raw, "notes"),
            release=_opt_str(raw, "release"),
            superseded_by=_opt_str(raw, "superseded_by"),
            reason=_opt_str(raw, "reason"),
            evidence=_opt_str(raw, "evidence"),
        )
