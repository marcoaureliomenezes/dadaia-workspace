"""Unit tests for StdlibHandoffValidator."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import HandoffSchemaError
from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator

# ---------------------------------------------------------------------------
# Path to the real schema
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_SCHEMA_PATH = _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "handoff-v1.schema.json"


# ---------------------------------------------------------------------------
# Minimal valid handoff fixture
# ---------------------------------------------------------------------------

_MINIMAL_VALID: dict[str, object] = {
    "schema_version": "handoff-v1",
    "agent": "software-engineer",
    "context": "dadaia-workspace",
    "produced_at": "2026-05-16T23:29:05Z",
    "scope": "dadaia-workspace/agent-comms-v1",
    "metrics": {"files_changed": 3, "tests_added": 10},
    "artifact": {
        "type": "report",
        "path": "reports/se-report.html",
        "content_hash": "a" * 64,
    },
}

_FULL_VALID: dict[str, object] = {
    **_MINIMAL_VALID,
    "release_id": "agent-comms-v1",
    "findings": [
        {
            "severity": "HIGH",
            "message": "Critical issue found",
            "detail_md": "Extended detail on the critical issue.",
            "fix_recommendation": "Fix the critical issue immediately.",
        },
        {
            "severity": "INFO",
            "message": "All good",
            "detail_md": "No action needed.",
            "fix_recommendation": "No action required.",
        },
    ],
    "decisions_required": ["Decide on schema v2"],
    "next_handoff": {
        "agent": "qa-engineer",
        "context": "dadaia-workspace",
        "expected_artifact_type": "report",
    },
}


# ---------------------------------------------------------------------------
# Test 1: minimal valid handoff returns empty list
# ---------------------------------------------------------------------------


def test_minimal_valid_handoff_returns_empty():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    errors = validator.validate(_MINIMAL_VALID)
    assert list(errors) == []


# ---------------------------------------------------------------------------
# Test 2: full valid handoff (all optional fields) returns empty
# ---------------------------------------------------------------------------


def test_full_valid_handoff_returns_empty():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    errors = validator.validate(_FULL_VALID)
    assert list(errors) == []


# ---------------------------------------------------------------------------
# Test 3: missing required field → error with field_path pointing to the missing field
# ---------------------------------------------------------------------------


def test_missing_required_field_produces_error():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {k: v for k, v in _MINIMAL_VALID.items() if k != "agent"}
    errors = list(validator.validate(doc))
    assert len(errors) >= 1
    field_paths = [e.field_path for e in errors]
    assert any("agent" in fp for fp in field_paths)


# ---------------------------------------------------------------------------
# Test 4: wrong type for `agent` (int instead of str) → error
# ---------------------------------------------------------------------------


def test_wrong_type_agent_produces_error():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "agent": 42}
    errors = list(validator.validate(doc))
    assert len(errors) >= 1
    assert any("agent" in e.field_path for e in errors)


# ---------------------------------------------------------------------------
# Test 5: invalid `produced_at` (not ISO 8601) → error
# ---------------------------------------------------------------------------


def test_invalid_produced_at_produces_error():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "produced_at": "not-a-date"}
    errors = list(validator.validate(doc))
    assert len(errors) >= 1
    assert any("produced_at" in e.field_path for e in errors)


# ---------------------------------------------------------------------------
# Test 6: invalid enum (severity = "BOGUS") → error
# ---------------------------------------------------------------------------


def test_invalid_enum_severity_produces_error():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {
        **_MINIMAL_VALID,
        "findings": [{"severity": "BOGUS", "message": "whatever"}],
    }
    errors = list(validator.validate(doc))
    assert len(errors) >= 1
    assert any("severity" in e.field_path for e in errors)


# ---------------------------------------------------------------------------
# Test 7: additionalProperties rejected (extra root key) → error
# ---------------------------------------------------------------------------


def test_additional_properties_rejected():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "unexpected_key": "oops"}
    errors = list(validator.validate(doc))
    assert len(errors) >= 1
    assert any("unexpected_key" in e.message or "unexpected_key" in e.field_path for e in errors)


# ---------------------------------------------------------------------------
# Test 8: schema with unsupported keyword raises HandoffSchemaError in __init__
# ---------------------------------------------------------------------------


def test_unsupported_keyword_in_schema_raises_at_init(tmp_path: Path):
    bad_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "oneOf": [{"type": "string"}],  # unsupported keyword
    }
    schema_file = tmp_path / "bad.schema.json"
    schema_file.write_text(json.dumps(bad_schema))
    with pytest.raises(HandoffSchemaError, match="oneOf"):
        StdlibHandoffValidator(schema_file)


# ---------------------------------------------------------------------------
# Test 9: schema file missing → raises HandoffSchemaError
# ---------------------------------------------------------------------------


def test_missing_schema_file_raises_handoff_schema_error(tmp_path: Path):
    missing = tmp_path / "nonexistent.schema.json"
    with pytest.raises(HandoffSchemaError, match="nonexistent"):
        StdlibHandoffValidator(missing)


# ---------------------------------------------------------------------------
# Test 10: error message includes the field path
# ---------------------------------------------------------------------------


def test_error_message_includes_field_path():
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "agent": 999}
    errors = list(validator.validate(doc))
    assert errors, "expected at least one error"
    # Each HandoffValidationError's str representation embeds the field path
    for error in errors:
        if "agent" in error.field_path:
            assert re.search(r"agent", str(error))
            break
    else:
        pytest.fail("No error about 'agent' field_path found")


# ---------------------------------------------------------------------------
# K-3 / AC-4 — handoff-v1.1 verdict field (panel-kanban-v1)
# ---------------------------------------------------------------------------


# AC-4.1: schema accepts verdict: "APPROVED"
def test_verdict_approved_is_accepted() -> None:
    """AC-4.1 — verdict: 'APPROVED' validates without errors."""
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "verdict": "APPROVED"}
    errors = list(validator.validate(doc))
    assert errors == [], f"Expected no errors but got: {errors}"


# AC-4.1: schema accepts verdict: "REJECTED"
def test_verdict_rejected_is_accepted() -> None:
    """AC-4.1 — verdict: 'REJECTED' validates without errors."""
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "verdict": "REJECTED"}
    errors = list(validator.validate(doc))
    assert errors == [], f"Expected no errors but got: {errors}"


# AC-4.1: schema rejects verdict: "MAYBE" (enum enforced)
def test_verdict_invalid_value_rejected() -> None:
    """AC-4.1 — verdict: 'MAYBE' must be rejected (enum constraint)."""
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "verdict": "MAYBE"}
    errors = list(validator.validate(doc))
    assert len(errors) >= 1, "Expected at least one error for verdict='MAYBE'"
    assert any("verdict" in e.field_path for e in errors), (
        f"Expected error on 'verdict' field_path; got: {[e.field_path for e in errors]}"
    )


# AC-4.2: existing sidecar without verdict still validates (backward compat)
def test_verdict_absent_still_validates() -> None:
    """AC-4.2 — sidecar without 'verdict' field validates (field is optional)."""
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    # _MINIMAL_VALID has no 'verdict' key — this is the backward-compat case
    assert "verdict" not in _MINIMAL_VALID
    errors = list(validator.validate(_MINIMAL_VALID))
    assert errors == [], f"Expected no errors for sidecar without verdict; got: {errors}"


# AC-4.3: verdict_reason string is accepted alongside verdict
def test_verdict_reason_string_accepted() -> None:
    """AC-4.3 adjacent — verdict_reason is optional string, validated when present."""
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {
        **_MINIMAL_VALID,
        "verdict": "APPROVED",
        "verdict_reason": "All acceptance criteria met.",
    }
    errors = list(validator.validate(doc))
    assert errors == [], f"Expected no errors but got: {errors}"


# AC-4.3: StdlibHandoffValidator with real schema accepts v1.1 sidecar with verdict APPROVED
def test_stdlib_validator_accepts_v1_1_sidecar_with_verdict() -> None:
    """AC-4.3 — StdlibHandoffValidator exits cleanly (no errors) on a v1.1 sidecar
    containing verdict: 'APPROVED', mirroring what dadaia reports validate does."""
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    sidecar: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "qa-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-31T10:00:00Z",
        "scope": "dadaia-workspace/panel-kanban-v1",
        "metrics": {"tests_run": 5, "tests_passed": 5},
        "artifact": {
            "type": "report",
            "content_hash": "a" * 64,
        },
        "verdict": "APPROVED",
        "verdict_reason": "All Playwright board scenarios passed.",
    }
    errors = list(validator.validate(sidecar))
    assert errors == [], (
        f"Expected no validation errors on v1.1 sidecar with verdict=APPROVED; got: {errors}"
    )
