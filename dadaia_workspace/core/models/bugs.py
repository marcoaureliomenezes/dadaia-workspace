"""Bug domain models — :class:`BugRecord`, the one-record-per-bug model (v0.5.0
FR2/T-050-08, D-F: expand -> switch -> contract).

Pure domain module — no I/O, no internal imports beyond ``dataclasses``/``enum``/``re``
(stdlib only): ``core/models/bugs.py`` is NOT in ``architecture.md``'s "Core file-I/O
authorized set", so the model never reads a schema file itself. :class:`BugRecord` is
one line of ``specs/bugs/BUGS.jsonl`` (the T-050-10 rename of the retired
``bugs.jsonl``), appended once (field set mirrors
``public/schemas/bugs/bug-record-v1.schema.json``, whose per-property ``x-mutability``/
``x-redact`` keywords are the ONE documented source of the three-category split —
A2.1). It derives its optional/redactable field set from its OWN
``dataclasses.field(metadata=...)`` declarations (per-field, colocated, zero I/O) rather
than a second, separately-maintained module-level tuple — the exact hand-kept mirror
that twice missed a newly added free-text field (T-043-23 -> T-044-62) and that A2.10
now forbids outright. :func:`redactable_property_names` is the schema-mapping-side pure
counterpart, used to prove the two never drift (contract tests) and reusable by a future
model (``findings``/``backlog``) without depending on file I/O either.

**``BugEvent`` and the v5 event-stream coherence fold are DELETED (v0.5.0 S1 FR23
firing, amendment A3, `specs/releases/0.5.0/reviews/S1-FR23-firing.md` §3).** SPEC FR2
and the earlier AR-1 ruling both said "the event fold and its state machine deleted";
they were not, at S1 firing time — ``BugEvent``, ``advance_coherence`` and the
``BugCoherenceRecord``/``BugCoherenceViolation``/``diagnose_bug_coherence_history`` v5
diagnostic survived here, consumed only by the doctor's now-retired v5 branch and the
migration adapter's now-retired fold, against a live ledger that carries **zero** v5
lines. They are gone; ``specs doctor`` now reports any surviving ``"event"``-keyed line
in the v6 ledger as a single SPEC-DOC-033 ERROR ("v5 line in a v6 ledger — migrate"),
never a folded diagnosis. :data:`BugEventKind`/:data:`TERMINAL_EVENTS` stay — they are
the v5/v6 line-classifier's vocabulary
(:func:`~dadaia_workspace.core.bug_provenance.classify_ledger_line`, permanent by
necessity: git history is v5-shaped forever) and the closed set of terminal
``BugRecord.status`` values.
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
    "BugEventKind",
    "BugRecord",
    "BugRecordImmutableFieldError",
    "BugRecordWriteOnceFieldSetError",
    "governance_completeness_gaps",
    "immutable_core_drift",
    "redact_text",
    "redactable_property_names",
]


class BugEventKind(StrEnum):
    """The seven historical v5 event kinds — the closed vocabulary
    :func:`~dadaia_workspace.core.bug_provenance.classify_ledger_line` still decodes
    permanently (git history is v5-shaped forever). ``reported`` opens a stream; the
    four in :data:`TERMINAL_EVENTS` are terminal (at most one per ``bug_id``);
    ``archived``/``picked`` are non-terminal annotations. The v5 write-side enforcement
    and diagnostic fold this enum once drove (``advance_coherence``,
    ``diagnose_bug_coherence_history``) are deleted (v0.5.0 S1 FR23 firing, A3) — the
    live ledger carries zero v5 lines, so nothing folds them anymore."""

    REPORTED = "reported"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    PICKED = "picked"


#: The terminal set for event coherence (AC-1 decision). ``archived`` is deliberately NOT
#: here — it is a non-terminal annotation exempt from the double-terminal coherence rule.
#:
#: v0.5.0 FR2/T-050-08 reuses this SAME string set as the terminal ``BugRecord.status``
#: values ("resolved"/"superseded"/"deferred"/"rejected" — the ``status`` enum's four
#: non-"open" members, ``bug-record-v1.schema.json``) rather than declaring a second,
#: independently-maintained constant: both ``features.bugs.service`` (archive
#: eligibility) and ``features.specs.doctor_governance`` (the archive-overdue WARN,
#: A2.8) import it from here, since neither may import the other
#: (`features-no-cross-feature`).
TERMINAL_EVENTS: frozenset[str] = frozenset(
    {
        BugEventKind.RESOLVED.value,
        BugEventKind.SUPERSEDED.value,
        BugEventKind.DEFERRED.value,
        BugEventKind.REJECTED.value,
    }
)

#: v0.5.0 FR2/A2.8 — the default age (days) at which a terminal ``BugRecord`` becomes
#: eligible for ``dadaia bugs archive`` and, if still live past it, trips the doctor's
#: overdue WARN. One shared constant so the CLI verb and the doctor check can never
#: drift apart on the threshold.
BUG_ARCHIVE_THRESHOLD_DAYS: int = 90


def _dataclass_field_names(
    dataclass_type: type, predicate: Callable[[Mapping[str, object]], bool]
) -> tuple[str, ...]:
    """Return the field names of *dataclass_type* whose ``metadata`` satisfies
    *predicate* — pure ``dataclasses.fields()`` introspection, zero file I/O.

    This is the ONE mechanism :class:`BugRecord` uses to
    derive its optional/redactable/categorized field sets: a per-field
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
#: decodes a folded :class:`BugRecord` back to a terminal (CWE-117, A7.2). Deleted
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
        skip it."""
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


# ============================================================================
# v0.5.0 T-050-08 (FR2 A2.3 / A2.7) — WARN-only diagnostics over a BugRecord.
#
# Both functions are pure and read only their own arguments (zero I/O — required for a
# `core` leaf); they exist here, not in `features/bugs` or `features/specs`, because
# BOTH `features.bugs.service.BugService` (``dadaia bugs status``) and
# `features.specs.doctor_governance.GovernanceValidator` (`specs doctor`) must render
# the SAME diagnosis and neither may import the other (`features-no-cross-feature`) —
# `core` is the one layer both already import. D15: coherence is DETECTED, never a
# block; every caller of these two functions renders a WARNING, never refuses a write
# or changes an exit code.
# ============================================================================


def governance_completeness_gaps(record: BugRecord) -> tuple[str, ...]:
    """A2.3 — the governance-completeness rule (SPEC FR2): reaching ``status:
    "resolved"`` without ``cause``/``caused_by``/``resolved_release``/``solution``, or
    ``status: "superseded"`` without ``superseded_by``, is a coherence GAP — surfaced as
    a WARNING by ``dadaia bugs status`` and ``specs doctor``, never a block (D15).

    Returns the sorted tuple of missing field names (empty when the record is complete
    for its own ``status``, or its ``status`` carries no completeness rule at all —
    ``open``/``deferred``/``rejected``).
    """
    if record.status == "resolved":
        return tuple(
            sorted(
                name
                for name, value in (
                    ("cause", record.cause),
                    ("caused_by", record.caused_by),
                    ("resolved_release", record.resolved_release),
                    ("solution", record.solution),
                )
                if not value
            )
        )
    if record.status == "superseded":
        return () if record.superseded_by else ("superseded_by",)
    return ()


def immutable_core_drift(record: BugRecord, baseline: BugRecord) -> tuple[str, ...]:
    """A2.7 — detect (never prevent) an immutable-core field that changed between
    *baseline* (the id's first-add snapshot) and *record* (the current on-disk value).

    Seam-level enforcement (``BugRecord.apply_governance_update``, A2.2a) already
    refuses a core-field CHANGE made through the record-store update seam; this
    function is the DETECTOR for the residual gap A2.2's own docstring names — any
    agent's file tool can still hand-edit a core field directly on disk, bypassing the
    seam entirely. ``baseline`` is an INJECTED snapshot (never derived here — this
    module holds no git access): until FR3/T-050-09's ``core.bug_provenance`` supplies
    a real git-derived first-add snapshot, every caller in this release passes an EMPTY
    baseline mapping, so the check is a genuine no-op in production (nothing to compare
    against) while staying provably correct here and at the two call sites' own fixture
    tests (fed a synthetic baseline directly). Returns ``()`` when *record* and
    *baseline* do not share an ``id``, or when nothing drifted.
    """
    if record.id != baseline.id:
        return ()
    return tuple(
        name
        for name in _BUG_RECORD_IMMUTABLE_CORE_FIELDS
        if getattr(record, name) != getattr(baseline, name)
    )
