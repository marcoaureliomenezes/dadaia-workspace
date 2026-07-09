"""Lifecycle preflight service and typed blocked-state construction."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from dadaia_workspace.core.models.hygiene import HygieneCounters
from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    GateEvidence,
    GateRequirement,
    LifecyclePhase,
    LifecycleRunStatus,
)
from dadaia_workspace.core.protocols.runtime_files import RuntimeFilePort, RuntimeFileRef
from dadaia_workspace.features.lifecycle.gates import HandoffGateValidator
from dadaia_workspace.features.lifecycle.role_atoms import ROLE_ATOM_MAP
from dadaia_workspace.features.lifecycle.run_store import (
    LifecycleRunStore,
    LifecycleRunStoreError,
)


def resolve_emitted_handoff_version(
    *,
    agent: str,
    injected_refs: Sequence[str] = (),
    specs_dir: Path | None = None,
) -> tuple[str, dict[str, list[str]] | None]:
    """Resolve the emitted handoff ``schema_version`` + ``self_pull`` block (FR3/ADR-5).

    Precedence:

    1. The run's recorded ``InjectedContext`` refs (deduplicated, order preserved) —
       the mechanical grounding data, never a second bookkeeping path (ADR-5).
    2. Role→atom map fallback: the emitting *agent*'s mapped atom(s), included only
       when the atom file actually exists under *specs_dir* (mechanical honesty —
       never claim an atom that is not on disk).
    3. Honest ``handoff-v1.1`` with no ``self_pull`` — the ONLY sanctioned v1.1
       emission; a v1.2 document with empty or fabricated refs is never produced.
    """
    refs: list[str] = []
    for ref in injected_refs:
        cleaned = ref.strip()
        if cleaned and cleaned not in refs:
            refs.append(cleaned)
    if not refs and specs_dir is not None:
        for role in (part.strip() for part in agent.split(",")):
            relpath = ROLE_ATOM_MAP.get(role)
            if relpath is not None and (specs_dir / relpath).is_file():
                mapped_ref = f"specs/{relpath}"
                if mapped_ref not in refs:
                    refs.append(mapped_ref)
    if refs:
        return "handoff-v1.2", {"refs": refs}
    return "handoff-v1.1", None


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


class LifecycleCommandStatus(StrEnum):
    OK = "OK"
    BLOCKED = "BLOCKED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class LifecycleCommandResult:
    """Service-level outcome for lifecycle CLI commands."""

    status: LifecycleCommandStatus
    message: str
    blocked: BlockedState | None = None


@dataclass(frozen=True)
class BlockedPushResult:
    """Blocked push preflight state plus emitted handoff evidence."""

    command: LifecycleCommandResult
    handoff: RuntimeFileRef


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

    def resume_run(self, run_store: LifecycleRunStore, run_id: str) -> LifecycleCommandResult:
        """Resume a lifecycle run and translate persistence failures to typed output.

        FR6 (T-66-07): a resumed run that is still ``BLOCKED`` must not be reported as
        an unconditional OK — it never actually advanced. Inspect the loaded run's
        persisted status and, when it is BLOCKED, surface the run's own
        ``blocked.reason`` as a BLOCKED command result so the CLI exits non-zero with
        the real reason instead of a dishonest "OK resumed". Re-driving the blocked
        step is a separate, deferred capability (out of scope here) — this only makes
        the reported status honest.
        """
        try:
            run = run_store.resume(run_id)
        except LifecycleRunStoreError as exc:
            return LifecycleCommandResult(
                status=LifecycleCommandStatus.INTERNAL_ERROR,
                message=str(exc),
            )
        if run.status is LifecycleRunStatus.BLOCKED and run.blocked is not None:
            return LifecycleCommandResult(
                status=LifecycleCommandStatus.BLOCKED,
                message=run.blocked.reason,
                blocked=run.blocked,
            )
        return LifecycleCommandResult(
            status=LifecycleCommandStatus.OK,
            message=f"resumed {run.run_id}",
        )

    def blocked_push_preflight(
        self,
        *,
        context: str,
        release_id: str,
        commit_sha: str,
        runtime_files: RuntimeFilePort,
        run_id: str,
        injected_refs: Sequence[str] = (),
        specs_dir: Path | None = None,
    ) -> BlockedPushResult:
        """Return and emit the resumable blocked state for no-approval push.

        Emits ``handoff-v1.2`` with ``self_pull.refs`` from the run's recorded
        ``InjectedContext`` refs (dedup); zero refs fall back to the role→atom map,
        then to an honest ``handoff-v1.1`` (FR3/ADR-5).
        """
        schema_version, self_pull = resolve_emitted_handoff_version(
            agent="lifecycle",
            injected_refs=injected_refs,
            specs_dir=specs_dir,
        )
        blocked = BlockedState(
            reason="push requires security-reviewer approval",
            blocked_at_step="push",
            resume_token=f"{context}:{release_id}:push:{commit_sha}",
            operator_command="git push",
            detail={
                "context": context,
                "release_id": release_id,
                "commit_sha": commit_sha,
            },
        )
        command = LifecycleCommandResult(
            status=LifecycleCommandStatus.BLOCKED,
            message=blocked.reason,
            blocked=blocked,
        )
        payload: dict[str, object] = {
            "schema_version": schema_version,
            "agent": "lifecycle",
            "context": context,
            "release_id": release_id,
            "produced_at": datetime.now(UTC)
            .isoformat(timespec="seconds")
            .replace(
                "+00:00",
                "Z",
            ),
            "artifact": {"type": "other"},
            "scope": "blocked-push",
            "metrics": {
                "commit_sha": commit_sha,
                "blocked_at_step": blocked.blocked_at_step,
                "operator_command": blocked.operator_command or "",
                "resume_token": blocked.resume_token or "",
            },
            "findings": [
                {
                    "severity": "HIGH",
                    "message": blocked.reason,
                    "detail_md": "Push is blocked until security-reviewer handoff approval.",
                    "fix_recommendation": blocked.operator_command or "git push",
                }
            ],
        }
        if self_pull is not None:
            payload["self_pull"] = self_pull
        handoff = runtime_files.write_handoff(
            context=context,
            filename=f"{run_id}-blocked-push.handoff.json",
            payload=payload,
        )
        return BlockedPushResult(command=command, handoff=handoff)

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
