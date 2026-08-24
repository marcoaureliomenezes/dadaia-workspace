"""Schema-file tests for the bug-event JSONL contract (v0.1.46 AC-1 / T-46-01).

Pins the static half: `bug-event-v1.schema.json` is a well-formed Draft 2020-12 JSON
Schema, a representative document of EACH event kind validates, and the rejection set —
missing required top-level field, bad `event` enum, and a `reported` event missing a
required payload field — all FAIL validation (not positive-only). This contract backs
the bug-registration guardrail — rejection rows all survive below.
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


def _resolved_fr23() -> dict[str, object]:
    """v0.4.4 FR23 (T-044-62): a `resolved` event carrying the three new evidence
    fields — well-formed shape (see also ``test_resolved_fr23_evidence_fields_validate``
    and the CLI-level tests in ``test_bugs_resolution_evidence_fr23.py``)."""
    return {
        "bug_id": "gate-swallows-archive",
        "event": "resolved",
        "ts": "2026-07-01T14:00:00Z",
        "reported_by": "software-engineer",
        "release": "v0.1.46",
        "evidence_loop": "pytest tests/unit/test_bug_event_schema.py -q",
        "evidence_seam": "tests/unit/test_bug_event_schema.py::test_each_event_kind_validates",
        "evidence_diff": "net-negative: -3/+1 lines on the schema fixtures",
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


def _picked() -> dict[str, object]:
    """v0.4.3 FR14: the non-terminal, repeatable reservation marker."""
    return {
        "bug_id": "commit-paths-index-scope-hardening",
        "event": "picked",
        "ts": "2026-08-17T14:00:00Z",
        "reported_by": "software-engineer",
        "release": "v0.4.3",
    }


# --- one valid document per event kind --------------------------------------------


@pytest.mark.parametrize(
    "doc",
    [_reported(), _resolved(), _superseded(), _deferred(), _rejected(), _archived(), _picked()],
    ids=["reported", "resolved", "superseded", "deferred", "rejected", "archived", "picked"],
)
def test_each_event_kind_validates(doc: dict[str, object]) -> None:
    Draft202012Validator(_schema()).validate(doc)

    if doc.get("event") == "archived":
        # `archived` is a non-terminal annotation — the 4 top-level fields are enough.
        assert set(doc) == {"bug_id", "event", "ts", "reported_by"}
        # Schema well-formedness + scoped $id (checked once, piggybacked here).
        Draft202012Validator.check_schema(_schema())
        assert _schema()["$id"] == "bug-event-v1"


# --- rejection cases (not positive-only) — the guardrail's rejection rows ---------


@pytest.mark.parametrize(
    ("name", "mutate_fn"),
    [
        ("missing_bug_id", lambda d: d.__delitem__("bug_id")),
        ("missing_event", lambda d: d.__delitem__("event")),
        ("missing_ts", lambda d: d.__delitem__("ts")),
        ("missing_reported_by", lambda d: d.__delitem__("reported_by")),
        ("bad_event_enum", lambda d: d.__setitem__("event", "closed")),
        ("bad_severity_enum", lambda d: d.__setitem__("severity", "URGENT")),
        ("unknown_top_level_property", lambda d: d.__setitem__("surprise", 1)),
        ("non_z_timestamp", lambda d: d.__setitem__("ts", "2026-07-01 13:00:00")),
    ],
)
def test_reported_top_level_rejection_table(name: str, mutate_fn: object) -> None:
    bad = _reported()
    mutate_fn(bad)  # type: ignore[operator]
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


@pytest.mark.parametrize(
    ("name", "doc_fn", "missing_field"),
    [
        ("resolved_missing_release", _resolved, "release"),
        ("superseded_missing_superseded_by", _superseded, "superseded_by"),
        ("deferred_missing_reason", _deferred, "reason"),
        ("picked_missing_release", _picked, "release"),
    ],
)
def test_terminal_event_missing_required_field_fails(
    name: str, doc_fn: object, missing_field: str
) -> None:
    bad = doc_fn()  # type: ignore[operator]
    del bad[missing_field]
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)


# --- v0.4.4 FR23 (T-044-62): the resolved-evidence gate's schema half -------------


def test_resolved_fr23_evidence_fields_validate() -> None:
    """A well-formed `resolved` event carrying the three new evidence fields validates
    (A23.2: `bug-event-v1` declares the fields)."""
    Draft202012Validator(_schema()).validate(_resolved_fr23())


def test_historical_resolved_event_without_fr23_fields_still_validates() -> None:
    """A23.2/A23.6 (R-10): the ledger is append-only and no past event is rewritten —
    a `resolved` event from BEFORE FR23 (no `evidence_loop`/`evidence_seam`/
    `evidence_diff` at all, mirroring the 132/438 on-disk events with zero evidence)
    stays schema-valid untouched, exactly like ``_resolved()`` above."""
    historical = _resolved()
    assert "evidence_loop" not in historical
    assert "evidence_seam" not in historical
    assert "evidence_diff" not in historical
    Draft202012Validator(_schema()).validate(historical)


@pytest.mark.parametrize(
    ("name", "mutate_fn"),
    [
        ("evidence_loop_too_short", lambda d: d.__setitem__("evidence_loop", "hi")),
        ("evidence_seam_too_short", lambda d: d.__setitem__("evidence_seam", "hi")),
        (
            "evidence_diff_missing_direction_token",
            lambda d: d.__setitem__("evidence_diff", "removed a branch"),
        ),
        (
            "evidence_diff_bad_direction_token",
            lambda d: d.__setitem__("evidence_diff", "sideways: unclear"),
        ),
    ],
)
def test_resolved_fr23_evidence_field_rejection_table(name: str, mutate_fn: object) -> None:
    bad = _resolved_fr23()
    mutate_fn(bad)  # type: ignore[operator]
    with pytest.raises(ValidationError):
        Draft202012Validator(_schema()).validate(bad)
