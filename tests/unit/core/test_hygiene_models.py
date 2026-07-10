"""Unit tests for pure hygiene core models.

Frozen-dataclass immutability for SlopPolicy is covered by the SHARED param sweep in
``tests/unit/core/models/test_workflow_execution.py::test_all_models_are_frozen``.
"""

from dadaia_workspace.core.models.hygiene import (
    HygieneCandidate,
    HygieneCandidateKind,
    HygieneCounters,
    HygieneProtectionKind,
    HygieneSnapshot,
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

    counters = HygieneCounters(
        zone_totals={HygieneZone.REPORTS: 122, HygieneZone.HANDOFF: 295, HygieneZone.TMP: 437724},
        expired_totals={HygieneZone.REPORTS: 121, HygieneZone.HANDOFF: 294},
        orphan_handoff_count=4,
        malformed_handoff_count=2,
        unknown_top_level_dirs=("imgs", "references"),
        cleanup_candidate_count=417,
        protected_residual_count=3,
        scan_elapsed_ms=250,
    )
    counters_data = counters.to_dict()
    assert counters_data["zone_totals"] == {"reports": 122, "handoff": 295, "tmp": 437724}
    assert counters_data["expired_totals"] == {"reports": 121, "handoff": 294}
    assert counters_data["unknown_top_level_dirs"] == ["imgs", "references"]
    assert HygieneCounters.from_dict(counters_data) == counters

    snapshot = HygieneSnapshot(
        schema_version="hygiene-snapshot-v1",
        timestamp="2026-06-18T04:30:00Z",
        context="dadaia-workspace",
        release_id="v0.1.15",
        run_id="run-1",
        policy=SlopPolicy(),
        counters=HygieneCounters(cleanup_candidate_count=1),
        candidates=(
            HygieneCandidate(
                path=".dadaia/tmp/software-engineer/old.tmp",
                zone=HygieneZone.TMP,
                kind=HygieneCandidateKind.EXPIRED_TMP,
                reason="older than tmp TTL",
                age_seconds=90000,
            ),
        ),
    )
    snap_data = snapshot.to_dict()
    assert snap_data["schema_version"] == "hygiene-snapshot-v1"
    assert snap_data["policy"]["reports_ttl_seconds"] == 172800
    assert snap_data["counters"]["cleanup_candidate_count"] == 1
    assert snap_data["candidates"][0]["kind"] == "expired_tmp"
    assert HygieneSnapshot.from_dict(snap_data) == snapshot
