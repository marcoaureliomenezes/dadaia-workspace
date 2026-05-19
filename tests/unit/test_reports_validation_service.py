"""Unit tests for ReportsValidationService — 8 tests using FakeHandoffValidator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.core.exceptions import HandoffValidationError
from dadaia_workspace.features.reports_validation.service import (
    ReportsValidationService,
)
from tests.fakes import FakeHandoffValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_valid_handoff(path: Path, artifact_path_rel: str = "report.html") -> dict[str, object]:
    """Write a syntactically well-formed handoff JSON to ``path``."""
    doc: dict[str, object] = {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-16T23:29:05Z",
        "artifact": {
            "type": "report",
            "path": artifact_path_rel,
            "content_hash": "a" * 64,
        },
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return doc


# ---------------------------------------------------------------------------
# Test 1: happy path — valid handoff returns ValidationResult(valid=True)
# ---------------------------------------------------------------------------


def test_validate_file_happy_path(tmp_path: Path):
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)
    handoff_path = tmp_path / "my-report.handoff.json"
    _write_valid_handoff(handoff_path)

    result = service.validate_file(handoff_path)

    assert result.valid is True
    assert result.errors == ()
    assert len(fake.calls) == 1


# ---------------------------------------------------------------------------
# Test 2: malformed JSON → valid=False with malformed-JSON error
# ---------------------------------------------------------------------------


def test_validate_file_malformed_json(tmp_path: Path):
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)
    handoff_path = tmp_path / "bad.handoff.json"
    handoff_path.write_text("{not valid json", encoding="utf-8")

    result = service.validate_file(handoff_path)

    assert result.valid is False
    assert len(result.errors) >= 1
    assert "$root" in result.errors[0].field_path
    assert "malformed" in result.errors[0].message.lower()
    # Validator should NOT have been called with malformed content
    assert len(fake.calls) == 0


# ---------------------------------------------------------------------------
# Test 3: schema violation propagated from FakeHandoffValidator → valid=False
# ---------------------------------------------------------------------------


def test_validate_file_schema_violation_propagated(tmp_path: Path):
    violation = HandoffValidationError("agent", "required field missing")
    fake = FakeHandoffValidator(canned_errors=[violation])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)
    handoff_path = tmp_path / "violated.handoff.json"
    _write_valid_handoff(handoff_path)

    result = service.validate_file(handoff_path)

    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0].field_path == "agent"


# ---------------------------------------------------------------------------
# Test 4: validate_all discovers *.handoff.json recursively under root
# ---------------------------------------------------------------------------


def test_validate_all_discovers_recursively(tmp_path: Path):
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)

    # Create handoff files at different depths
    (tmp_path / "ctx-a").mkdir()
    (tmp_path / "ctx-a" / "agent1").mkdir()
    _write_valid_handoff(tmp_path / "ctx-a" / "agent1" / "r1.handoff.json")
    _write_valid_handoff(tmp_path / "ctx-a" / "agent1" / "r2.handoff.json")
    (tmp_path / "ctx-b").mkdir()
    (tmp_path / "ctx-b" / "agent2").mkdir()
    _write_valid_handoff(tmp_path / "ctx-b" / "agent2" / "r3.handoff.json")

    results = service.validate_all()

    assert len(results) == 3


# ---------------------------------------------------------------------------
# Test 5: validate_all with context= filter only returns matching subdir
# ---------------------------------------------------------------------------


def test_validate_all_context_filter(tmp_path: Path):
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)

    (tmp_path / "ctx-a").mkdir()
    (tmp_path / "ctx-a" / "se").mkdir()
    _write_valid_handoff(tmp_path / "ctx-a" / "se" / "r1.handoff.json")

    (tmp_path / "ctx-b").mkdir()
    (tmp_path / "ctx-b" / "pe").mkdir()
    _write_valid_handoff(tmp_path / "ctx-b" / "pe" / "r2.handoff.json")

    results = service.validate_all(context="ctx-a")

    assert len(results) == 1
    assert "ctx-a" in str(results[0].path)


# ---------------------------------------------------------------------------
# Test 6: check_hash returns "match" when artifact sha256 matches handoff's content_hash
# ---------------------------------------------------------------------------


def test_check_hash_returns_match(tmp_path: Path):
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)

    # Create artifact and compute its hash
    artifact = tmp_path / "report.html"
    artifact.write_bytes(b"<html>content</html>")
    actual_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()

    # Write handoff JSON referring to the artifact with the correct hash
    handoff_path = tmp_path / "report.handoff.json"
    doc: dict[str, object] = {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-16T23:29:05Z",
        "artifact": {
            "type": "report",
            "path": "report.html",
            "content_hash": actual_hash,
        },
    }
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")

    status = service.check_hash(handoff_path)
    assert status == "match"


# ---------------------------------------------------------------------------
# Test 7: check_hash returns "mismatch" when sha256 differs
# ---------------------------------------------------------------------------


def test_check_hash_returns_mismatch(tmp_path: Path):
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)

    artifact = tmp_path / "report.html"
    artifact.write_bytes(b"<html>original</html>")

    handoff_path = tmp_path / "report.handoff.json"
    doc: dict[str, object] = {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-16T23:29:05Z",
        "artifact": {
            "type": "report",
            "path": "report.html",
            "content_hash": "b" * 64,  # deliberately wrong hash
        },
    }
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")

    status = service.check_hash(handoff_path)
    assert status == "mismatch"


# ---------------------------------------------------------------------------
# Test 8: check_hash returns "missing_artifact" when sibling artifact does not exist
# ---------------------------------------------------------------------------


def test_check_hash_returns_missing_artifact(tmp_path: Path):
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)

    handoff_path = tmp_path / "report.handoff.json"
    doc: dict[str, object] = {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-16T23:29:05Z",
        "artifact": {
            "type": "report",
            "path": "nonexistent.html",  # no file here
            "content_hash": "a" * 64,
        },
    }
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")

    status = service.check_hash(handoff_path)
    assert status == "missing_artifact"
