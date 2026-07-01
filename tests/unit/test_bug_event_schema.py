"""Schema-file tests for the bug-event JSONL contract (v0.1.46 AC-1 / T-46-01).

Pins the static half: `bug-event-v1.schema.json` is a well-formed Draft 2020-12 JSON
Schema, a representative document of EACH event kind validates, and the rejection set —
missing required top-level field, bad `event` enum, and a `reported` event missing a
required payload field — all FAIL validation (not positive-only).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

_SCHEMAS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "schemas"


def _schema() -> dict[str, object]:
    return json.loads((_SCHEMAS / "bugs" / "bug-event-v1.schema.json").read_text(encoding="utf-8"))


def _reported() -> dict[str, object]:
    return {
        "bug_id": "gate-swallows-archive",
        "event": "reported",
        "ts": "2026-07-01T13:00:00Z",
        "reported_by": "software-engineer",
        "title": "gate classifies _archive as ADDITIVE",
        "severity": "HIGH",
        "surface": "gate_policy.classify_path",
        "component": "spec_context",
        "context": "dadaia-workspace",
        "tags": ["gate", "frozen"],
        "symptom": "specs/bugs/_archive/x resolves ADDITIVE",
        "repro": "classify_path('specs/bugs/_archive/x.jsonl')",
        "expected": "FROZEN",
        "notes": "found during v0.1.46",
    }


def _resolved() -> dict[str, object]:
    return {
        "bug_id": "gate-swallows-archive",
        "event": "resolved",
        "ts": "2026-07-01T14:00:00Z",
        "reported_by": "software-engineer",
        "release": "v0.1.46",
    }


def _superseded() -> dict[str, object]:
    return {
        "bug_id": "old-defect",
        "event": "superseded",
        "ts": "2026-07-01T14:00:00Z",
        "reported_by": "product-engineer",
        "superseded_by": "sdd-governance-v2-agents-lifecycle",
    }


def _deferred() -> dict[str, object]:
    return {
        "bug_id": "flaky-perf",
        "event": "deferred",
        "ts": "2026-07-01T14:00:00Z",
        "reported_by": "project-manager",
        "reason": "load-sensitive; not this cycle",
    }


def _rejected() -> dict[str, object]:
    return {
        "bug_id": "not-a-bug",
        "event": "rejected",
        "ts": "2026-07-01T14:00:00Z",
        "reported_by": "project-manager",
        "reason": "working as designed",
    }


def _archived() -> dict[str, object]:
    return {
        "bug_id": "legacy-closed",
        "event": "archived",
        "ts": "2026-07-01T14:00:00Z",
        "reported_by": "project-auditor",
    }


# --- schema is well-formed --------------------------------------------------------


def test_schema_is_well_formed() -> None:
    Draft202012Validator.check_schema(_schema())


def test_schema_id_is_scoped() -> None:
    assert _schema()["$id"] == "bug-event-v1"


# --- one valid document per event kind --------------------------------------------


@pytest.mark.parametrize(
    "doc",
    [_reported(), _resolved(), _superseded(), _deferred(), _rejected(), _archived()],
    ids=["reported", "resolved", "superseded", "deferred", "rejected", "archived"],
)
def test_each_event_kind_validates(doc: dict[str, object]) -> None:
    Draft202012Validator(_schema()).validate(doc)


def test_archived_needs_no_payload() -> None:
    """`archived` is a non-terminal annotation — the 4 top-level fields are enough."""
    doc = _archived()
    assert set(doc) == {"bug_id", "event", "ts", "reported_by"}
    Draft202012Validator(_schema()).validate(doc)


# --- rejection cases (not positive-only) ------------------------------------------


@pytest.mark.parametrize("field", ["bug_id", "event", "ts", "reported_by"])
def test_missing_required_top_level_field_fails(field: str) -> None:
    bad = _reported()
    del bad[field]
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


def test_bad_event_enum_fails() -> None:
    bad = _reported()
    bad["event"] = "closed"
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


@pytest.mark.parametrize(
    "field",
    [
        "title",
        "severity",
        "surface",
        "component",
        "context",
        "tags",
        "symptom",
        "repro",
        "expected",
        "notes",
    ],
)
def test_reported_missing_payload_field_fails(field: str) -> None:
    bad = _reported()
    del bad[field]
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


def test_resolved_missing_release_fails() -> None:
    bad = _resolved()
    del bad["release"]
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


def test_superseded_missing_superseded_by_fails() -> None:
    bad = _superseded()
    del bad["superseded_by"]
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


def test_deferred_missing_reason_fails() -> None:
    bad = _deferred()
    del bad["reason"]
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


def test_bad_severity_enum_fails() -> None:
    bad = _reported()
    bad["severity"] = "URGENT"
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


def test_unknown_top_level_property_fails() -> None:
    bad = _reported()
    bad["surprise"] = 1
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


def test_non_z_timestamp_fails() -> None:
    bad = _reported()
    bad["ts"] = "2026-07-01 13:00:00"
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)
