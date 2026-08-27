"""Bug domain models — the event-sourced stream (v0.1.46 AC-1/AC-2) and, since v0.5.0
FR2, the one-record-per-bug replacement it is expanding into (D-F: expand -> switch ->
contract; T-050-07 is the 'expand' step — nothing on the executed path reads
:class:`BugRecord` yet).

Pure domain module — no I/O, no internal imports beyond ``dataclasses``/``enum``/``re``
(stdlib only): ``core/models/bugs.py`` is NOT in ``architecture.md``'s "Core file-I/O
authorized set", so neither model ever reads a schema file itself. A :class:`BugEvent`
is one append-only event in a ``specs/bugs/<YYYYMMDDTHH>Z-<n>.jsonl`` stream (field set
mirrors ``public/schemas/bugs/bug-event-v1.schema.json``); a :class:`BugRecord` is one
line of the future ``specs/bugs/BUGS.jsonl``, appended once (field set mirrors
``public/schemas/bugs/bug-record-v1.schema.json``, whose per-property ``x-mutability``/
``x-redact`` keywords are the ONE documented source of the three-category split —
A2.1). Both models derive their optional/redactable field sets from their OWN
``dataclasses.field(metadata=...)`` declarations (per-field, colocated, zero I/O) rather
than a second, separately-maintained module-level tuple — the exact hand-kept mirror
that twice missed a newly added free-text field (T-043-23 -> T-044-62) and that A2.10
now forbids outright. :func:`redactable_property_names` is the schema-mapping-side pure
counterpart, used to prove the two never drift (contract tests) and reusable by a future
model (``findings``/``backlog``) without depending on file I/O either.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from dataclasses import fields as dc_fields
from enum import StrEnum
from typing import Any

__all__ = [
    "TERMINAL_EVENTS",
    "BugCoherenceRecord",
    "BugCoherenceViolation",
    "BugEvent",
    "BugEventKind",
    "BugRecord",
    "BugRecordImmutableFieldError",
    "BugRecordWriteOnceFieldSetError",
    "advance_coherence",
    "diagnose_bug_coherence_history",
    "redact_text",
    "redactable_property_names",
]


class BugEventKind(StrEnum):
    """The seven event kinds. ``reported`` opens a stream; the four in
    :data:`TERMINAL_EVENTS` are terminal (at most one per ``bug_id``); ``archived`` is a
    NON-terminal annotation (defined-but-unemitted in v0.1.46); ``picked`` (v0.4.3
    T-043-18/FR14) is a NON-terminal, repeatable OBSERVABLE RESERVATION MARKER — never
    a lease (NO-LOCKS DOCTRINE): it grants nothing, expires never, blocks nothing. A
    repeated pick on the same open stream is allowed and surfaced, never refused; the
    only refusals are stream-integrity refusals (pick-after-terminal, pick before any
    ``reported``), never concurrency refusals — see :func:`advance_coherence`."""

    REPORTED = "reported"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    PICKED = "picked"


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

    ``picked`` (v0.4.3 T-043-18/FR14) is checked BEFORE the generic non-terminal
    early-return: it is a STREAM-INTEGRITY check, never a concurrency lock — a pick
    after a terminal event (the stream is closed) or before any ``reported`` (the
    stream was never opened) is incoherent, exactly like a terminal event would be.
    Coherent picks (including a REPEATED pick on the same open stream — NO-LOCKS: two
    visible picks is the sanctioned race outcome, never refused) mutate NEITHER
    *seen_reported* nor *terminated* — a pick is a marker, not a state transition.
    """
    if event == BugEventKind.REPORTED.value:
        seen_reported.add(bug_id)
        terminated.discard(bug_id)  # a reopen clears the prior terminal state
        return None
    if event == BugEventKind.PICKED.value:
        if bug_id in terminated:
            return (
                f"bug '{bug_id}' has a 'picked' event after an existing terminal — a "
                "pick is only valid on an open stream"
            )
        if bug_id not in seen_reported:
            return (
                f"'picked' event for bug '{bug_id}' with no prior 'reported' event — "
                "every stream must open with 'reported'"
            )
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


def _dataclass_field_names(
    dataclass_type: type, predicate: Callable[[Mapping[str, object]], bool]
) -> tuple[str, ...]:
    """Return the field names of *dataclass_type* whose ``metadata`` satisfies
    *predicate* — pure ``dataclasses.fields()`` introspection, zero file I/O.

    This is the ONE mechanism both :class:`BugEvent` and :class:`BugRecord` use to
    derive their optional/redactable/categorized field sets: a per-field
    ``dataclasses.field(metadata={...})`` entry, colocated with each field's own
    declaration, never a second, separately-maintained module-level tuple/list/set of
    names (A2.10) — adding a field to the dataclass is the only edit a new property
    ever needs; nothing here can "miss" it the way a hand-kept list twice did
    (T-043-23 -> T-044-62).
    """
    return tuple(f.name for f in dc_fields(dataclass_type) if predicate(f.metadata))


def redactable_property_names(schema: Mapping[str, object]) -> tuple[str, ...]:
    """Return every property of *schema* eligible for write-time redaction.

    Pure function of an EXPLICIT schema mapping — performs zero file I/O itself, so it
    is safe to call from ``core`` (which is not in ``architecture.md``'s core
    file-I/O authorized set). Loading the packaged ``bug-record-v1.schema.json`` file
    happens in ``infrastructure``/the container seam, or — as here — in a test, and is
    threaded in as data, exactly like ``denylist_terms`` already is (v0.4.5 FR6/
    T-045-19). A property qualifies when its declared ``type`` includes ``"string"``
    and it is not explicitly opted out via ``"x-redact": false`` (set on exactly
    ``id``/``ts``/``reported_by`` in ``bug-record-v1.schema.json`` — the record's
    stable identity fields). A schema fixture that adds a brand-new free-text
    property is picked up with NO code edited here (A2.6) — this function reads
    property names, never a hand-kept list of them.
    """
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError("schema has no 'properties' object")
    names: list[str] = []
    for name, spec in properties.items():
        if not isinstance(spec, Mapping):
            continue
        if spec.get("x-redact") is False:
            continue
        declared_type = spec.get("type")
        is_string_typed = declared_type == "string" or (
            isinstance(declared_type, list) and "string" in declared_type
        )
        if not is_string_typed:
            continue
        names.append(name)
    return tuple(names)


# Redaction patterns for `notes` (privacy rules): operator-local home paths + IPs never
# land in a committed bug event. The username segment of a home path is scrubbed; the IPv4
# form is masked wholesale. (A version token like v0.1.46 has only three numeric groups and
# is never matched.)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_POSIX_HOME_RE = re.compile(r"(/home/|/Users/)[^/\s:]+")
_WIN_HOME_RE = re.compile(r"([A-Za-z]:\\Users\\)[^\\\s:]+")

#: The C0/C1/DEL control range MINUS TAB (0x09), LF (0x0A) and CR (0x0D), plus the
#: Unicode LINE/PARAGRAPH SEPARATORS (U+2028/U+2029). Stripped — never escaped — FIRST
#: inside :func:`redact_text`, before any masking pass (v0.4.5 FR7/A7.3/A7.6, narrowed
#: by bug ``bug-event-sanitation-strips-tab-lf-cr-from-free-text``; bundles bug
#: ``bug-event-field-with-unicode-line-separator-silently-drops-the-event``).
#: ``JsonlBugStore.append_event`` serializes every field with ``json.dumps(...,
#: ensure_ascii=False)``, which already escapes the WHOLE C0/C1/DEL range as a JSON
#: string escape — a literal TAB/LF/CR inside a field value can never fragment a
#: JSONL line, because ``JsonlBugStore.iter_events`` splits the file on a literal
#: ``"\\n"`` character, never on ``str.splitlines()``'s wider terminator set (v0.4.5
#: FR7 read-side fix). TAB/LF/CR carry neither hazard this class exists to close and
#: must round-trip intact — deleting them only destroyed the word boundaries of every
#: multi-line free-text field (``repro``, ``evidence_loop``, ``evidence_seam``, …),
#: silently, on the live write path (bug
#: ``bug-event-sanitation-strips-tab-lf-cr-from-free-text``). What DOES still need
#: stripping: (a) U+0085/U+2028/U+2029 — the only bytes ``json.dumps`` leaves raw AND
#: a naive ``str.splitlines()``-style reader would treat as a terminator, the actual
#: fragmentation hazard (A7.1); (b) ESC and the rest of C0/C1/DEL — a raw ESC forges
#: an ANSI escape sequence or a fake second output line in any consumer that ever
#: decodes a folded :class:`BugEvent` back to a terminal (CWE-117, A7.2). Deleted
#: rather than escaped, unlike that precedent: a denylisted term an attacker
#: interrupts with one of these bytes must re-join into a contiguous substring for
#: the masking pass immediately below to still catch it (A7.6) — an escape sequence
#: (``"\\x1b"``) would leave the two halves apart.
_UNSAFE_FORMAT_CHARS_RE = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x80-\x9f\u2028\u2029]")


def redact_text(text: str, denylist_terms: Sequence[tuple[str, str]] = ()) -> str:
    """Return ``text`` with unsafe control/format characters stripped, then
    operator-local home-path usernames, IPv4 addresses, and any operator denylist term
    masked.

    The control/format strip (see :data:`_UNSAFE_FORMAT_CHARS_RE`) runs FIRST, before
    every masking pass (v0.4.5 FR7/A7.6) — so a denylisted term an attacker split with
    an embedded ESC or Unicode line/paragraph separator still gets matched below, and
    no such byte ever survives into a persisted field.

    ``denylist_terms`` is ``(term, reason)`` pairs from the SAME operator-term source
    the push-time scan already refuses on
    (``infrastructure.privacy_check.load_privacy_terms`` /
    ``features.chokepoints.denylist_scan.operator_terms_match``) — threaded in by the
    caller since this module is pure core and must never import ``infrastructure``
    (v0.4.5 FR6/T-045-19, `core-no-upper-layers`). Matched case-insensitively as a
    literal substring, mirroring the push-time scan's own semantics exactly (A6.3), so
    a term that would refuse a push is masked before it is ever committed. Defaults to
    ``()`` — a no-op for the denylist pass — so every pre-FR6 caller keeps masking
    IP/home paths; the control/format strip is unconditional and a no-op on clean text.
    """
    out = _UNSAFE_FORMAT_CHARS_RE.sub("", text)
    out = _IPV4_RE.sub("[REDACTED-IP]", out)
    out = _POSIX_HOME_RE.sub(r"\1[REDACTED]", out)
    out = _WIN_HOME_RE.sub(r"\1[REDACTED]", out)
    for term, _reason in denylist_terms:
        if term:
            out = re.sub(re.escape(term), "[REDACTED-TERM]", out, flags=re.IGNORECASE)
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
    title: str | None = field(default=None, metadata={"optional_str": True})
    severity: str | None = field(default=None, metadata={"optional_str": True})
    surface: str | None = field(default=None, metadata={"optional_str": True})
    component: str | None = field(default=None, metadata={"optional_str": True})
    context: str | None = field(default=None, metadata={"optional_str": True})
    tags: tuple[str, ...] = ()
    symptom: str | None = field(default=None, metadata={"optional_str": True})
    repro: str | None = field(default=None, metadata={"optional_str": True})
    expected: str | None = field(default=None, metadata={"optional_str": True})
    notes: str | None = field(default=None, metadata={"optional_str": True})
    release: str | None = field(default=None, metadata={"optional_str": True})
    superseded_by: str | None = field(default=None, metadata={"optional_str": True})
    reason: str | None = field(default=None, metadata={"optional_str": True})
    evidence: str | None = field(default=None, metadata={"optional_str": True})
    evidence_loop: str | None = field(default=None, metadata={"optional_str": True})
    evidence_seam: str | None = field(default=None, metadata={"optional_str": True})
    evidence_diff: str | None = field(default=None, metadata={"optional_str": True})

    @property
    def is_terminal(self) -> bool:
        """True iff this event is one of the terminal set (``archived`` is NOT terminal)."""
        return self.event in TERMINAL_EVENTS

    def redact(self, denylist_terms: Sequence[tuple[str, str]] = ()) -> BugEvent:
        """Return a copy with every optional string field scrubbed of operator-local
        paths/IPs and any operator denylist term, via :func:`redact_text`.

        The field set is derived from ``BugEvent``'s OWN ``dataclasses.field(metadata=
        {"optional_str": True})`` declarations (see :func:`_dataclass_field_names`) —
        never an independently hand-kept module-level tuple (SPEC v0.4.5 FR6/A6.5,
        carried forward at v0.5.0 A2.10; closes the T-043-23 -> T-044-62 chain, where a
        hand-kept list twice missed a newly added free-text field). ``denylist_terms``
        is the SAME operator-term source the push-time scan already refuses on,
        threaded in via the CLI/container composition seam since this module never
        imports ``infrastructure`` (`core-no-upper-layers`). Defaults to ``()`` so
        IP/home-path masking alone still runs for every caller.
        """

        def _scrub(value: str | None) -> str | None:
            return None if value is None else redact_text(value, denylist_terms)

        # `dataclasses.replace`'s mypy plugin cannot field-check a bare **dict
        # comprehension (it unifies every remaining field's type against the dict's
        # single inferred value type); an explicitly `Any`-typed local sidesteps that
        # without weakening `_scrub`'s own `str | None` signature above.
        updates: dict[str, Any] = {
            name: _scrub(getattr(self, name)) for name in _BUG_EVENT_OPTIONAL_STR_FIELDS
        }
        return replace(self, **updates)

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape — only the set fields are emitted."""
        out: dict[str, object] = {
            "bug_id": self.bug_id,
            "event": self.event,
            "ts": self.ts,
            "reported_by": self.reported_by,
        }
        for name in _BUG_EVENT_OPTIONAL_STR_FIELDS:
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
            evidence_loop=_opt_str(raw, "evidence_loop"),
            evidence_seam=_opt_str(raw, "evidence_seam"),
            evidence_diff=_opt_str(raw, "evidence_diff"),
        )


#: Derived (never hand-kept — A2.10), from ``BugEvent``'s own field metadata; reproduces
#: the exact 16-name/order set the retired ``_OPTIONAL_STR_FIELDS`` tuple held, since it
#: was itself originally hand-transcribed from ``bug-event-v1.schema.json``'s property
#: order — the source of truth is now this dataclass, not a copy of it.
_BUG_EVENT_OPTIONAL_STR_FIELDS: tuple[str, ...] = _dataclass_field_names(
    BugEvent, lambda metadata: bool(metadata.get("optional_str"))
)


# ============================================================================
# BugRecord — v0.5.0 FR2: one record per bug, immutable core, mutable governance.
# ============================================================================


class BugRecordImmutableFieldError(ValueError):
    """Raised by :meth:`BugRecord.apply_governance_update` when a change would alter
    an immutable-core field's value (A2.2a).

    Seam-level enforcement only, named in its own message per A2.7: any agent's file
    tool can still hand-edit any field directly on disk — that is what the A2.7
    ``specs doctor`` WARN and the FR14 pillar-1 finding DETECT, never prevent.
    """

    def __init__(self, field_name: str) -> None:
        super().__init__(
            f"bug-record field {field_name!r} is immutable-core and cannot be changed "
            "through the record-store update seam (A2.2a) — seam-level enforcement "
            "only; a file tool can still hand-edit it (A2.7 detects, never prevents)"
        )
        self.field_name = field_name


class BugRecordWriteOnceFieldSetError(ValueError):
    """Raised by :meth:`BugRecord.apply_governance_update` when a change would alter a
    write-once field that is already set to a DIFFERENT value (A2.2b).

    Re-applying the SAME value the field already holds is a no-op, not a violation —
    only a genuinely differing second write is refused.
    """

    def __init__(self, field_name: str) -> None:
        super().__init__(
            f"bug-record field {field_name!r} is write-once and already set — a "
            "second write with a different value is refused (A2.2b)"
        )
        self.field_name = field_name


def _require_record_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"bug record missing required string field {key!r}")
    return value


def _opt_record_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"bug record field {key!r} must be a string")
    return value


@dataclass(frozen=True)
class BugRecord:
    """One record per bug (v0.5.0 FR2, D11) — appended once, no event stream, no fold.

    Field set mirrors ``public/schemas/bugs/bug-record-v1.schema.json`` exactly. Every
    field's ``category`` metadata below (``"immutable-core"`` | ``"write-once"`` |
    ``"mutable-governance"``) reproduces that schema's per-property ``x-mutability``
    keyword — the schema is the documented source (A2.1); this dataclass is the
    zero-I/O runtime mirror a contract test keeps locked to it. THIS is the one place
    the categorization lives in Python: nothing here re-collects it into a second,
    independently-maintained module-level tuple/list/set of names (A2.10).

    ``status`` has NO ``picked`` value (v0.5.0 FR2) — the pick is the bundled
    definition commit (FR8 shape 5), not a status.
    """

    # -- Immutable core (required; refused when CHANGED through the update seam — A2.2a).
    id: str = field(metadata={"category": "immutable-core", "identity": True})
    ts: str = field(metadata={"category": "immutable-core", "identity": True})
    reported_by: str = field(metadata={"category": "immutable-core", "identity": True})
    title: str = field(metadata={"category": "immutable-core"})
    severity: str = field(metadata={"category": "immutable-core"})
    surface: str = field(metadata={"category": "immutable-core"})
    component: str = field(metadata={"category": "immutable-core"})
    context: str = field(metadata={"category": "immutable-core"})
    symptom: str = field(metadata={"category": "immutable-core"})
    repro: str = field(metadata={"category": "immutable-core"})
    expected: str = field(metadata={"category": "immutable-core"})
    # -- Mutable governance (required; present as null until set — v0.5.0 FR2).
    status: str = field(default="open", metadata={"category": "mutable-governance"})
    cause: str | None = field(default=None, metadata={"category": "mutable-governance"})
    caused_by: str | None = field(default=None, metadata={"category": "mutable-governance"})
    lineage_source: str | None = field(default=None, metadata={"category": "mutable-governance"})
    registration_commit: str | None = field(
        default=None, metadata={"category": "mutable-governance"}
    )
    registration_granularity: str | None = field(
        default=None, metadata={"category": "mutable-governance"}
    )
    resolved_commit: str | None = field(default=None, metadata={"category": "mutable-governance"})
    resolution_granularity: str | None = field(
        default=None, metadata={"category": "mutable-governance"}
    )
    resolved_release: str | None = field(default=None, metadata={"category": "mutable-governance"})
    audited: str | None = field(default=None, metadata={"category": "mutable-governance"})
    # -- Write-once, absent until set (A2.2b / A2.11 — the FR23 evidence triple restored).
    root_cause: str | None = field(default=None, metadata={"category": "write-once"})
    solution: str | None = field(default=None, metadata={"category": "write-once"})
    evidence_loop: str | None = field(default=None, metadata={"category": "write-once"})
    evidence_seam: str | None = field(default=None, metadata={"category": "write-once"})
    evidence_diff: str | None = field(default=None, metadata={"category": "write-once"})
    diff_direction: str | None = field(default=None, metadata={"category": "write-once"})
    superseded_by: str | None = field(default=None, metadata={"category": "write-once"})
    migration_note: str | None = field(default=None, metadata={"category": "write-once"})

    def apply_governance_update(self, changes: Mapping[str, object]) -> BugRecord:
        """Apply *changes*, returning a NEW record — the seam every writer of an
        EXISTING record goes through (registration is :meth:`from_dict`/the
        constructor, not this method). ``features/bugs/service.py`` wraps this call
        for ``dadaia bugs update`` (T-050-08/AS-16), for the fixer's resolution write
        and the auditor's ``audited``/``resolved_commit`` write alike (A2.13 — one
        seam, every writer role).

        Refuses (:class:`BugRecordImmutableFieldError`) a CHANGE to an immutable-core
        field's value — re-asserting its current value is a harmless no-op (A2.2a).
        Refuses (:class:`BugRecordWriteOnceFieldSetError`) a second, DIFFERING write to
        a write-once field that is already set; setting it from absent (``None``)
        always succeeds (A2.2b). A governance field may be set freely.

        A2.7's own limit, stated here per A2.2's docstring requirement: this is
        SEAM-LEVEL enforcement only — any agent's file tool can still rewrite any
        field directly on disk; that is what the A2.7 doctor WARN / FR14 pillar-1
        finding DETECT, never prevent.
        """
        updates: dict[str, Any] = {}
        for key, value in changes.items():
            if key in _BUG_RECORD_IMMUTABLE_CORE_FIELDS:
                if value != getattr(self, key):
                    raise BugRecordImmutableFieldError(key)
                continue
            if key in _BUG_RECORD_WRITE_ONCE_FIELDS:
                current = getattr(self, key)
                if current is not None and value != current:
                    raise BugRecordWriteOnceFieldSetError(key)
                updates[key] = value
                continue
            if key in _BUG_RECORD_GOVERNANCE_FIELDS:
                updates[key] = value
                continue
            raise ValueError(f"unknown bug-record field {key!r}")
        if not updates:
            return self
        return replace(self, **updates)

    def redact(self, denylist_terms: Sequence[tuple[str, str]] = ()) -> BugRecord:
        """Return a copy with every free-text field scrubbed via :func:`redact_text`.

        The field set is every declared field EXCEPT the three identity fields
        (``id``/``ts``/``reported_by``, marked ``metadata={"identity": True}`` on
        their OWN declarations above) — derived from THIS dataclass's own fields via
        :func:`_dataclass_field_names`, zero file I/O. A field added to
        :class:`BugRecord` is redacted by default with NO code edited here (A2.6/
        A2.10). The SAME set is documented, per property, by
        ``bug-record-v1.schema.json``'s ``x-redact`` keyword (``false`` on exactly
        ``id``/``ts``/``reported_by``); :func:`redactable_property_names` is the pure
        schema-mapping-side half of that same rule, cross-checked against this method's
        field set by a contract test so the two never drift.
        """

        def _scrub(value: str | None) -> str | None:
            return None if value is None else redact_text(value, denylist_terms)

        updates: dict[str, Any] = {
            name: _scrub(getattr(self, name)) for name in _BUG_RECORD_REDACTABLE_FIELDS
        }
        return replace(self, **updates)

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape.

        Immutable-core and mutable-governance fields are ALWAYS emitted (present as
        ``null`` until a governance field is set — v0.5.0 FR2); write-once fields are
        emitted only once set (legitimately absent from a freshly registered record).
        """
        out: dict[str, object] = {
            name: getattr(self, name)
            for name in (*_BUG_RECORD_IMMUTABLE_CORE_FIELDS, *_BUG_RECORD_GOVERNANCE_FIELDS)
        }
        for name in _BUG_RECORD_WRITE_ONCE_FIELDS:
            value = getattr(self, name)
            if value is not None:
                out[name] = value
        return out

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> BugRecord:
        """Parse a JSONL object into a :class:`BugRecord`. Raises ``ValueError`` on a
        malformed record (missing/typed-wrong required field) so tolerant readers can
        skip it (mirrors :meth:`BugEvent.from_dict`)."""
        return cls(
            id=_require_record_str(raw, "id"),
            ts=_require_record_str(raw, "ts"),
            reported_by=_require_record_str(raw, "reported_by"),
            title=_require_record_str(raw, "title"),
            severity=_require_record_str(raw, "severity"),
            surface=_require_record_str(raw, "surface"),
            component=_require_record_str(raw, "component"),
            context=_require_record_str(raw, "context"),
            symptom=_require_record_str(raw, "symptom"),
            repro=_require_record_str(raw, "repro"),
            expected=_require_record_str(raw, "expected"),
            status=_require_record_str(raw, "status"),
            cause=_opt_record_str(raw, "cause"),
            caused_by=_opt_record_str(raw, "caused_by"),
            lineage_source=_opt_record_str(raw, "lineage_source"),
            registration_commit=_opt_record_str(raw, "registration_commit"),
            registration_granularity=_opt_record_str(raw, "registration_granularity"),
            resolved_commit=_opt_record_str(raw, "resolved_commit"),
            resolution_granularity=_opt_record_str(raw, "resolution_granularity"),
            resolved_release=_opt_record_str(raw, "resolved_release"),
            audited=_opt_record_str(raw, "audited"),
            root_cause=_opt_record_str(raw, "root_cause"),
            solution=_opt_record_str(raw, "solution"),
            evidence_loop=_opt_record_str(raw, "evidence_loop"),
            evidence_seam=_opt_record_str(raw, "evidence_seam"),
            evidence_diff=_opt_record_str(raw, "evidence_diff"),
            diff_direction=_opt_record_str(raw, "diff_direction"),
            superseded_by=_opt_record_str(raw, "superseded_by"),
            migration_note=_opt_record_str(raw, "migration_note"),
        )


#: Derived (A2.10) — never hand-kept — from ``BugRecord``'s own field metadata.
_BUG_RECORD_IMMUTABLE_CORE_FIELDS: tuple[str, ...] = _dataclass_field_names(
    BugRecord, lambda metadata: metadata.get("category") == "immutable-core"
)
_BUG_RECORD_WRITE_ONCE_FIELDS: tuple[str, ...] = _dataclass_field_names(
    BugRecord, lambda metadata: metadata.get("category") == "write-once"
)
_BUG_RECORD_GOVERNANCE_FIELDS: tuple[str, ...] = _dataclass_field_names(
    BugRecord, lambda metadata: metadata.get("category") == "mutable-governance"
)
_BUG_RECORD_REDACTABLE_FIELDS: tuple[str, ...] = _dataclass_field_names(
    BugRecord, lambda metadata: not metadata.get("identity")
)
