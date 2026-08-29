"""Bug domain models — :class:`BugRecord`, the one-record-per-bug model.

Pure domain module — no I/O, no internal imports beyond ``dataclasses``/``enum``
(stdlib only) plus ONE sibling core module, ``core.redaction`` (the shared, also-pure
``redact_text``/``first_privacy_hit`` primitives both this model and
``core.models.backlog`` import — never each other). ``core/models/bugs.py`` is NOT in
``architecture.md``'s "Core file-I/O authorized set", so the model never reads a schema
file itself. :class:`BugRecord` is one line of ``specs/bugs/BUGS.jsonl``, appended once
(field set mirrors ``public/schemas/bugs/bug-record-v1.schema.json``, whose per-property
``x-mutability``/``x-redact`` keywords are the ONE documented source of the
three-category split — A2.1). It derives its optional/redactable field set from its OWN
``dataclasses.field(metadata=...)`` declarations (per-field, colocated, zero I/O) rather
than a second, separately-maintained module-level tuple (A2.10).

``BugEventKind``/:data:`TERMINAL_EVENTS` are the v5/v6 line-classifier's vocabulary
(:func:`~dadaia_workspace.core.bug_provenance.classify_ledger_line`, permanent by
necessity: git history is v5-shaped forever) and the closed set of terminal
``BugRecord.status`` values. A surviving ``"event"``-keyed v5 line in the v6 ledger
fails :meth:`BugRecord.from_dict` and surfaces as a single SPEC-DOC-033 ERROR, never a
folded diagnosis.

**Status transitions are the interface.** :meth:`BugRecord.resolve`/:meth:`supersede`/
:meth:`defer`/:meth:`reject` are the ONLY way a record reaches their respective terminal
status, each refusing (:class:`IncompleteTransitionError`) an incomplete/malformed call
before any field is set — status is UNREACHABLE without its own required fields, and
unreachable at all through :meth:`apply_governance_update` (a bare ``status`` change is
refused there; a transition method applies its evidence fields through that seam, then
sets ``status`` itself). A record that reached an incomplete terminal status before this
seam existed is never re-diagnosed: completeness is prospective, not retroactive.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from dataclasses import fields as dc_fields
from enum import StrEnum
from typing import Any

from dadaia_workspace.core.redaction import PatternLike, first_privacy_hit, redact_text

__all__ = [
    "TERMINAL_EVENTS",
    "BugEventKind",
    "BugRecord",
    "BugRecordImmutableFieldError",
    "BugRecordWriteOnceFieldSetError",
    "IncompleteTransitionError",
    "redact_text",
]


class BugEventKind(StrEnum):
    """The seven historical v5 event kinds — the closed vocabulary
    :func:`~dadaia_workspace.core.bug_provenance.classify_ledger_line` still decodes
    permanently (git history is v5-shaped forever). ``reported`` opens a stream; the
    four in :data:`TERMINAL_EVENTS` are terminal (at most one per ``bug_id``);
    ``archived``/``picked`` are non-terminal annotations."""

    REPORTED = "reported"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    PICKED = "picked"


#: The terminal set for event coherence. ``archived`` is deliberately NOT here — it is a
#: non-terminal annotation exempt from the double-terminal coherence rule. Reused as the
#: terminal ``BugRecord.status`` values ("resolved"/"superseded"/"deferred"/"rejected" —
#: the ``status`` enum's four non-"open" members, ``bug-record-v1.schema.json``) rather
#: than a second, independently-maintained constant: both ``features.bugs.service``
#: (archive eligibility) and ``features.specs.doctor_governance`` (the archive-overdue
#: WARN) import it from here, since neither may import the other
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


#: Case-insensitive substring denylist masking + control/format-char stripping +
#: IP/home-path scrubbing (SPEC v0.4.5 FR6/FR7, T-045-19) — the primitive itself
#: lives in ``core.redaction`` (relocated at the bug
#: ``backlog-histo-writer-skips-write-time-denylist-redaction`` fix: a SECOND
#: write-time record model, ``core.models.backlog.BacklogHistoRecord``, needed the
#: identical seam, and ``core/models/bugs.py`` must never import
#: ``core/models/backlog.py`` — both import this shared, domain-agnostic sibling
#: instead). Re-exported here, unchanged, for every existing caller of
#: ``dadaia_workspace.core.models.bugs.redact_text``.


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


class IncompleteTransitionError(ValueError):
    """Raised by a :class:`BugRecord` transition method (:meth:`resolve`,
    :meth:`supersede`, :meth:`defer`, :meth:`reject`) when the caller omits a field
    the target status requires, or supplies one that fails its own format rule
    (``evidence_diff``'s pattern, ``diff_direction``'s closed enum, or the three
    literal shapes an evidence field must never carry).

    The record is left COMPLETELY untouched on refusal — a transition method raises
    before ever calling :meth:`BugRecord.apply_governance_update`, so there is
    always a correction path: a caller who mistyped a value simply calls the
    transition again with the corrected one (closes bug
    ``bug-record-write-once-evidence-fields-can-embed-selfscan-triggering-literal-
    with-no-correction-path`` — the old failure mode was a write-once field that
    landed WITH the bad literal, refusing any second write to correct it; refusing
    AT the write means the bad literal never lands in the first place).
    """

    def __init__(self, verb: str, problems: Sequence[str]) -> None:
        joined = "; ".join(problems)
        super().__init__(
            f"bug-record transition {verb!r} refused — {joined} (the record is "
            "unchanged; call the transition again with corrected values)"
        )
        self.verb = verb
        self.problems = tuple(problems)


#: bug-record-v1.schema.json's ``evidence_diff`` pattern — restated here once, the
#: schema being the documented source (A2.1); this is the runtime mirror.
_EVIDENCE_DIFF_PATTERN_RE = re.compile(r"^(net-negative|net-positive|net-neutral):\s*\S.*$")

#: bug-record-v1.schema.json's ``diff_direction`` closed enum.
_DIFF_DIRECTIONS: frozenset[str] = frozenset({"net-negative", "net-neutral", "net-positive"})

#: bug-record-v1.schema.json's ``status`` closed enum (mirrors ``TERMINAL_EVENTS`` +
#: ``"open"`` — restated as its own set so :meth:`BugRecord.from_dict` can validate it
#: without constructing a throwaway ``BugEventKind`` mapping).
_STATUS_VALUES: frozenset[str] = frozenset({"open", *TERMINAL_EVENTS})


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
        for ``dadaia bugs update``, for the fixer's resolution write and the
        auditor's ``audited``/``resolved_commit`` write alike (A2.13 — one seam,
        every writer role).

        Refuses (:class:`BugRecordImmutableFieldError`) a CHANGE to an immutable-core
        field's value — re-asserting its current value is a harmless no-op (A2.2a).
        Refuses (:class:`BugRecordWriteOnceFieldSetError`) a second, DIFFERING write to
        a write-once field that is already set; setting it from absent (``None``)
        always succeeds (A2.2b). Refuses (``ValueError``) the key ``"status"`` outright
        — status changes only through :meth:`resolve`/:meth:`supersede`/:meth:`defer`/
        :meth:`reject`, each unreachable without its own required fields; a bare
        governance write can never reach a terminal status. Any OTHER governance field
        may be set freely.

        A2.7's own limit, stated here per A2.2's docstring requirement: this is
        SEAM-LEVEL enforcement only — any agent's file tool can still rewrite any
        field directly on disk; that is what the A2.7 doctor WARN / FR14 pillar-1
        finding DETECT, never prevent.
        """
        updates: dict[str, Any] = {}
        for key, value in changes.items():
            if key == "status":
                raise ValueError(
                    "bug-record field 'status' is unreachable through "
                    "apply_governance_update — use the matching transition instead: "
                    "resolve|supersede|defer|reject (status is unreachable without "
                    "its own required fields)"
                )
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

    def resolve(
        self,
        *,
        cause: str | None = None,
        caused_by: str | None = None,
        resolved_release: str | None = None,
        solution: str | None = None,
        evidence_loop: str | None = None,
        evidence_seam: str | None = None,
        evidence_diff: str | None = None,
        diff_direction: str | None = None,
        privacy_patterns: Sequence[PatternLike] = (),
    ) -> BugRecord:
        """The ONE way a record reaches ``status="resolved"``. Every keyword is
        REQUIRED (every problem is collected, not just the first); ``caused_by``
        must be an explicit string — the literal ``"none"`` declares "no known
        predecessor". ``evidence_loop``/``evidence_seam``/``evidence_diff`` are each
        checked against *privacy_patterns* (the operator's own baseline privacy
        patterns, threaded in by the caller — :func:`~dadaia_workspace.core.redaction
        .first_privacy_hit`); a hit refuses the whole call.

        Raises :class:`IncompleteTransitionError` naming every problem found; the
        record is left untouched on refusal. Applies its fields through
        :meth:`apply_governance_update` (write-once/immutable-core rules still
        enforced), then sets ``status`` itself — ``apply_governance_update`` refuses
        the key ``"status"``.
        """
        problems: list[str] = []
        values: dict[str, str] = {}
        for name, value in (
            ("cause", cause),
            ("caused_by", caused_by),
            ("resolved_release", resolved_release),
            ("solution", solution),
            ("evidence_loop", evidence_loop),
            ("evidence_seam", evidence_seam),
            ("evidence_diff", evidence_diff),
            ("diff_direction", diff_direction),
        ):
            if value is None or not value.strip():
                problems.append(f"{name!r} is required")
                continue
            values[name] = value

        if "evidence_diff" in values and not _EVIDENCE_DIFF_PATTERN_RE.match(
            values["evidence_diff"]
        ):
            problems.append(
                "'evidence_diff' must match "
                "'^(net-negative|net-positive|net-neutral): <rationale>' "
                "(bug-record-v1.schema.json)"
            )
        if "diff_direction" in values and values["diff_direction"] not in _DIFF_DIRECTIONS:
            problems.append(
                f"'diff_direction' must be one of {sorted(_DIFF_DIRECTIONS)}, got "
                f"{values['diff_direction']!r}"
            )
        for evidence_field in ("evidence_loop", "evidence_seam", "evidence_diff"):
            evidence_value = values.get(evidence_field)
            if evidence_value is None:
                continue
            hit = first_privacy_hit(evidence_value, privacy_patterns)
            if hit is not None:
                problems.append(f"{evidence_field!r} must not contain {hit}")

        if problems:
            raise IncompleteTransitionError("resolve", problems)

        updated = self.apply_governance_update(
            {
                "cause": values["cause"],
                "caused_by": values["caused_by"],
                "resolved_release": values["resolved_release"],
                "solution": values["solution"],
                "evidence_loop": values["evidence_loop"],
                "evidence_seam": values["evidence_seam"],
                "evidence_diff": values["evidence_diff"],
                "diff_direction": values["diff_direction"],
            }
        )
        return replace(updated, status="resolved")

    def supersede(
        self, *, by: str | None = None, privacy_patterns: Sequence[PatternLike] = ()
    ) -> BugRecord:
        """The ONE way a record reaches ``status="superseded"`` — *by* (the
        superseding backlog/bug/release slug) is REQUIRED and checked against
        *privacy_patterns* (see :meth:`resolve`)."""
        if by is None or not by.strip():
            raise IncompleteTransitionError("supersede", ["'by' is required"])
        hit = first_privacy_hit(by, privacy_patterns)
        if hit is not None:
            raise IncompleteTransitionError("supersede", [f"'by' must not contain {hit}"])
        updated = self.apply_governance_update({"superseded_by": by})
        return replace(updated, status="superseded")

    def defer(
        self, *, reason: str | None = None, privacy_patterns: Sequence[PatternLike] = ()
    ) -> BugRecord:
        """The ONE way a record reaches ``status="deferred"`` — *reason* is REQUIRED
        and checked against *privacy_patterns* (see :meth:`resolve`). Stored in
        ``cause`` — the schema's only generic mutable-governance narrative field,
        reused rather than a second, transition-only field for the same purpose."""
        if reason is None or not reason.strip():
            raise IncompleteTransitionError("defer", ["'reason' is required"])
        hit = first_privacy_hit(reason, privacy_patterns)
        if hit is not None:
            raise IncompleteTransitionError("defer", [f"'reason' must not contain {hit}"])
        updated = self.apply_governance_update({"cause": reason})
        return replace(updated, status="deferred")

    def reject(
        self, *, reason: str | None = None, privacy_patterns: Sequence[PatternLike] = ()
    ) -> BugRecord:
        """The ONE way a record reaches ``status="rejected"`` (same ``cause``-reuse
        rule as :meth:`defer`). *reason* is REQUIRED."""
        if reason is None or not reason.strip():
            raise IncompleteTransitionError("reject", ["'reason' is required"])
        hit = first_privacy_hit(reason, privacy_patterns)
        if hit is not None:
            raise IncompleteTransitionError("reject", [f"'reason' must not contain {hit}"])
        updated = self.apply_governance_update({"cause": reason})
        return replace(updated, status="rejected")

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
        malformed record (missing/typed-wrong required field, or a ``status`` outside
        the closed enum {open, resolved, superseded, deferred, rejected} —
        bug-record-v1.schema.json; v0.5.1 K5 deepening) so tolerant readers can skip
        it. This is the ONE record-level parser every reader (the record store, the
        service, the doctor) shares — never a second, hand-rolled field check."""
        status = _require_record_str(raw, "status")
        if status not in _STATUS_VALUES:
            raise ValueError(
                f"bug record field 'status' must be one of {sorted(_STATUS_VALUES)}, got {status!r}"
            )
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
            status=status,
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
