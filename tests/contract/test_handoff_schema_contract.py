"""Public handoff sidecar schema contracts."""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.stdlib_handoff_validator import StdlibHandoffValidator

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
    validator = StdlibHandoffValidator(_SCHEMA_PATH)

    assert list(validator.validate(_valid_handoff())) == []


def test_handoff_contract_rejects_missing_metrics() -> None:
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = _valid_handoff()
    doc.pop("metrics")

    errors = list(validator.validate(doc))

    assert errors
    assert any("metrics" in error.field_path or "metrics" in error.message for error in errors)


def test_handoff_contract_rejects_invalid_verdict() -> None:
    validator = StdlibHandoffValidator(_SCHEMA_PATH)
    doc = {**_valid_handoff(), "verdict": "MAYBE"}

    errors = list(validator.validate(doc))

    assert errors
    assert any("verdict" in error.field_path for error in errors)
