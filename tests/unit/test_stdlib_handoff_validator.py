"""Unit tests for StdlibHandoffValidator.

The verdict enum feeds the pre-push security gate — the MAYBE-rejected row is
preserved below alongside the accepted APPROVED/REJECTED/absent/reason cases.
"""

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


def test_minimal_and_full_valid_handoffs_return_empty() -> None:
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    assert list(validator.validate(_MINIMAL_VALID)) == []
    assert list(validator.validate(_FULL_VALID)) == []


@pytest.mark.parametrize(
    ("name", "doc_fn", "expect_field_fragment"),
    [
        (
            "missing_required_field",
            lambda: {k: v for k, v in _MINIMAL_VALID.items() if k != "agent"},
            "agent",
        ),
        ("wrong_type_agent", lambda: {**_MINIMAL_VALID, "agent": 42}, "agent"),
        (
            "invalid_produced_at",
            lambda: {**_MINIMAL_VALID, "produced_at": "not-a-date"},
            "produced_at",
        ),
        (
            "invalid_enum_severity",
            lambda: {
                **_MINIMAL_VALID,
                "findings": [{"severity": "BOGUS", "message": "whatever"}],
            },
            "severity",
        ),
        (
            "additional_properties_rejected",
            lambda: {**_MINIMAL_VALID, "unexpected_key": "oops"},
            "unexpected_key",
        ),
    ],
)
def test_validation_rejection_table(name: str, doc_fn: object, expect_field_fragment: str) -> None:
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = doc_fn()  # type: ignore[operator]
    errors = list(validator.validate(doc))
    assert len(errors) >= 1
    assert any(
        expect_field_fragment in e.field_path or expect_field_fragment in e.message for e in errors
    )


def test_error_message_includes_field_path() -> None:
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_MINIMAL_VALID, "agent": 999}
    errors = list(validator.validate(doc))
    assert errors, "expected at least one error"
    for error in errors:
        if "agent" in error.field_path:
            assert re.search(r"agent", str(error))
            break
    else:
        pytest.fail("No error about 'agent' field_path found")


def test_schema_load_failures_raise_handoff_schema_error(tmp_path: Path) -> None:
    bad_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "oneOf": [{"type": "string"}],  # unsupported keyword
    }
    schema_file = tmp_path / "bad.schema.json"
    schema_file.write_text(json.dumps(bad_schema))
    with pytest.raises(HandoffSchemaError, match="oneOf"):
        StdlibHandoffValidator(schema_file)

    missing = tmp_path / "nonexistent.schema.json"
    with pytest.raises(HandoffSchemaError, match="nonexistent"):
        StdlibHandoffValidator(missing)


# ---------------------------------------------------------------------------
# K-3 / AC-4 — handoff-v1.1 verdict field (panel-kanban-v1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "doc_fn", "expect_valid"),
    [
        ("verdict_approved", lambda: {**_MINIMAL_VALID, "verdict": "APPROVED"}, True),
        ("verdict_rejected", lambda: {**_MINIMAL_VALID, "verdict": "REJECTED"}, True),
        (
            # The verdict enum feeds the pre-push security gate — MAYBE must be
            # rejected.
            "verdict_maybe_rejected",
            lambda: {**_MINIMAL_VALID, "verdict": "MAYBE"},
            False,
        ),
        ("verdict_absent_backward_compat", lambda: dict(_MINIMAL_VALID), True),
        (
            "verdict_reason_accepted_alongside_verdict",
            lambda: {
                **_MINIMAL_VALID,
                "verdict": "APPROVED",
                "verdict_reason": "All acceptance criteria met.",
            },
            True,
        ),
    ],
)
def test_verdict_field_table(name: str, doc_fn: object, expect_valid: bool) -> None:
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = doc_fn()  # type: ignore[operator]
    errors = list(validator.validate(doc))
    if expect_valid:
        assert errors == [], f"Expected no errors but got: {errors}"
    else:
        assert len(errors) >= 1
        assert any("verdict" in e.field_path for e in errors)


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
