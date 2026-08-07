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






def _required_int(value: object) -> int:
    return int(str(value))


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return _required_int(value)
