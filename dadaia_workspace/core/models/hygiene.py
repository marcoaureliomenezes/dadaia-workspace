"""Pure hygiene models for workspace slop policy and counters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class HygieneZone(StrEnum):
    REPORTS = "reports"
    HANDOFF = "handoff"
    TMP = "tmp"


class HygieneCandidateKind(StrEnum):
    EXPIRED_REPORT = "expired_report"
    EXPIRED_HANDOFF = "expired_handoff"
    EXPIRED_TMP = "expired_tmp"
    ORPHAN_HANDOFF = "orphan_handoff"
    MALFORMED_HANDOFF = "malformed_handoff"
    EMPTY_DIRECTORY = "empty_directory"
    UNKNOWN_TOP_LEVEL = "unknown_top_level"
    #: v0.1.78 T-C / FR-C: a workflow-step handoff-ledger payload
    #: (``.dadaia/runs/lifecycle/<run>/steps/*.step-payload.json``) that is cleanup-eligible
    #: (``DELETE_AFTER_CONSUMED`` + every declared consumer has consumed it), belongs to a
    #: TERMINAL run, and is past the tmp-zone consumed TTL — the ONE canonical cleanup
    #: contract's ``.dadaia/runs`` coverage (bug
    #: ``split-cleanup-engines-strand-stale-step-payloads``).
    EXPIRED_STEP_PAYLOAD = "expired_step_payload"


class HygieneProtectionKind(StrEnum):
    IMPORTANT_REPORT = "important_report"
    CURRENT_RELEASE_EVIDENCE = "current_release_evidence"
    ACTIVE_RUN = "active_run"
    DURABLE_STATE = "durable_state"
    LOCK = "lock"
    SESSION = "session"
    OPERATOR_PROTECTED = "operator_protected"
    #: v0.1.74: a zone-root doc file (AGENTS.md / README.md / .gitkeep) — the documented
    #: scoped-rules / zone-documentation mechanism, lib-projected with historical mtimes;
    #: canonical, never reclaimable (bug public-install-restores-expired-zone-agents).
    CANONICAL_ZONE_DOC = "canonical_zone_doc"
    OUTSIDE_SAFE_ZONE = "outside_safe_zone"


@dataclass(frozen=True)
class SlopPolicy:
    reports_ttl_seconds: int = 48 * 60 * 60
    handoff_ttl_seconds: int = 24 * 60 * 60
    tmp_ttl_seconds: int = 24 * 60 * 60
    safe_zones: tuple[HygieneZone, ...] = (
        HygieneZone.REPORTS,
        HygieneZone.HANDOFF,
        HygieneZone.TMP,
    )
    durable_top_level_dirs: tuple[str, ...] = (
        "agentic",
        "hooks",
        "locks",
        "logs",
        "mcps",
        "reports",
        "handoff",
        "runs",
        "sessions",
        "states",
        "tmp",
    )

    def ttl_for(self, zone: HygieneZone) -> int:
        if zone is HygieneZone.REPORTS:
            return self.reports_ttl_seconds
        if zone is HygieneZone.HANDOFF:
            return self.handoff_ttl_seconds
        if zone is HygieneZone.TMP:
            return self.tmp_ttl_seconds
        raise ValueError(f"unsupported hygiene zone: {zone}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reports_ttl_seconds": self.reports_ttl_seconds,
            "handoff_ttl_seconds": self.handoff_ttl_seconds,
            "tmp_ttl_seconds": self.tmp_ttl_seconds,
            "safe_zones": [zone.value for zone in self.safe_zones],
            "durable_top_level_dirs": list(self.durable_top_level_dirs),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> SlopPolicy:
        safe_zones = data.get("safe_zones", [])
        durable_dirs = data.get("durable_top_level_dirs", [])
        assert isinstance(safe_zones, list)
        assert isinstance(durable_dirs, list)
        return cls(
            reports_ttl_seconds=_required_int(data["reports_ttl_seconds"]),
            handoff_ttl_seconds=_required_int(data["handoff_ttl_seconds"]),
            tmp_ttl_seconds=_required_int(data["tmp_ttl_seconds"]),
            safe_zones=tuple(HygieneZone(str(zone)) for zone in safe_zones),
            durable_top_level_dirs=tuple(str(item) for item in durable_dirs),
        )


@dataclass(frozen=True)
class HygieneCandidate:
    path: str
    zone: HygieneZone
    kind: HygieneCandidateKind
    reason: str
    age_seconds: int | None = None
    protected: bool = False
    protection_kind: HygieneProtectionKind | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "zone": self.zone.value,
            "kind": self.kind.value,
            "reason": self.reason,
            "age_seconds": self.age_seconds,
            "protected": self.protected,
            "protection_kind": self.protection_kind.value if self.protection_kind else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> HygieneCandidate:
        protection = data.get("protection_kind")
        age = data.get("age_seconds")
        return cls(
            path=str(data["path"]),
            zone=HygieneZone(str(data["zone"])),
            kind=HygieneCandidateKind(str(data["kind"])),
            reason=str(data["reason"]),
            age_seconds=_optional_int(age),
            protected=bool(data.get("protected", False)),
            protection_kind=HygieneProtectionKind(str(protection)) if protection else None,
        )


@dataclass(frozen=True)
class HygieneCounters:
    zone_totals: dict[HygieneZone, int] = field(default_factory=dict)
    expired_totals: dict[HygieneZone, int] = field(default_factory=dict)
    orphan_handoff_count: int = 0
    malformed_handoff_count: int = 0
    unknown_top_level_dirs: tuple[str, ...] = ()
    cleanup_candidate_count: int = 0
    protected_residual_count: int = 0
    #: Expired candidates the cleaner cannot delete (parent not user-writable) — an
    #: OPERATOR advisory, never a preflight block (bug
    #: preflight-hygiene-gate-demands-root-owned-deletions).
    unreclaimable_count: int = 0
    scan_elapsed_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_totals": {zone.value: count for zone, count in self.zone_totals.items()},
            "expired_totals": {zone.value: count for zone, count in self.expired_totals.items()},
            "orphan_handoff_count": self.orphan_handoff_count,
            "malformed_handoff_count": self.malformed_handoff_count,
            "unknown_top_level_dirs": list(self.unknown_top_level_dirs),
            "cleanup_candidate_count": self.cleanup_candidate_count,
            "protected_residual_count": self.protected_residual_count,
            "unreclaimable_count": self.unreclaimable_count,
            "scan_elapsed_ms": self.scan_elapsed_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> HygieneCounters:
        zone_totals = data.get("zone_totals", {})
        expired_totals = data.get("expired_totals", {})
        unknown_dirs = data.get("unknown_top_level_dirs", [])
        assert isinstance(zone_totals, dict)
        assert isinstance(expired_totals, dict)
        assert isinstance(unknown_dirs, list)
        return cls(
            zone_totals={
                HygieneZone(str(zone)): _required_int(count) for zone, count in zone_totals.items()
            },
            expired_totals={
                HygieneZone(str(zone)): _required_int(count)
                for zone, count in expired_totals.items()
            },
            orphan_handoff_count=_required_int(data.get("orphan_handoff_count", 0)),
            malformed_handoff_count=_required_int(data.get("malformed_handoff_count", 0)),
            unknown_top_level_dirs=tuple(str(item) for item in unknown_dirs),
            cleanup_candidate_count=_required_int(data.get("cleanup_candidate_count", 0)),
            unreclaimable_count=_required_int(data.get("unreclaimable_count", 0)),
            protected_residual_count=_required_int(data.get("protected_residual_count", 0)),
            scan_elapsed_ms=_optional_int(data.get("scan_elapsed_ms")),
        )


@dataclass(frozen=True)
class HygieneSnapshot:
    schema_version: str
    timestamp: str
    context: str
    release_id: str
    run_id: str
    policy: SlopPolicy
    counters: HygieneCounters
    candidates: tuple[HygieneCandidate, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "context": self.context,
            "release_id": self.release_id,
            "run_id": self.run_id,
            "policy": self.policy.to_dict(),
            "counters": self.counters.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> HygieneSnapshot:
        policy_raw = data["policy"]
        counters_raw = data["counters"]
        candidates_raw = data.get("candidates", [])
        assert isinstance(policy_raw, dict)
        assert isinstance(counters_raw, dict)
        assert isinstance(candidates_raw, list)
        return cls(
            schema_version=str(data["schema_version"]),
            timestamp=str(data["timestamp"]),
            context=str(data["context"]),
            release_id=str(data["release_id"]),
            run_id=str(data["run_id"]),
            policy=SlopPolicy.from_dict(policy_raw),
            counters=HygieneCounters.from_dict(counters_raw),
            candidates=tuple(
                HygieneCandidate.from_dict(candidate)
                for candidate in candidates_raw
                if isinstance(candidate, dict)
            ),
        )


def _required_int(value: object) -> int:
    return int(str(value))


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return _required_int(value)
