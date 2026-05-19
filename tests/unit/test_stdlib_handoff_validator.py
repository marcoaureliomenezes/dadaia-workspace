"""Unit tests for StdlibHandoffValidator — 10 tests, TDD first-pass."""

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
        {"severity": "HIGH", "message": "Critical issue found"},
        {"severity": "INFO", "message": "All good"},
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
