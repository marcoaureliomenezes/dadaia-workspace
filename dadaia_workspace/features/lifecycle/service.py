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
class PresenceState:
    """Caller mode plus advisory sibling presence used by lifecycle preflight."""

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
    presence: PresenceState
    hygiene: HygieneCounters
    required_handoffs: tuple[RequiredHandoff, ...] = ()


@dataclass(frozen=True)
class LifecyclePreflightResult:
    """Result of lifecycle preflight.

    ``warnings`` (v0.1.76 T-4, FR7): advisory, non-blocking lines — e.g. a live foreign
    session's presence on the same context. Never a reason to fail the gate (the
    NO-LOCKS DOCTRINE: no path may block an agent or operator because of another
    session); purely informational for the operator/report.
    """

    ok: bool
    blocked: BlockedState | None = None
    evidence: tuple[GateEvidence, ...] = ()
    warnings: tuple[str, ...] = ()


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
            # Bug r20-implementation-undefined-release-preflight-masks-guard: an
            # UNDEFINED release used to be reported as "context is not bound", because the
            # binding check ran first. The operator then binds — correctly, as instructed —
            # and hits the real problem only on the next attempt. Order the checks by how
            # fundamental the condition is: a release that does not exist cannot be bound
            # to, so it is named first. The bind check still runs for every release that
            # DOES exist, which is every real case.
            self._check_active_release,
            self._check_binding,
            self._check_specs_doctor,
            self._check_hygiene,
        )
        for check in checks:
            blocked = check(data)
            if blocked is not None:
                return LifecyclePreflightResult(ok=False, blocked=blocked)

        # Git cleanliness and sibling presence are advisory only.
        warnings = self._check_git(data) + self._check_presence(data)

        handoff_result = self._check_handoffs(data)
        if handoff_result.blocked is not None:
            return handoff_result

        return LifecyclePreflightResult(
            ok=True, evidence=handoff_result.evidence, warnings=warnings
        )

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
            # v0.1.78 T-C / FR-C: the session is bound to the WRONG context — the exact
            # remediation is re-binding THIS session to the context the run actually needs
            # (never a foreign session's binding; opt-in self-scoped correction only).
            return self._blocked(
                data,
                "wrong bound context",
                operator_command=(
                    f"dadaia context bind {data.context} --mode {data.required_mode} "
                    f"--release {data.release_id}"
                ),
            )
        if data.binding.release_id != data.release_id:
            # v0.1.78 T-C / FR-C: same remediation shape — re-bind to the release the run
            # targets.
            return self._blocked(
                data,
                "wrong bound release",
                operator_command=(
                    f"dadaia context bind {data.context} --mode {data.required_mode} "
                    f"--release {data.release_id}"
                ),
            )
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
            # Two different conditions used to share one message and one remedy. When
            # ACTIVE.md points at ANOTHER release, re-binding is the fix. When it points at
            # NOTHING, the target release simply does not exist — and telling the operator
            # to bind to it hands them a command that cannot work
            # (bug r20-implementation-undefined-release-preflight-masks-guard).
            active = (data.active_release.release_id or "").strip()
            if active in {"", "none", "None"}:
                return self._blocked(
                    data,
                    f"release {data.release_id!r} is not defined — no release is active in "
                    "this context, so there is nothing to implement yet. Author the backlog "
                    "first (the command below), then run release-definition against that "
                    f"backlog run id to define {data.release_id}",
                    # Bug r23-preflight-operator-command-not-pasteable: this ended in
                    # `--backlog-run-id <a completed backlog run>` — a blank the operator
                    # cannot fill without a run id they do not have. And when no release is
                    # defined, release-definition is not even the right next action:
                    # authoring the backlog it would consume is, and THAT command needs
                    # nothing looked up. Prescribe the step they can take right now, with
                    # the follow-up spelled out after it.
                    operator_command=(
                        f"dadaia lifecycle backlog-definition --context {data.context} "
                        f"--release-id {data.release_id} "
                        f"--run-id bd-{data.release_id.replace('.', '-')} "
                        "--demand 'what this release should deliver'"
                    ),
                )
            return self._blocked(
                data,
                f"active release mismatch: this context is on {active!r}, "
                f"the run targets {data.release_id!r}",
                operator_command=(
                    f"dadaia context bind {data.context} --mode {data.required_mode} "
                    f"--release {data.release_id}"
                ),
            )
        if not self._phase_matches(data.active_release.phase, data.expected_phase):
            # v0.1.78 T-C / FR-C: ACTIVE.md's phase does not match what this step expects —
            # `dadaia reports workflow-status` is the read-only command that surfaces the current
            # release/phase/step so the operator can see exactly where the ladder actually
            # is before deciding the next move.
            return self._blocked(
                data,
                "active release phase mismatch",
                operator_command="dadaia reports workflow-status --json",
            )
        return None

    def _check_git(self, data: LifecyclePreflightInput) -> tuple[str, ...]:
        warnings: list[str] = []
        if data.git.dirty_paths:
            warnings.append(
                "[GIT] dirty worktree is advisory for lifecycle preflight; "
                f"paths={','.join(data.git.dirty_paths)}; authoritative commit/review "
                "and push-security gates still apply."
            )
        if data.git.upstream_branch is None:
            warnings.append(
                "[GIT] missing upstream branch is advisory for lifecycle preflight; "
                "set one with git push --set-upstream origin HEAD before relying on push gates."
            )
        if data.git.unpushed_commit_count > 0:
            warnings.append(
                "[GIT] unpushed commits are advisory for lifecycle preflight; "
                f"count={data.git.unpushed_commit_count}; push-security and CI gates "
                "remain authoritative."
            )
        return tuple(warnings)

    def _check_specs_doctor(self, data: LifecyclePreflightInput) -> BlockedState | None:
        if not data.specs_doctor.ok:
            return self._blocked(
                data,
                "specs doctor failed",
                operator_command="dadaia specs doctor",
                detail={"specs_doctor": data.specs_doctor.summary},
            )
        return None

    def _check_presence(self, data: LifecyclePreflightInput) -> tuple[str, ...]:
        """Presence-advisory only (v0.1.76 T-4, FR7, NO-LOCKS DOCTRINE).

        A live sibling session may not block a lifecycle verb. The caller's own mode is
        validated separately by ``_check_binding``; presence is informational only.
        """
        if data.presence.live_foreign_holder:
            holder = data.presence.holder_session_id or "unknown"
            return (
                f"[PRESENCE] another session ({holder!r}) has a live presence on this "
                "context. Races between sessions are accepted and surfaced, never "
                "blocked — no action required.",
            )
        return ()

    def _check_hygiene(self, data: LifecyclePreflightInput) -> BlockedState | None:
        # v0.1.72 FR3 (bug `hygiene-preflight-blocks-protected-residuals`): candidates the
        # cleaner itself protects (current_release_evidence) are NOT reclaimable waste —
        # a gate must never demand deletion of evidence the deleter refuses to delete.
        # Block only on the UNPROTECTED remainder.
        # Permission-unreclaimable candidates (root-owned container artifacts) join the
        # protected residuals on the never-demand side of the gate (bug
        # preflight-hygiene-gate-demands-root-owned-deletions): the cleaner cannot
        # delete them, so blocking on them makes the remediation loop unsatisfiable.
        unprotected = (
            data.hygiene.cleanup_candidate_count
            - data.hygiene.protected_residual_count
            - data.hygiene.unreclaimable_count
        )
        if unprotected > 0:
            return self._blocked(
                data,
                "hygiene cleanup candidates present",
                operator_command="dadaia reports workflow-hygiene-clean --dry-run",
                detail={
                    "cleanup_candidate_count": str(data.hygiene.cleanup_candidate_count),
                    "protected_residual_count": str(data.hygiene.protected_residual_count),
                },
            )
        if data.hygiene.malformed_handoff_count > 0:
            return self._blocked(
                data,
                "malformed handoffs present",
                operator_command="dadaia reports workflow-hygiene-status --json",
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
                # v0.1.78 T-C / FR-C: name the exact failed handoff so the operator's next
                # command inspects the SAME document the gate rejected, not a generic status
                # dump — ``detail["handoff"]`` above already carries the source path; the
                # remediation command surfaces it too so `--json` consumers don't have to
                # cross-reference ``detail``.
                return LifecyclePreflightResult(
                    ok=False,
                    blocked=self._blocked(
                        data,
                        "required handoff gate failed",
                        operator_command=(
                            f"dadaia reports workflow-status --json  # inspect {required.source}"
                        ),
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
                # Bug r4d-resume-preflight-invalid-step-traceback: a reader seeing
                # blocked_at_step="preflight" naturally reaches for
                # `--resume-from preflight`, which cannot work — preflight is a GATE
                # evaluated BEFORE any run exists, so there is no run to resume. Say so
                # in-band; the remedy is the operator_command above, then re-run the verb.
                "resumable": "false",
                "resume_hint": (
                    "preflight is a gate, not a resumable step — do NOT pass "
                    "--resume-from preflight; apply operator_command, then re-run the verb"
                ),
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
