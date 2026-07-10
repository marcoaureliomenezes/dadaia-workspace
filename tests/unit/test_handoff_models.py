"""Unit tests for dadaia_workspace.core.models.handoff — HandoffDocument dataclasses.

Frozen-instance immutability is covered by the shared param sweep in
``tests/unit/core/models/test_workflow_execution.py::test_all_models_are_frozen``.
"""

import pytest

from dadaia_workspace.core.models.handoff import (
    ArtifactRef,
    ArtifactType,
    HandoffDocument,
    Severity,
)

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


def test_handoff_document_from_dict_minimal_full_and_next_handoff_optional() -> None:
    minimal = HandoffDocument.from_dict(MINIMAL_DATA)
    assert minimal.schema_version == "handoff-v1"
    assert minimal.agent == "software-engineer"
    assert minimal.context == "dadaia-workspace"
    assert minimal.produced_at == "2026-05-16T23:29:05Z"
    assert isinstance(minimal.artifact, ArtifactRef)
    assert minimal.artifact.type == ArtifactType.report
    assert (
        minimal.artifact.path
        == ".dadaia/reports/dadaia-workspace/software-engineer/2026-05-16T232905Z.html"
    )
    assert (
        minimal.artifact.content_hash
        == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    # Optional fields default; next_handoff defaults to None absent the key.
    assert minimal.release_id is None
    assert minimal.findings == ()
    assert minimal.decisions_required == ()
    assert minimal.next_handoff is None

    full = HandoffDocument.from_dict(FULL_DATA)
    assert full.release_id == "agent-comms-v1"
    assert len(full.findings) == 2
    assert full.findings[0].severity == Severity.HIGH
    assert full.findings[0].message == "Validator does not support oneOf."
    assert full.findings[1].severity == Severity.LOW
    assert len(full.decisions_required) == 1
    assert full.decisions_required[0] == "Operator must confirm flip of ACTIVE.md."
    assert full.next_handoff is not None
    assert full.next_handoff.agent == "product-engineer"
    assert full.next_handoff.context == "dadaia-workspace"
    assert full.next_handoff.expected_artifact_type == ArtifactType.spec


@pytest.mark.parametrize(
    ("type_value", "expected_enum"),
    [
        ("report", ArtifactType.report),
        ("spec", ArtifactType.spec),
        ("plan", ArtifactType.plan),
        ("tasks", ArtifactType.tasks),
        ("closure", ArtifactType.closure),
        ("memory", ArtifactType.memory),
        ("other", ArtifactType.other),
    ],
)
def test_artifact_ref_type_stored(type_value: str, expected_enum: ArtifactType) -> None:
    data = {**MINIMAL_DATA, "artifact": {**MINIMAL_DATA["artifact"], "type": type_value}}  # type: ignore[arg-type]
    doc = HandoffDocument.from_dict(data)
    assert doc.artifact.type == expected_enum


@pytest.mark.parametrize(
    ("sev_value", "expected_enum"),
    [
        ("CRITICAL", Severity.CRITICAL),
        ("HIGH", Severity.HIGH),
        ("MEDIUM", Severity.MEDIUM),
        ("LOW", Severity.LOW),
        ("INFO", Severity.INFO),
    ],
)
def test_finding_severity_stored(sev_value: str, expected_enum: Severity) -> None:
    data = {
        **MINIMAL_DATA,
        "findings": [{"severity": sev_value, "message": "test msg"}],
    }
    doc = HandoffDocument.from_dict(data)
    assert doc.findings[0].severity == expected_enum
