"""Lifecycle preflight service and typed blocked-state construction."""

from __future__ import annotations

from dataclasses import dataclass

from dadaia_workspace.core.models.hygiene import HygieneCounters
from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    GateEvidence,
    GateRequirement,
    LifecyclePhase,
)
from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator


@dataclass(frozen=True)
class BoundContext:
    """Resolved context binding for the current session."""

    context: str
    release_id: str
    mode: str
    session_id: str


@dataclass(frozen=True)
class ActiveReleaseState:
    """Current ACTIVE.md release pointer and phase."""

    release_id: str | None
    phase: str | None


@dataclass(frozen=True)
class GitPreflightState:
    """Structured git state needed by lifecycle preflight."""

    dirty_paths: tuple[str, ...] = ()
    upstream_branch: str | None = None
    unpushed_commit_count: int = 0


@dataclass(frozen=True)
class SpecsDoctorState:
    """Structured specs doctor result."""

    ok: bool
    summary: str = ""


@dataclass(frozen=True)
class LeaseModeState:
    """Resolved lifecycle lease and mode state."""

    mode: str
    holder_session_id: str | None = None
    live_foreign_holder: bool = False


@dataclass(frozen=True)
class RequiredHandoff:
    """One handoff document that must satisfy a gate requirement."""

    source: str
    document: dict[str, object]
    requirement: GateRequirement
    artifact_hash: str | None = None
    max_age_seconds: int | None = None
    age_seconds: int | None = None


@dataclass(frozen=True)
class LifecyclePreflightInput:
    """Complete structured input for a lifecycle preflight run."""

    context: str
    release_id: str
    expected_phase: LifecyclePhase
    required_mode: str
    current_step: str
    binding: BoundContext | None
    active_release: ActiveReleaseState
    git: GitPreflightState
    specs_doctor: SpecsDoctorState
    lease: LeaseModeState
    hygiene: HygieneCounters
    required_handoffs: tuple[RequiredHandoff, ...] = ()


@dataclass(frozen=True)
class LifecyclePreflightResult:
    """Result of lifecycle preflight."""

    ok: bool
    blocked: BlockedState | None = None
    evidence: tuple[GateEvidence, ...] = ()


class LifecyclePreflightService:
    """Evaluate lifecycle preconditions and return typed blocked state."""

    def __init__(self, *, handoff_validator: HandoffGateValidator | None = None) -> None:
        self._handoff_validator = handoff_validator or HandoffGateValidator()

    def preflight(self, data: LifecyclePreflightInput) -> LifecyclePreflightResult:
        checks = (
            self._check_binding,
            self._check_active_release,
            self._check_git,
            self._check_specs_doctor,
            self._check_lease,
            self._check_hygiene,
        )
        for check in checks:
            blocked = check(data)
            if blocked is not None:
                return LifecyclePreflightResult(ok=False, blocked=blocked)

        handoff_result = self._check_handoffs(data)
        if handoff_result.blocked is not None:
            return handoff_result

        return LifecyclePreflightResult(ok=True, evidence=handoff_result.evidence)

    def _check_binding(self, data: LifecyclePreflightInput) -> BlockedState | None:
        if data.binding is None:
            return self._blocked(
                data,
                "context is not bound",
                operator_command=(
                    f"dadaia context bind {data.context} --mode {data.required_mode} "
                    f"--release {data.release_id}"
                ),
            )
        if data.binding.context != data.context:
            return self._blocked(data, "wrong bound context")
        if data.binding.release_id != data.release_id:
            return self._blocked(data, "wrong bound release")
        if not self._mode_matches(data.binding.mode, data.required_mode):
            return self._blocked(
                data,
                "wrong bound mode",
                operator_command=(
                    f"dadaia context bind {data.context} --mode {data.required_mode} "
                    f"--release {data.release_id}"
                ),
            )
        return None

    def _check_active_release(self, data: LifecyclePreflightInput) -> BlockedState | None:
        if data.active_release.release_id != data.release_id:
            return self._blocked(data, "active release mismatch")
        if not self._phase_matches(data.active_release.phase, data.expected_phase):
            return self._blocked(data, "active release phase mismatch")
        return None

    def _check_git(self, data: LifecyclePreflightInput) -> BlockedState | None:
        if data.git.dirty_paths:
            return self._blocked(
                data,
                "dirty worktree",
                operator_command="git status --short",
                detail={"dirty_paths": ",".join(data.git.dirty_paths)},
            )
        if data.git.upstream_branch is None:
            return self._blocked(
                data,
                "missing upstream branch",
                operator_command="git push --set-upstream origin HEAD",
            )
        if data.git.unpushed_commit_count > 0:
            return self._blocked(
                data,
                "unpushed commits pending",
                operator_command="git push",
                detail={"unpushed_commit_count": str(data.git.unpushed_commit_count)},
            )
        return None

    def _check_specs_doctor(self, data: LifecyclePreflightInput) -> BlockedState | None:
        if not data.specs_doctor.ok:
            return self._blocked(
                data,
                "specs doctor failed",
                operator_command="dadaia specs doctor",
                detail={"specs_doctor": data.specs_doctor.summary},
            )
        return None

    def _check_lease(self, data: LifecyclePreflightInput) -> BlockedState | None:
        if not self._mode_matches(data.lease.mode, data.required_mode):
            return self._blocked(data, "lease mode mismatch")
        if data.lease.live_foreign_holder:
            return self._blocked(
                data,
                "live foreign lease holder",
                detail={"holder_session_id": data.lease.holder_session_id or ""},
            )
        return None

    def _check_hygiene(self, data: LifecyclePreflightInput) -> BlockedState | None:
        if data.hygiene.cleanup_candidate_count > 0:
            return self._blocked(
                data,
                "hygiene cleanup candidates present",
                operator_command="dadaia lifecycle hygiene clean --dry-run",
                detail={
                    "cleanup_candidate_count": str(data.hygiene.cleanup_candidate_count),
                    "protected_residual_count": str(data.hygiene.protected_residual_count),
                },
            )
        if data.hygiene.malformed_handoff_count > 0:
            return self._blocked(
                data,
                "malformed handoffs present",
                operator_command="dadaia lifecycle hygiene status --json",
                detail={"malformed_handoff_count": str(data.hygiene.malformed_handoff_count)},
            )
        return None

    def _check_handoffs(self, data: LifecyclePreflightInput) -> LifecyclePreflightResult:
        evidence: list[GateEvidence] = []
        for required in data.required_handoffs:
            validation = self._handoff_validator.validate(
                required.document,
                required.requirement,
                context=data.context,
                release_id=data.release_id,
                source=required.source,
                artifact_hash=required.artifact_hash,
                max_age_seconds=required.max_age_seconds,
                age_seconds=required.age_seconds,
            )
            if not validation.accepted:
                return LifecyclePreflightResult(
                    ok=False,
                    blocked=self._blocked(
                        data,
                        "required handoff gate failed",
                        detail={
                            "handoff": required.source,
                            "reasons": ",".join(validation.reasons),
                        },
                    ),
                )
            assert validation.evidence is not None
            evidence.append(validation.evidence)
        return LifecyclePreflightResult(ok=True, evidence=tuple(evidence))

    def _blocked(
        self,
        data: LifecyclePreflightInput,
        reason: str,
        *,
        operator_command: str | None = None,
        detail: dict[str, str] | None = None,
    ) -> BlockedState:
        return BlockedState(
            reason=reason,
            blocked_at_step=data.current_step,
            resume_token=f"{data.context}:{data.release_id}:{data.current_step}",
            operator_command=operator_command,
            detail={
                "context": data.context,
                "release_id": data.release_id,
                "expected_phase": data.expected_phase.value,
                **(detail or {}),
            },
        )

    @staticmethod
    def _phase_matches(raw_phase: str | None, expected: LifecyclePhase) -> bool:
        if raw_phase is None:
            return False
        normalized = raw_phase.strip().lower()
        return normalized in {expected.name.lower(), expected.value.lower()}

    @staticmethod
    def _mode_matches(raw_mode: str, expected_mode: str) -> bool:
        normalized = raw_mode.strip().lower()
        expected = expected_mode.strip().lower()
        return normalized in {expected, f"bound_{expected}"}
