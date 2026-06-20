"""Integration tests for lifecycle QA/security/code-review gate handoffs."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.lifecycle import (
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
)
from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator

HASH = "a" * 64


def _handoff(
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


def _requirement(
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
        _handoff(agent=agent, findings=[{"severity": "LOW", "message": "accepted"}]),
        _requirement(agent=agent, max_unresolved_severity=threshold),
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
            _handoff(agent="qa-engineer", context="other"),
            _requirement(agent="qa-engineer"),
            "wrong context",
        ),
        (
            _handoff(agent="security-reviewer"),
            _requirement(agent="qa-engineer"),
            "wrong agent",
        ),
        (
            _handoff(agent="security-reviewer", release_id="v0.1.14"),
            _requirement(agent="security-reviewer"),
            "wrong release_id",
        ),
        (
            _handoff(agent="qa-engineer", verdict="REJECTED"),
            _requirement(agent="qa-engineer"),
            "wrong verdict",
        ),
        (
            _handoff(agent="security-reviewer", commit_sha="old123"),
            _requirement(agent="security-reviewer"),
            "wrong commit_sha",
        ),
        (
            _handoff(agent="qa-engineer", task_group="other-rc"),
            _requirement(agent="qa-engineer"),
            "wrong task_group",
        ),
        (
            _handoff(agent="code-reviewer", findings=[{"severity": "HIGH", "message": "bug"}]),
            _requirement(agent="code-reviewer", max_unresolved_severity="MEDIUM"),
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


def test_review_gate_rejects_stale_approval() -> None:
    result = HandoffGateValidator().validate(
        _handoff(agent="security-reviewer"),
        _requirement(agent="security-reviewer"),
        context="dadaia-workspace",
        release_id="v0.1.15",
        source=".dadaia/handoff/dadaia-workspace/security.handoff.json",
        artifact_hash=HASH,
        max_age_seconds=600,
        age_seconds=601,
    )

    assert result.accepted is False
    assert "stale handoff" in result.reasons
