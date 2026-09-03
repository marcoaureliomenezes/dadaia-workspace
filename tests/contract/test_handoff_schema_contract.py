"""Intent: CONTRACT — handoff-v1.schema.json (DADAIA §5.4 validation)

Public handoff sidecar schema contracts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.handoff_index import load_schema, validate_schema_shape

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _REPO_ROOT / "dadaia_workspace" / "public" / "schemas" / "handoff-v1.schema.json"


def _valid_handoff() -> dict[str, object]:
    return {
        "schema_version": "handoff-v1.1",
        "agent": "code-reviewer",
        "context": "dadaia-workspace",
        "produced_at": "2026-06-03T12:00:00Z",
        "scope": "dadaia-workspace/tests",
        "metrics": {"files_changed": 2, "tests_added": 1},
        "artifact": {
            "type": "report",
            "path": ".dadaia/reports/dadaia-workspace/code-reviewer/report.html",
            "content_hash": "a" * 64,
        },
        "findings": [
            {
                "severity": "HIGH",
                "message": "Suite has stale implementation tests.",
                "detail_md": "Tests assert deleted implementation details instead of current contracts.",
                "fix_recommendation": "Delete stale tests and promote behavior contracts.",
            }
        ],
        "verdict": "APPROVED",
        "verdict_reason": "Contract is valid.",
    }


def test_handoff_v1_1_accepts_current_required_contract() -> None:
    schema = load_schema(_SCHEMA_PATH)

    assert validate_schema_shape(_valid_handoff(), schema) == []


def _missing_metrics() -> dict[str, object]:
    doc = _valid_handoff()
    doc.pop("metrics")
    return doc


def _invalid_verdict() -> dict[str, object]:
    return {**_valid_handoff(), "verdict": "MAYBE"}


def _traversal_path(path: str) -> dict[str, object]:
    doc = _valid_handoff()
    artifact = dict(doc["artifact"])  # type: ignore[arg-type]
    artifact["path"] = path
    doc["artifact"] = artifact
    return doc


@pytest.mark.parametrize(
    ("doc", "expected_field"),
    [
        pytest.param(_missing_metrics(), "metrics", id="missing-metrics"),
        pytest.param(_invalid_verdict(), "verdict", id="invalid-verdict"),
        pytest.param(_traversal_path("/etc/passwd"), None, id="absolute-path"),
        pytest.param(_traversal_path("../report.html"), None, id="parent-traversal"),
        pytest.param(
            _traversal_path(".dadaia/reports/../states/private.json"),
            None,
            id="embedded-parent-traversal",
        ),
    ],
)
def test_handoff_contract_rejects_invalid_documents(
    doc: dict[str, object], expected_field: str | None
) -> None:
    schema = load_schema(_SCHEMA_PATH)

    errors = validate_schema_shape(doc, schema)

    assert errors
    if expected_field is not None:
        assert any(
            expected_field in error.field_path or expected_field in error.message
            for error in errors
        )
