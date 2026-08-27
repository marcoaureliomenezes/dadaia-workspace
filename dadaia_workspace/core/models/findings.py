"""Audit-finding domain model — :class:`FindingRecord`, the one-record-per-finding model
(v0.5.0 FR13, D5, D11).

Pure domain module — no I/O, no internal imports beyond ``dataclasses``/``collections.abc``
(stdlib only): ``core/models/findings.py`` is NOT in ``architecture.md``'s "Core file-I/O
authorized set", so the model never reads a schema file itself. :class:`FindingRecord` is
one line of ``specs/audits/<YYYYMMDDTHHMMSSZ>-<session_id_8chars>/FINDINGS.jsonl``,
appended once (field set mirrors
``public/schemas/audits/finding-record-v1.schema.json``, whose per-property
``x-mutability`` keyword is the ONE documented source of the two-category split — A13.1,
mirrors A2.1). It derives its category field sets from its OWN
``dataclasses.field(metadata=...)`` declarations (per-field, colocated, zero I/O) rather
than a second, separately-maintained module-level tuple — the exact hand-kept mirror
A2.10 forbids (the shape that twice missed a newly added free-text field on
:class:`~dadaia_workspace.core.models.bugs.BugRecord`, T-043-23 -> T-044-62).

**No store instance is registered for this model in ``container.py`` at this fold
(A13.4).** ``specs/audits/**`` has no CLI writer (D15/A14.5) — ``project-auditor`` and the
remediation closure both append/rewrite ``FINDINGS.jsonl`` with file tools, never through
a code seam — so a ``build_findings_store`` composition-root function would have zero
call sites: "a registration with no caller is dead code behind a protocol" (A13.4, fold
3, `software-architect` §6). The generic
``infrastructure.jsonl_record_store.JsonlRecordStore`` already accepts this model's
``to_dict``/``from_dict`` pair unchanged the moment a real consumer needs one (FR15's
doctor fold, or a later writer) — that registration lands in the task that adds the
call site, not here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from dataclasses import fields as dc_fields
from typing import Any

__all__ = [
    "FindingRecord",
    "FindingRecordImmutableFieldError",
]


def _dataclass_field_names(
    dataclass_type: type, predicate: Callable[[Mapping[str, object]], bool]
) -> tuple[str, ...]:
    """Return the field names of *dataclass_type* whose ``metadata`` satisfies
    *predicate* — pure ``dataclasses.fields()`` introspection, zero file I/O.

    This is the ONE mechanism :class:`FindingRecord` uses to derive its immutable-core /
    mutable-governance field sets: a per-field ``dataclasses.field(metadata={...})``
    entry, colocated with each field's own declaration, never a second, separately-
    maintained module-level tuple/list/set of names (A2.10/A13.1) — adding a field to
    the dataclass is the only edit a new property ever needs.
    """
    return tuple(f.name for f in dc_fields(dataclass_type) if predicate(f.metadata))


class FindingRecordImmutableFieldError(ValueError):
    """Raised by :meth:`FindingRecord.apply_governance_update` when a change would
    alter an immutable-core field's value (mirrors ``BugRecordImmutableFieldError``,
    A2.2a).

    Seam-level enforcement only: any agent's file tool can still hand-edit any field
    directly on disk — that is what a future doctor check would DETECT, never prevent.
    """

    def __init__(self, field_name: str) -> None:
        super().__init__(
            f"finding-record field {field_name!r} is immutable-core and cannot be "
            "changed through the record-store update seam — seam-level enforcement "
            "only; a file tool can still hand-edit it"
        )
        self.field_name = field_name


def _require_finding_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"finding record missing required string field {key!r}")
    return value


def _optional_finding_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"finding record field {key!r} must be a string")
    return value


def _require_finding_refs(raw: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ValueError(f"finding record field {key!r} must be an array of strings")
    refs = tuple(value)
    if not refs or not all(isinstance(item, str) and item for item in refs):
        raise ValueError(f"finding record field {key!r} must be a non-empty array of strings")
    return refs


@dataclass(frozen=True)
class FindingRecord:
    """One record per audit finding (v0.5.0 FR13, D5, D11) — appended once, no event
    stream, no fold.

    Field set mirrors ``public/schemas/audits/finding-record-v1.schema.json`` exactly.
    Every field's ``category`` metadata below (``"immutable-core"`` |
    ``"mutable-governance"``) reproduces that schema's per-property ``x-mutability``
    keyword — the schema is the documented source (A13.1); this dataclass is the
    zero-I/O runtime mirror a contract test keeps locked to it. THIS is the one place
    the categorization lives in Python: nothing here re-collects it into a second,
    independently-maintained module-level tuple/list/set of names (A2.10).

    Unlike :class:`~dadaia_workspace.core.models.bugs.BugRecord`, there is no
    write-once category: a finding's evidence is authored complete at append time
    (A13.5) and only its three governance fields are ever rewritten, in place, by the
    remediation release that dispositions it.
    """

    # -- Immutable core (required; refused when CHANGED through the update seam).
    id: str = field(metadata={"category": "immutable-core", "identity": True})
    pillar: str = field(metadata={"category": "immutable-core"})
    severity: str = field(metadata={"category": "immutable-core"})
    refs: tuple[str, ...] = field(metadata={"category": "immutable-core"})
    claim: str = field(metadata={"category": "immutable-core"})
    evidence: str = field(metadata={"category": "immutable-core"})
    # -- Mutable governance (required; present as `open`/null until dispositioned).
    disposition: str = field(default="open", metadata={"category": "mutable-governance"})
    release: str | None = field(default=None, metadata={"category": "mutable-governance"})
    reason: str | None = field(default=None, metadata={"category": "mutable-governance"})

    def apply_governance_update(self, changes: Mapping[str, object]) -> FindingRecord:
        """Apply *changes*, returning a NEW record — the seam a remediation-release
        writer (or ``project-auditor``'s own file-tool rewrite) goes through
        conceptually when it dispositions this finding.

        Refuses (:class:`FindingRecordImmutableFieldError`) a CHANGE to an
        immutable-core field's value — re-asserting its current value is a harmless
        no-op. A governance field (``disposition``/``release``/``reason``) may be set
        freely, any number of times.
        """
        updates: dict[str, Any] = {}
        for key, value in changes.items():
            if key in _FINDING_RECORD_IMMUTABLE_CORE_FIELDS:
                if value != getattr(self, key):
                    raise FindingRecordImmutableFieldError(key)
                continue
            if key in _FINDING_RECORD_GOVERNANCE_FIELDS:
                updates[key] = value
                continue
            raise ValueError(f"unknown finding-record field {key!r}")
        if not updates:
            return self
        return replace(self, **updates)

    def to_dict(self) -> dict[str, object]:
        """Serialize to the JSONL object shape. Every field is ALWAYS emitted (the
        governance fields present as ``"open"``/``null`` until dispositioned)."""
        return {
            "id": self.id,
            "pillar": self.pillar,
            "severity": self.severity,
            "refs": list(self.refs),
            "claim": self.claim,
            "evidence": self.evidence,
            "disposition": self.disposition,
            "release": self.release,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, object]) -> FindingRecord:
        """Parse a JSONL object into a :class:`FindingRecord`. Raises ``ValueError`` on
        a malformed record (missing/typed-wrong required field) so tolerant readers can
        skip it."""
        return cls(
            id=_require_finding_str(raw, "id"),
            pillar=_require_finding_str(raw, "pillar"),
            severity=_require_finding_str(raw, "severity"),
            refs=_require_finding_refs(raw, "refs"),
            claim=_require_finding_str(raw, "claim"),
            evidence=_require_finding_str(raw, "evidence"),
            disposition=_require_finding_str(raw, "disposition"),
            release=_optional_finding_str(raw, "release"),
            reason=_optional_finding_str(raw, "reason"),
        )


#: Derived (A2.10) — never hand-kept — from ``FindingRecord``'s own field metadata.
_FINDING_RECORD_IMMUTABLE_CORE_FIELDS: tuple[str, ...] = _dataclass_field_names(
    FindingRecord, lambda metadata: metadata.get("category") == "immutable-core"
)
_FINDING_RECORD_GOVERNANCE_FIELDS: tuple[str, ...] = _dataclass_field_names(
    FindingRecord, lambda metadata: metadata.get("category") == "mutable-governance"
)
