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


# ---------------------------------------------------------------------------
# Relocated from tests/integration/test_lifecycle_review_gates.py (T-7, v0.1.75):
# pure in-process HandoffGateValidator.validate() matrix — no subprocess/server/fs,
# so it belongs in the unit tier. Coverage preserved verbatim.
# ---------------------------------------------------------------------------


def _multi_agent_handoff(
    *,
    agent: str,
    context: str = "dadaia-workspace",
    release_id: str = "v0.1.15",
    verdict: str = "APPROVED",
    commit_sha: str = "abc123",
    task_group: str = "rc-1",
    findings: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "handoff-v1.1",
        "agent": agent,
        "context": context,
        "release_id": release_id,
        "produced_at": "2026-06-18T12:00:00Z",
        "scope": task_group,
        "metrics": {"commit_sha": commit_sha, "task_group": task_group},
        "artifact": {
            "type": "report",
            "path": f".dadaia/reports/dadaia-workspace/{agent}/review.html",
            "content_hash": HASH,
        },
        "verdict": verdict,
        "findings": findings or [],
    }


def _multi_agent_requirement(
    *,
    agent: str,
    commit_sha: str = "abc123",
    task_group: str = "rc-1",
    max_unresolved_severity: str | None = None,
) -> GateRequirement:
    return GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent=agent,
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
        commit_sha=commit_sha,
        task_group=task_group,
        max_unresolved_severity=max_unresolved_severity,
    )


@pytest.mark.parametrize(
    ("agent", "threshold"),
    (
        ("qa-engineer", None),
        ("security-reviewer", None),
        ("code-reviewer", "MEDIUM"),
    ),
)
def test_review_gate_accepts_matching_approved_handoff(agent: str, threshold: str | None) -> None:
    result = HandoffGateValidator().validate(
        _multi_agent_handoff(agent=agent, findings=[{"severity": "LOW", "message": "accepted"}]),
        _multi_agent_requirement(agent=agent, max_unresolved_severity=threshold),
        context="dadaia-workspace",
        release_id="v0.1.15",
        source=f".dadaia/handoff/dadaia-workspace/{agent}.handoff.json",
        artifact_hash=HASH,
        max_age_seconds=600,
        age_seconds=10,
    )

    assert result.accepted is True
    assert result.evidence is not None
    assert result.evidence.agent == agent
    assert result.evidence.context == "dadaia-workspace"
    assert result.evidence.release_id == "v0.1.15"
    assert result.evidence.verdict is GateVerdict.APPROVED
    assert result.evidence.commit_sha == "abc123"
    assert result.evidence.task_group == "rc-1"


@pytest.mark.parametrize(
    ("handoff", "requirement", "reason"),
    (
        (
            _multi_agent_handoff(agent="qa-engineer", context="other"),
            _multi_agent_requirement(agent="qa-engineer"),
            "wrong context",
        ),
        (
            _multi_agent_handoff(agent="security-reviewer"),
            _multi_agent_requirement(agent="qa-engineer"),
            "wrong agent",
        ),
        (
            _multi_agent_handoff(agent="security-reviewer", release_id="v0.1.14"),
            _multi_agent_requirement(agent="security-reviewer"),
            "wrong release_id",
        ),
        (
            _multi_agent_handoff(agent="qa-engineer", verdict="REJECTED"),
            _multi_agent_requirement(agent="qa-engineer"),
            "wrong verdict",
        ),
        (
            _multi_agent_handoff(agent="security-reviewer", commit_sha="old123"),
            _multi_agent_requirement(agent="security-reviewer"),
            "wrong commit_sha",
        ),
        (
            _multi_agent_handoff(agent="qa-engineer", task_group="other-rc"),
            _multi_agent_requirement(agent="qa-engineer"),
            "wrong task_group",
        ),
        (
            _multi_agent_handoff(
                agent="code-reviewer", findings=[{"severity": "HIGH", "message": "bug"}]
            ),
            _multi_agent_requirement(agent="code-reviewer", max_unresolved_severity="MEDIUM"),
            "unresolved severity exceeds threshold",
        ),
    ),
)
def test_review_gate_rejects_wrong_identity_or_unresolved_findings(
    handoff: dict[str, object],
    requirement: GateRequirement,
    reason: str,
) -> None:
    result = HandoffGateValidator().validate(
        handoff,
        requirement,
        context="dadaia-workspace",
        release_id="v0.1.15",
        source=".dadaia/handoff/dadaia-workspace/review.handoff.json",
        artifact_hash=HASH,
        max_age_seconds=600,
        age_seconds=10,
    )

    assert result.accepted is False
    assert reason in result.reasons

    stale_result = HandoffGateValidator().validate(
        _multi_agent_handoff(agent="security-reviewer"),
        _multi_agent_requirement(agent="security-reviewer"),
        context="dadaia-workspace",
        release_id="v0.1.15",
        source=".dadaia/handoff/dadaia-workspace/security.handoff.json",
        artifact_hash=HASH,
        max_age_seconds=600,
        age_seconds=601,
    )

    assert stale_result.accepted is False
    assert "stale handoff" in stale_result.reasons
