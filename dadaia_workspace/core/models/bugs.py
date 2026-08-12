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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

__all__ = [
    "TERMINAL_EVENTS",
    "BugCoherenceRecord",
    "BugCoherenceViolation",
    "BugEvent",
    "BugEventKind",
    "advance_coherence",
    "diagnose_bug_coherence_history",
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


def advance_coherence(
    bug_id: str,
    event: str,
    seen_reported: set[str],
    terminated: set[str],
) -> str | None:
    """Advance the one-terminal stream-coherence fold by a single event.

    THE single authority for the coherence invariant — every stream opens with
    ``reported``; an open stream carries at most one terminal; ``reported`` reopens. The
    specs doctor folds history through it to DIAGNOSE (SPEC-DOC-033) and
    ``BugService.append_event`` folds through it to REFUSE, so the diagnostic gate and
    the enforced gate can never diverge (v0.1.72 law).

    Mutates the fold state (*seen_reported*/*terminated*) in place; returns the
    violation clause for THIS event, or ``None`` when it is coherent. ``archived`` and
    any other non-terminal annotation always advance cleanly.
    """
    if event == BugEventKind.REPORTED.value:
        seen_reported.add(bug_id)
        terminated.discard(bug_id)  # a reopen clears the prior terminal state
        return None
    if event not in TERMINAL_EVENTS:
        return None
    if bug_id in terminated:
        return (
            f"bug '{bug_id}' has a second terminal event '{event}' after an existing "
            "terminal — a bug_id may carry at most one terminal"
        )
    terminated.add(bug_id)
    if bug_id not in seen_reported:
        return (
            f"terminal event '{event}' for bug '{bug_id}' with no prior 'reported' "
            "event — every stream must open with 'reported'"
        )
    return None


@dataclass(frozen=True)
class BugCoherenceRecord[P]:
    """One ``(bug_id, event)`` pair from a whole-history bug-event stream, tagged with an
    opaque *position* the caller supplies (e.g. ``(jsonl_path, lineno)``) purely so a
    returned violation can be traced back to its source line. The fold in
    :func:`diagnose_bug_coherence_history` never inspects *position* — it only round-trips
    it back onto the matching :class:`BugCoherenceViolation`.
    """

    bug_id: str
    event: str
    position: P


@dataclass(frozen=True)
class BugCoherenceViolation[P]:
    """One still-UNHEALED coherence violation surfaced by
    :func:`diagnose_bug_coherence_history`, carrying the offending record's *clause* (the
    exact text :func:`advance_coherence` produced) and its *position* back to the caller.
    """

    bug_id: str
    event: str
    clause: str
    position: P


def diagnose_bug_coherence_history[P](
    records: Sequence[BugCoherenceRecord[P]],
) -> list[BugCoherenceViolation[P]]:
    """Diagnose a WHOLE ``bug_id``/``event`` history for still-unhealed coherence
    violations — SPEC-DOC-033's diagnostic half, and the ONE place the healing rule
    lives (v0.5.0 FR2).

    Folds *records*, in order, through :func:`advance_coherence` — the SAME per-event
    authority ``BugService.append_event`` folds through to REFUSE an append — so a
    violation this function reports is always one the append path would also have
    refused, and vice versa (the v0.1.72 law: the diagnostic gate and the enforced gate
    can never diverge).

    **The healing rule.** A violation for ``bug_id`` is HEALED — dropped from the
    result — when a LATER ``reported`` event for the same ``bug_id`` exists anywhere
    after it in *records*. A later ``reported`` is the store's own append-only
    compensation vocabulary: it already clears the prior terminal state inside the fold
    (see the ``reported`` branch above, which discards *terminated*), so a history that
    reopens and re-terminates coherently is, as a whole, healed. A violation with no
    later ``reported`` for its ``bug_id`` — including a FRESH violation that occurs
    *after* a healing ``reported`` (a re-violation of an already-reopened stream) —
    has no later compensation and stays UNHEALED.

    This function only DIAGNOSES: it never mutates, reorders, or drops any record from
    the underlying append-only store — healing is a reporting decision, not a rewrite.
    Returned violations preserve the input order of *records*.
    """
    seen_reported: set[str] = set()
    terminated: set[str] = set()
    last_reported_index: dict[str, int] = {}
    raw_violations: list[tuple[int, BugCoherenceViolation[P]]] = []

    for index, record in enumerate(records):
        if record.event == BugEventKind.REPORTED.value:
            last_reported_index[record.bug_id] = index
        clause = advance_coherence(record.bug_id, record.event, seen_reported, terminated)
        if clause is not None:
            raw_violations.append(
                (
                    index,
                    BugCoherenceViolation(
                        bug_id=record.bug_id,
                        event=record.event,
                        clause=clause,
                        position=record.position,
                    ),
                )
            )

    return [
        violation
        for index, violation in raw_violations
        if last_reported_index.get(violation.bug_id, -1) <= index
    ]


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
