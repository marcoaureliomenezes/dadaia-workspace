"""Unit tests for the surviving pure hygiene core models (v0.3.0: the engine's
``HygieneCounters``/``HygieneSnapshot`` died with the workflow runtime; ``SlopPolicy``,
``HygieneZone`` and ``HygieneCandidate`` survive as the workspace-clean / report-retention
contract)."""

from dadaia_workspace.core.models.hygiene import (
    HygieneCandidate,
    HygieneCandidateKind,
    HygieneProtectionKind,
    HygieneZone,
    SlopPolicy,
)


def test_slop_policy_defaults_match_release_ttl_law() -> None:
    policy = SlopPolicy()

    assert policy.ttl_for(HygieneZone.REPORTS) == 48 * 60 * 60
    assert policy.ttl_for(HygieneZone.HANDOFF) == 24 * 60 * 60
    assert policy.ttl_for(HygieneZone.TMP) == 24 * 60 * 60
    assert policy.safe_zones == (
        HygieneZone.REPORTS,
        HygieneZone.HANDOFF,
        HygieneZone.TMP,
    )


def test_hygiene_models_round_trip_to_primitive_dict() -> None:
    policy = SlopPolicy(
        reports_ttl_seconds=7200,
        handoff_ttl_seconds=3600,
        tmp_ttl_seconds=1800,
        safe_zones=(HygieneZone.REPORTS, HygieneZone.TMP),
        durable_top_level_dirs=("reports", "tmp", "states"),
    )
    data = policy.to_dict()
    assert data == {
        "reports_ttl_seconds": 7200,
        "handoff_ttl_seconds": 3600,
        "tmp_ttl_seconds": 1800,
        "safe_zones": ["reports", "tmp"],
        "durable_top_level_dirs": ["reports", "tmp", "states"],
    }
    assert SlopPolicy.from_dict(data) == policy

    candidate = HygieneCandidate(
        path=".dadaia/reports/dadaia-workspace/report.html",
        zone=HygieneZone.REPORTS,
        kind=HygieneCandidateKind.EXPIRED_REPORT,
        reason="older than reports TTL",
        age_seconds=172801,
        protected=True,
        protection_kind=HygieneProtectionKind.CURRENT_RELEASE_EVIDENCE,
    )
    cand_data = candidate.to_dict()
    assert cand_data == {
        "path": ".dadaia/reports/dadaia-workspace/report.html",
        "zone": "reports",
        "kind": "expired_report",
        "reason": "older than reports TTL",
        "age_seconds": 172801,
        "protected": True,
        "protection_kind": "current_release_evidence",
    }
    assert HygieneCandidate.from_dict(cand_data) == candidate
