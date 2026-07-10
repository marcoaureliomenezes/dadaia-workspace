"""Unit tests for lifecycle handoff gate validators.

CRITICAL: the handoff gate validator — commit_sha exact-match (the push chokepoint keys on
it), severity threshold, and anti-substring matching.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from dadaia_workspace.core.models.lifecycle import (
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
)
from dadaia_workspace.features.lifecycle.gates import HandoffGateValidation, HandoffGateValidator

HASH = "a" * 64


def _handoff(**overrides: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "qa-engineer",
        "context": "dadaia-workspace",
        "release_id": "v0.1.15",
        "produced_at": "2026-06-18T12:00:00Z",
        "scope": "T-015-09",
        "metrics": {"commit_sha": "abc123", "task_group": "T-015-09"},
        "artifact": {
            "type": "report",
            "path": ".dadaia/reports/dadaia-workspace/qa/report.html",
            "content_hash": HASH,
        },
        "verdict": "APPROVED",
        "findings": [{"severity": "LOW", "message": "minor"}],
    }
    doc.update(overrides)
    return doc


def _requirement(**overrides: object) -> GateRequirement:
    kwargs: dict[str, object] = {
        "evidence_kind": GateEvidenceKind.HANDOFF,
        "required_agent": "qa-engineer",
        "required_verdict": GateVerdict.APPROVED,
        "release_id": "v0.1.15",
        "commit_sha": "abc123",
        "task_group": "T-015-09",
        "max_unresolved_severity": "MEDIUM",
    }
    kwargs.update(overrides)
    return GateRequirement(**kwargs)  # type: ignore[arg-type]


def _validate(
    handoff: dict[str, object],
    requirement: GateRequirement | None = None,
    *,
    artifact_hash: str | None = HASH,
    max_age_seconds: int | None = 600,
    age_seconds: int | None = 60,
) -> HandoffGateValidation:
    return HandoffGateValidator().validate(
        handoff,
        requirement or _requirement(),
        context="dadaia-workspace",
        release_id="v0.1.15",
        source=".dadaia/handoff/dadaia-workspace/qa.handoff.json",
        artifact_hash=artifact_hash,
        max_age_seconds=max_age_seconds,
        age_seconds=age_seconds,
    )


def test_approved_handoff_returns_structured_gate_evidence() -> None:
    result = _validate(_handoff())

    assert result.accepted is True
    assert result.reasons == ()
    assert result.evidence is not None
    assert result.evidence.evidence_kind is GateEvidenceKind.HANDOFF
    assert result.evidence.agent == "qa-engineer"
    assert result.evidence.context == "dadaia-workspace"
    assert result.evidence.release_id == "v0.1.15"
    assert result.evidence.verdict is GateVerdict.APPROVED
    assert result.evidence.commit_sha == "abc123"
    assert result.evidence.task_group == "T-015-09"


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda doc: doc.pop("artifact"), "malformed artifact"),
        (lambda doc: doc.pop("schema_version"), "malformed schema_version"),
        (lambda doc: doc.pop("produced_at"), "malformed produced_at"),
        (lambda doc: doc.pop("scope"), "malformed scope"),
        (lambda doc: doc.pop("metrics"), "malformed metrics"),
        (lambda doc: doc.update({"verdict": "MAYBE"}), "malformed verdict"),
        (
            lambda doc: doc.update({"artifact": {"content_hash": HASH}}),
            "malformed artifact type",
        ),
        (lambda doc: doc.update({"findings": "bad"}), "malformed findings"),
    ],
)
def test_rejects_malformed_handoff(
    mutate: Callable[[dict[str, object]], object],
    reason: str,
) -> None:
    doc = _handoff()
    mutate(doc)

    result = _validate(doc)

    assert result.accepted is False
    assert reason in result.reasons
    assert result.evidence is None


@pytest.mark.parametrize(
    ("handoff", "requirement", "reason"),
    [
        (_handoff(agent="security-reviewer"), None, "wrong agent"),
        (_handoff(context="other-context"), None, "wrong context"),
        (_handoff(release_id="v0.1.14"), None, "wrong release_id"),
        (_handoff(verdict="REJECTED"), None, "wrong verdict"),
        (
            _handoff(metrics={"commit_sha": "def456", "task_group": "T-015-09"}),
            None,
            "wrong commit_sha",
        ),
        (
            _handoff(metrics={"commit_sha": "abc123", "task_group": "T-015-09-extra"}),
            None,
            "wrong task_group",
        ),
        (
            _handoff(metrics={"commit_sha": "abc123-extra", "task_group": "T-015-09"}),
            None,
            "wrong commit_sha",
        ),
        (
            _handoff(agent="qa-engineer-extra"),
            None,
            "wrong agent",
        ),
    ],
)
def test_rejects_wrong_semantic_fields_without_substring_matching(
    handoff: dict[str, object],
    requirement: GateRequirement | None,
    reason: str,
) -> None:
    result = _validate(handoff, requirement)

    assert result.accepted is False
    assert reason in result.reasons


@pytest.mark.parametrize(
    ("handoff_overrides", "kwargs", "reason"),
    [
        ({}, {"age_seconds": 601}, "stale handoff"),
        ({}, {"artifact_hash": "b" * 64}, "artifact hash mismatch"),
        (
            {"findings": [{"severity": "HIGH", "message": "blocking issue"}]},
            {},
            "unresolved severity exceeds threshold",
        ),
    ],
    ids=["stale", "hash-mismatch", "severity-threshold"],
)
def test_rejects_staleness_hash_mismatch_and_severity_threshold(
    handoff_overrides: dict[str, object], kwargs: dict[str, object], reason: str
) -> None:
    result = _validate(_handoff(**handoff_overrides), **kwargs)  # type: ignore[arg-type]

    assert result.accepted is False
    assert reason in result.reasons
