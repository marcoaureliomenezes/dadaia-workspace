"""Unit tests for dadaia_workspace.core.models.handoff — HandoffDocument dataclasses."""

import dataclasses

import pytest

from dadaia_workspace.core.models.handoff import (
    ArtifactRef,
    ArtifactType,
    Finding,
    HandoffDocument,
    NextHandoff,
    Severity,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_DATA: dict[str, object] = {
    "schema_version": "handoff-v1",
    "agent": "software-engineer",
    "context": "dadaia-workspace",
    "produced_at": "2026-05-16T23:29:05Z",
    "artifact": {
        "type": "report",
        "path": ".dadaia/reports/dadaia-workspace/software-engineer/2026-05-16T232905Z.html",
        "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    },
}

FULL_DATA: dict[str, object] = {
    "schema_version": "handoff-v1",
    "agent": "software-engineer",
    "context": "dadaia-workspace",
    "produced_at": "2026-05-16T23:29:05Z",
    "artifact": {
        "type": "report",
        "path": ".dadaia/reports/dadaia-workspace/software-engineer/2026-05-16T232905Z.html",
        "content_hash": "a3f1b2c9d4e5f6071819202122232425262728293031323334353637383940410a",
    },
    "release_id": "agent-comms-v1",
    "findings": [
        {"severity": "HIGH", "message": "Validator does not support oneOf."},
        {"severity": "LOW", "message": "Container grows but acceptable."},
    ],
    "decisions_required": ["Operator must confirm flip of ACTIVE.md."],
    "next_handoff": {
        "agent": "product-engineer",
        "context": "dadaia-workspace",
        "expected_artifact_type": "spec",
    },
}


# ---------------------------------------------------------------------------
# Test 1 — minimal required-only parses correctly
# ---------------------------------------------------------------------------


def test_handoff_document_from_dict_minimal() -> None:
    doc = HandoffDocument.from_dict(MINIMAL_DATA)

    assert doc.schema_version == "handoff-v1"
    assert doc.agent == "software-engineer"
    assert doc.context == "dadaia-workspace"
    assert doc.produced_at == "2026-05-16T23:29:05Z"
    assert isinstance(doc.artifact, ArtifactRef)
    assert doc.artifact.type == ArtifactType.report
    assert doc.artifact.path == ".dadaia/reports/dadaia-workspace/software-engineer/2026-05-16T232905Z.html"
    assert doc.artifact.content_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    # Optional fields default
    assert doc.release_id is None
    assert doc.findings == ()
    assert doc.decisions_required == ()
    assert doc.next_handoff is None


# ---------------------------------------------------------------------------
# Test 2 — full parse with all optional fields
# ---------------------------------------------------------------------------


def test_handoff_document_from_dict_full() -> None:
    doc = HandoffDocument.from_dict(FULL_DATA)

    assert doc.release_id == "agent-comms-v1"
    assert len(doc.findings) == 2
    assert doc.findings[0].severity == Severity.HIGH
    assert doc.findings[0].message == "Validator does not support oneOf."
    assert doc.findings[1].severity == Severity.LOW
    assert len(doc.decisions_required) == 1
    assert doc.decisions_required[0] == "Operator must confirm flip of ACTIVE.md."
    assert doc.next_handoff is not None
    assert doc.next_handoff.agent == "product-engineer"
    assert doc.next_handoff.context == "dadaia-workspace"
    assert doc.next_handoff.expected_artifact_type == ArtifactType.spec


# ---------------------------------------------------------------------------
# Test 3 — dataclass is frozen (assigning raises FrozenInstanceError)
# ---------------------------------------------------------------------------


def test_handoff_document_frozen() -> None:
    doc = HandoffDocument.from_dict(MINIMAL_DATA)

    with pytest.raises(dataclasses.FrozenInstanceError):
        doc.agent = "other-agent"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Test 4 — ArtifactType round-trips (from_dict then .artifact.type enum)
# ---------------------------------------------------------------------------


def test_artifact_ref_type_stored() -> None:
    for type_value, expected_enum in [
        ("report", ArtifactType.report),
        ("spec", ArtifactType.spec),
        ("plan", ArtifactType.plan),
        ("tasks", ArtifactType.tasks),
        ("closure", ArtifactType.closure),
        ("memory", ArtifactType.memory),
        ("other", ArtifactType.other),
    ]:
        data = {**MINIMAL_DATA, "artifact": {**MINIMAL_DATA["artifact"], "type": type_value}}  # type: ignore[arg-type]
        doc = HandoffDocument.from_dict(data)
        assert doc.artifact.type == expected_enum


# ---------------------------------------------------------------------------
# Test 5 — Severity round-trips
# ---------------------------------------------------------------------------


def test_finding_severity_stored() -> None:
    for sev_value, expected_enum in [
        ("CRITICAL", Severity.CRITICAL),
        ("HIGH", Severity.HIGH),
        ("MEDIUM", Severity.MEDIUM),
        ("LOW", Severity.LOW),
        ("INFO", Severity.INFO),
    ]:
        data = {
            **MINIMAL_DATA,
            "findings": [{"severity": sev_value, "message": "test msg"}],
        }
        doc = HandoffDocument.from_dict(data)
        assert doc.findings[0].severity == expected_enum


# ---------------------------------------------------------------------------
# Test 6 — next_handoff optional defaults to None
# ---------------------------------------------------------------------------


def test_next_handoff_optional_none() -> None:
    doc = HandoffDocument.from_dict(MINIMAL_DATA)

    assert doc.next_handoff is None
