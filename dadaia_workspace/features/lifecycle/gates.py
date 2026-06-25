"""Semantic gate validators for lifecycle handoff evidence."""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.models.lifecycle import (
    GateEvidence,
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
)

_SEVERITY_RANK: dict[str, int] = {
    "INFO": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}


@dataclass(frozen=True)
class HandoffGateValidation:
    """Semantic validation result for a handoff gate."""

    accepted: bool
    evidence: GateEvidence | None = None
    reasons: tuple[str, ...] = ()


class HandoffGateValidator:
    """Validate raw handoff JSON against one lifecycle gate requirement."""

    def validate(
        self,
        handoff: dict[str, object],
        requirement: GateRequirement,
        *,
        context: str,
        release_id: str,
        source: str,
        artifact_hash: str | None = None,
        max_age_seconds: int | None = None,
        age_seconds: int | None = None,
    ) -> HandoffGateValidation:
        reasons: list[str] = []
        evidence = self._evidence_from_handoff(handoff, context, release_id, source, reasons)
        if evidence is not None:
            reasons.extend(
                self._requirement_reasons(
                    handoff,
                    evidence,
                    requirement,
                    artifact_hash=artifact_hash,
                    max_age_seconds=max_age_seconds,
                    age_seconds=age_seconds,
                )
            )
        if reasons:
            return HandoffGateValidation(accepted=False, reasons=tuple(reasons))
        assert evidence is not None
        return HandoffGateValidation(accepted=True, evidence=evidence)

    def _evidence_from_handoff(
        self,
        handoff: dict[str, object],
        context: str,
        release_id: str,
        source: str,
        reasons: list[str],
    ) -> GateEvidence | None:
        agent = self._string_field(handoff, "agent", reasons)
        actual_context = self._string_field(handoff, "context", reasons)
        actual_release = self._string_field(handoff, "release_id", reasons)
        self._schema_version(handoff, reasons)
        self._string_field(handoff, "produced_at", reasons)
        self._string_field(handoff, "scope", reasons)
        verdict = self._verdict(handoff, reasons)
        metrics = self._metrics(handoff, reasons)
        artifact = self._artifact(handoff, reasons)
        if not reasons:
            if actual_context != context:
                reasons.append("wrong context")
            if actual_release != release_id:
                reasons.append("wrong release_id")
        if reasons:
            return None
        assert agent is not None
        assert verdict is not None
        assert metrics is not None
        assert artifact is not None
        commit_sha = self._optional_metric(metrics, "commit_sha", reasons)
        task_group = self._optional_metric(metrics, "task_group", reasons)
        if reasons:
            return None
        return GateEvidence(
            evidence_kind=GateEvidenceKind.HANDOFF,
            source=source,
            context=context,
            release_id=release_id,
            agent=agent,
            verdict=verdict,
            commit_sha=commit_sha,
            task_group=task_group,
            metrics={str(key): str(value) for key, value in metrics.items()},
        )

    def _requirement_reasons(
        self,
        handoff: dict[str, object],
        evidence: GateEvidence,
        requirement: GateRequirement,
        *,
        artifact_hash: str | None,
        max_age_seconds: int | None,
        age_seconds: int | None,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if requirement.evidence_kind is not GateEvidenceKind.HANDOFF:
            reasons.append("unsupported evidence kind")
        if requirement.required_agent is not None and evidence.agent != requirement.required_agent:
            reasons.append("wrong agent")
        if (
            requirement.required_verdict is not None
            and evidence.verdict is not requirement.required_verdict
        ):
            reasons.append("wrong verdict")
        if requirement.release_id is not None and evidence.release_id != requirement.release_id:
            reasons.append("wrong release_id")
        if requirement.commit_sha is not None and evidence.commit_sha != requirement.commit_sha:
            reasons.append("wrong commit_sha")
        if requirement.task_group is not None and evidence.task_group != requirement.task_group:
            reasons.append("wrong task_group")
        if max_age_seconds is not None and (age_seconds is None or age_seconds > max_age_seconds):
            reasons.append("stale handoff")
        if artifact_hash is not None:
            artifact = handoff["artifact"]
            assert isinstance(artifact, dict)
            if artifact.get("content_hash") != artifact_hash:
                reasons.append("artifact hash mismatch")
        severity_reason = self._severity_reason(handoff, requirement.max_unresolved_severity)
        if severity_reason is not None:
            reasons.append(severity_reason)
        return tuple(reasons)

    def _severity_reason(
        self,
        handoff: dict[str, object],
        max_unresolved_severity: str | None,
    ) -> str | None:
        if max_unresolved_severity is None:
            return None
        max_rank = _SEVERITY_RANK.get(max_unresolved_severity)
        if max_rank is None:
            return "invalid severity threshold"
        findings = handoff.get("findings", [])
        if not isinstance(findings, list):
            return "malformed findings"
        for finding in findings:
            if not isinstance(finding, dict):
                return "malformed findings"
            severity = finding.get("severity")
            if not isinstance(severity, str) or severity not in _SEVERITY_RANK:
                return "malformed findings"
            if _SEVERITY_RANK[severity] > max_rank:
                return "unresolved severity exceeds threshold"
        return None

    def _string_field(
        self,
        handoff: dict[str, object],
        field: str,
        reasons: list[str],
    ) -> str | None:
        value = handoff.get(field)
        if not isinstance(value, str) or not value:
            reasons.append(f"malformed {field}")
            return None
        return value

    def _verdict(self, handoff: dict[str, object], reasons: list[str]) -> GateVerdict | None:
        value = handoff.get("verdict")
        if not isinstance(value, str):
            reasons.append("malformed verdict")
            return None
        try:
            return GateVerdict(value)
        except ValueError:
            reasons.append("malformed verdict")
            return None

    def _schema_version(self, handoff: dict[str, object], reasons: list[str]) -> None:
        value = handoff.get("schema_version")
        if value not in {"handoff-v1", "handoff-v1.1"}:
            reasons.append("malformed schema_version")

    def _metrics(
        self,
        handoff: dict[str, object],
        reasons: list[str],
    ) -> dict[str, object] | None:
        value = handoff.get("metrics")
        if not isinstance(value, dict):
            reasons.append("malformed metrics")
            return None
        return value

    def _artifact(
        self,
        handoff: dict[str, object],
        reasons: list[str],
    ) -> dict[str, object] | None:
        value = handoff.get("artifact")
        if not isinstance(value, dict):
            reasons.append("malformed artifact")
            return None
        artifact_type = value.get("type")
        if artifact_type not in {"report", "spec", "plan", "tasks", "closure", "memory", "other"}:
            reasons.append("malformed artifact type")
        content_hash = value.get("content_hash")
        if content_hash is not None and (
            not isinstance(content_hash, str) or len(content_hash) != 64
        ):
            reasons.append("malformed artifact hash")
        return value

    def _optional_metric(
        self,
        metrics: dict[str, object],
        field: str,
        reasons: list[str],
    ) -> str | None:
        value = metrics.get(field)
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            reasons.append(f"malformed {field}")
            return None
        return value
