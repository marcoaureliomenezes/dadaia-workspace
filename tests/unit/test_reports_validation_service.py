"""Unit tests for ReportsValidationService.

Content-hash integrity feeds the security-verdict PR gate (DADAIA.md §4;
`dd-gitflow-default`) — the artifact-path-outside-workspace rejection is CRIT and
kept standalone.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dadaia_workspace.core.exceptions import HandoffValidationError
from dadaia_workspace.features.reports.validation import (
    ReportsValidationService,
)
from tests.fakes import FakeHandoffValidator


def _write_valid_handoff(path: Path, artifact_path_rel: str = "report.html") -> dict[str, object]:
    """Write a syntactically well-formed handoff JSON to ``path``."""
    artifact_path = path.parent / artifact_path_rel
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(b"<html>report</html>")
    content_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    doc: dict[str, object] = {
        "schema_version": "handoff-v1",
        "agent": "software-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-05-16T23:29:05Z",
        "artifact": {
            "type": "report",
            "path": artifact_path_rel,
            "content_hash": content_hash,
        },
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return doc


def _doc_with_artifact(
    *,
    artifact_path: str | None,
    content_hash: str,
    agent: str = "software-engineer",
    context: str = "dadaia-workspace",
) -> dict[str, object]:
    artifact: dict[str, object] = {"type": "report", "content_hash": content_hash}
    if artifact_path is not None:
        artifact["path"] = artifact_path
    return {
        "schema_version": "handoff-v1",
        "agent": agent,
        "context": context,
        "produced_at": "2026-05-16T23:29:05Z",
        "artifact": artifact,
    }


# --- validate_file() — happy path / malformed JSON / schema violation ------------


def test_validate_file_table(tmp_path: Path) -> None:
    happy_fake = FakeHandoffValidator(canned_errors=[])
    happy_service = ReportsValidationService(validator=happy_fake, reports_root=tmp_path)
    happy_path = tmp_path / "my-report.handoff.json"
    _write_valid_handoff(happy_path)
    happy_result = happy_service.validate_file(happy_path)
    assert happy_result.valid is True
    assert happy_result.errors == ()
    assert happy_result.hash_status == "match"
    assert len(happy_fake.calls) == 1

    malformed_dir = tmp_path / "malformed"
    malformed_dir.mkdir()
    malformed_fake = FakeHandoffValidator(canned_errors=[])
    malformed_service = ReportsValidationService(
        validator=malformed_fake, reports_root=malformed_dir
    )
    malformed_path = malformed_dir / "bad.handoff.json"
    malformed_path.write_text("{not valid json", encoding="utf-8")
    malformed_result = malformed_service.validate_file(malformed_path)
    assert malformed_result.valid is False
    assert len(malformed_result.errors) >= 1
    assert "$root" in malformed_result.errors[0].field_path
    assert "malformed" in malformed_result.errors[0].message.lower()
    assert len(malformed_fake.calls) == 0  # not called with malformed content

    violation_dir = tmp_path / "violated"
    violation_dir.mkdir()
    violation = HandoffValidationError("agent", "required field missing")
    violation_fake = FakeHandoffValidator(canned_errors=[violation])
    violation_service = ReportsValidationService(
        validator=violation_fake, reports_root=violation_dir
    )
    violation_path = violation_dir / "violated.handoff.json"
    _write_valid_handoff(violation_path)
    violation_result = violation_service.validate_file(violation_path)
    assert violation_result.valid is False
    assert len(violation_result.errors) == 1
    assert violation_result.errors[0].field_path == "agent"


def test_validate_file_hash_mismatch_and_missing_artifact_path(tmp_path: Path) -> None:
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)

    mismatch_dir = tmp_path / "mismatch"
    mismatch_dir.mkdir()
    (mismatch_dir / "report.html").write_bytes(b"<html>changed</html>")
    mismatch_handoff = mismatch_dir / "report.handoff.json"
    mismatch_handoff.write_text(
        json.dumps(_doc_with_artifact(artifact_path="report.html", content_hash="b" * 64)),
        encoding="utf-8",
    )
    mismatch_result = service.validate_file(mismatch_handoff)
    assert mismatch_result.valid is False
    assert mismatch_result.hash_status == "mismatch"
    assert any("artifact hash check failed" in error.message for error in mismatch_result.errors)

    no_path_dir = tmp_path / "no-path"
    no_path_dir.mkdir()
    no_path_handoff = no_path_dir / "handoff.handoff.json"
    no_path_handoff.write_text(
        json.dumps(_doc_with_artifact(artifact_path=None, content_hash="b" * 64)), encoding="utf-8"
    )
    no_path_result = service.validate_file(no_path_handoff)
    assert no_path_result.valid is True
    assert no_path_result.hash_status is None


# --- validate_all() — recursive discovery + context filter -----------------------


def test_validate_all_recursive_and_context_filter(tmp_path: Path) -> None:
    fake = FakeHandoffValidator(canned_errors=[])
    service = ReportsValidationService(validator=fake, reports_root=tmp_path)

    (tmp_path / "ctx-a").mkdir()
    (tmp_path / "ctx-a" / "agent1").mkdir()
    _write_valid_handoff(tmp_path / "ctx-a" / "agent1" / "r1.handoff.json")
    _write_valid_handoff(tmp_path / "ctx-a" / "agent1" / "r2.handoff.json")
    (tmp_path / "ctx-b").mkdir()
    (tmp_path / "ctx-b" / "agent2").mkdir()
    _write_valid_handoff(tmp_path / "ctx-b" / "agent2" / "r3.handoff.json")

    all_results = service.validate_all()
    assert len(all_results) == 3

    filtered_results = service.validate_all(context="ctx-a")
    assert len(filtered_results) == 2
    assert all("ctx-a" in str(r.path) for r in filtered_results)


# --- check_hash() — match / mismatch / missing-artifact / workspace-relative -----


def test_check_hash_table(tmp_path: Path) -> None:
    fake = FakeHandoffValidator(canned_errors=[])

    match_dir = tmp_path / "match"
    match_dir.mkdir()
    match_service = ReportsValidationService(validator=fake, reports_root=match_dir)
    artifact = match_dir / "report.html"
    artifact.write_bytes(b"<html>content</html>")
    actual_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    match_handoff = match_dir / "report.handoff.json"
    match_handoff.write_text(
        json.dumps(_doc_with_artifact(artifact_path="report.html", content_hash=actual_hash)),
        encoding="utf-8",
    )
    assert match_service.check_hash(match_handoff) == "match"

    mismatch_dir = tmp_path / "mismatch2"
    mismatch_dir.mkdir()
    mismatch_service = ReportsValidationService(validator=fake, reports_root=mismatch_dir)
    (mismatch_dir / "report.html").write_bytes(b"<html>original</html>")
    mismatch_handoff = mismatch_dir / "report.handoff.json"
    mismatch_handoff.write_text(
        json.dumps(_doc_with_artifact(artifact_path="report.html", content_hash="b" * 64)),
        encoding="utf-8",
    )
    assert mismatch_service.check_hash(mismatch_handoff) == "mismatch"

    missing_dir = tmp_path / "missing"
    missing_dir.mkdir()
    missing_service = ReportsValidationService(validator=fake, reports_root=missing_dir)
    missing_handoff = missing_dir / "report.handoff.json"
    missing_handoff.write_text(
        json.dumps(_doc_with_artifact(artifact_path="nonexistent.html", content_hash="a" * 64)),
        encoding="utf-8",
    )
    assert missing_service.check_hash(missing_handoff) == "missing_artifact"

    # Workspace-relative artifact.path resolution (a report path composed relative to
    # the workspace root, not the handoff's own directory).
    handoff_root = tmp_path / ".dadaia" / "handoff"
    handoff_root.mkdir(parents=True)
    relative_service = ReportsValidationService(validator=fake, reports_root=handoff_root)

    artifact = tmp_path / ".dadaia" / "reports" / "dadaia-workspace" / "qa-engineer" / "report.html"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"<html>canonical report</html>")
    actual_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()

    handoff_path = handoff_root / "dadaia-workspace" / "2026-06-04T000000Z-qa-report.handoff.json"
    handoff_path.parent.mkdir()
    doc: dict[str, object] = {
        "schema_version": "handoff-v1",
        "agent": "qa-engineer",
        "context": "dadaia-workspace",
        "produced_at": "2026-06-04T00:00:00Z",
        "artifact": {
            "type": "report",
            "path": ".dadaia/reports/dadaia-workspace/qa-engineer/report.html",
            "content_hash": actual_hash,
        },
    }
    handoff_path.write_text(json.dumps(doc), encoding="utf-8")

    assert relative_service.check_hash(handoff_path) == "match"


def test_check_hash_rejects_artifact_path_outside_workspace(tmp_path: Path) -> None:
    """CRIT traversal guard: an artifact path outside the workspace root must never
    resolve — it is treated as a missing artifact, never followed."""
    fake = FakeHandoffValidator(canned_errors=[])
    handoff_root = tmp_path / ".dadaia" / "handoff"
    handoff_root.mkdir(parents=True)
    service = ReportsValidationService(validator=fake, reports_root=handoff_root)

    outside = tmp_path.parent / "outside-report.html"
    outside.write_bytes(b"outside")
    try:
        handoff_path = handoff_root / "ctx" / "2026-06-04T000000Z-qa-report.handoff.json"
        handoff_path.parent.mkdir()
        doc: dict[str, object] = {
            "schema_version": "handoff-v1",
            "agent": "qa-engineer",
            "context": "ctx",
            "produced_at": "2026-06-04T00:00:00Z",
            "artifact": {
                "type": "report",
                "path": str(outside),
                "content_hash": hashlib.sha256(outside.read_bytes()).hexdigest(),
            },
        }
        handoff_path.write_text(json.dumps(doc), encoding="utf-8")

        assert service.check_hash(handoff_path) == "missing_artifact"
    finally:
        outside.unlink(missing_ok=True)
