"""Unit tests for lifecycle preflight service."""

from __future__ import annotations

import pytest

from dadaia_workspace.core.models.hygiene import HygieneCounters
from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    GateEvidenceKind,
    GateRequirement,
    GateVerdict,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.service import (
    ActiveReleaseState,
    BoundContext,
    GitPreflightState,
    LifecycleCommandStatus,
    LifecyclePreflightInput,
    LifecyclePreflightService,
    PresenceState,
    RequiredHandoff,
    SpecsDoctorState,
)

HASH = "a" * 64


def _handoff(**overrides: object) -> dict[str, object]:
    doc: dict[str, object] = {
        "schema_version": "handoff-v1.1",
        "agent": "qa-engineer",
        "context": "dadaia-workspace",
        "release_id": "v0.1.15",
        "produced_at": "2026-06-18T12:00:00Z",
        "scope": "T-015-10",
        "metrics": {"commit_sha": "abc123", "task_group": "T-015-10"},
        "artifact": {"type": "report", "content_hash": HASH},
        "verdict": "APPROVED",
    }
    doc.update(overrides)
    return doc


def _handoff_requirement() -> GateRequirement:
    return GateRequirement(
        evidence_kind=GateEvidenceKind.HANDOFF,
        required_agent="qa-engineer",
        required_verdict=GateVerdict.APPROVED,
        release_id="v0.1.15",
        commit_sha="abc123",
        task_group="T-015-10",
        max_unresolved_severity="MEDIUM",
    )


def _input(**overrides: object) -> LifecyclePreflightInput:
    kwargs: dict[str, object] = {
        "context": "dadaia-workspace",
        "release_id": "v0.1.15",
        "expected_phase": LifecyclePhase.IMPLEMENTATION,
        "required_mode": "implementation",
        "current_step": "preflight",
        "binding": BoundContext(
            context="dadaia-workspace",
            release_id="v0.1.15",
            mode="implementation",
            session_id="sess-1",
        ),
        "active_release": ActiveReleaseState(
            release_id="v0.1.15",
            phase="IMPLEMENTATION",
        ),
        "git": GitPreflightState(upstream_branch="origin/feature/v0.1.15"),
        "specs_doctor": SpecsDoctorState(ok=True),
        "presence": PresenceState(mode="implementation", holder_session_id="sess-1"),
        "hygiene": HygieneCounters(),
        "required_handoffs": (),
    }
    kwargs.update(overrides)
    return LifecyclePreflightInput(**kwargs)  # type: ignore[arg-type]


def test_preflight_passes_with_evidence_and_accepts_bound_implementation_tokens() -> None:
    required = RequiredHandoff(
        source=".dadaia/handoff/dadaia-workspace/qa.handoff.json",
        document=_handoff(),
        requirement=_handoff_requirement(),
        artifact_hash=HASH,
        max_age_seconds=600,
        age_seconds=10,
    )

    result = LifecyclePreflightService().preflight(
        _input(required_handoffs=(required,)),
    )

    assert result.ok is True
    assert result.blocked is None
    assert len(result.evidence) == 1
    assert result.evidence[0].agent == "qa-engineer"

    bound_result = LifecyclePreflightService().preflight(
        _input(
            binding=BoundContext(
                context="dadaia-workspace",
                release_id="v0.1.15",
                mode="BOUND_IMPLEMENTATION",
                session_id="sess-1",
            ),
            presence=PresenceState(mode="BOUND_IMPLEMENTATION", holder_session_id="sess-1"),
        ),
    )

    assert bound_result.ok is True
    assert bound_result.blocked is None


@pytest.mark.parametrize(
    ("override", "reason", "command"),
    [
        ({"binding": None}, "context is not bound", "dadaia context bind"),
        (
            {
                "binding": BoundContext(
                    context="other",
                    release_id="v0.1.15",
                    mode="implementation",
                    session_id="sess-1",
                )
            },
            "wrong bound context",
            "dadaia context bind",
        ),
        (
            {
                "binding": BoundContext(
                    context="dadaia-workspace",
                    release_id="v0.1.14",
                    mode="implementation",
                    session_id="sess-1",
                )
            },
            "wrong bound release",
            "dadaia context bind",
        ),
        (
            {
                "binding": BoundContext(
                    context="dadaia-workspace",
                    release_id="v0.1.15",
                    mode="read",
                    session_id="sess-1",
                )
            },
            "wrong bound mode",
            "dadaia context bind",
        ),
        (
            {"active_release": ActiveReleaseState(release_id="v0.1.14", phase="implementation")},
            "active release mismatch",
            "dadaia context bind",
        ),
        (
            {"active_release": ActiveReleaseState(release_id="v0.1.15", phase="definition")},
            "active release phase mismatch",
            "dadaia reports workflow-status",
        ),
        (
            {"specs_doctor": SpecsDoctorState(ok=False, summary="SPEC missing")},
            "specs doctor failed",
            "dadaia specs doctor",
        ),
        (
            {"hygiene": HygieneCounters(cleanup_candidate_count=1)},
            "hygiene cleanup candidates present",
            "dadaia reports workflow-hygiene-clean --dry-run",
        ),
        (
            # v0.1.72 FR3: 13 candidates but only 12 protected — the ONE unprotected
            # candidate still blocks (the gate keeps its teeth for reclaimable waste).
            {"hygiene": HygieneCounters(cleanup_candidate_count=13, protected_residual_count=12)},
            "hygiene cleanup candidates present",
            "dadaia reports workflow-hygiene-clean --dry-run",
        ),
        (
            {"hygiene": HygieneCounters(malformed_handoff_count=1)},
            "malformed handoffs present",
            "dadaia reports workflow-hygiene-status --json",
        ),
    ],
)
def test_preflight_failures_return_typed_blocked_state(
    override: dict[str, object],
    reason: str,
    command: str,
) -> None:
    """v0.1.78 T-C / FR-C: EVERY blocked reason carries a non-null, actionable
    ``operator_command`` — no site defaults to ``None`` and leaves the operator guessing
    the next command. Parametrized over every ``_blocked(...)`` call site in
    ``LifecyclePreflightService.preflight`` (bug
    ``split-cleanup-engines-strand-stale-step-payloads``, absorbed backlog
    ``preflight-block-reasons-missing-operator-command``).
    """
    result = LifecyclePreflightService().preflight(_input(**override))

    assert result.ok is False
    assert result.blocked is not None
    assert result.blocked.reason == reason
    assert result.blocked.blocked_at_step == "preflight"
    assert result.blocked.resume_token == "dadaia-workspace:v0.1.15:preflight"
    assert result.blocked.operator_command is not None, (
        f"blocked reason {reason!r} must carry a non-null operator_command"
    )
    assert result.blocked.operator_command.startswith(command)


# ---------------------------------------------------------------------------
# Sibling presence can never block a lifecycle verb.
# ---------------------------------------------------------------------------


def test_preflight_never_blocks_on_sibling_mode() -> None:
    result = LifecyclePreflightService().preflight(
        _input(presence=PresenceState(mode="read", holder_session_id="sess-1")),
    )

    assert result.ok is True, result.blocked
    assert result.blocked is None


def test_preflight_never_blocks_on_live_sibling_but_warns() -> None:
    result = LifecyclePreflightService().preflight(
        _input(
            presence=PresenceState(
                mode="implementation",
                holder_session_id="sess-2",
                live_foreign_holder=True,
            )
        ),
    )

    assert result.ok is True, result.blocked
    assert result.blocked is None
    assert any("sess-2" in w for w in result.warnings), result.warnings


def test_preflight_no_warning_when_no_foreign_holder() -> None:
    result = LifecyclePreflightService().preflight(_input())

    assert result.ok is True
    assert result.warnings == ()


@pytest.mark.parametrize(
    ("git", "expected"),
    [
        (
            GitPreflightState(
                dirty_paths=("specs/releases/v0.2.5/SPEC.md",),
                upstream_branch="origin/main",
            ),
            (
                "[GIT] dirty worktree is advisory for lifecycle preflight; "
                "paths=specs/releases/v0.2.5/SPEC.md"
            ),
        ),
        (
            GitPreflightState(upstream_branch=None),
            "[GIT] missing upstream branch is advisory for lifecycle preflight",
        ),
        (
            GitPreflightState(upstream_branch="origin/main", unpushed_commit_count=2),
            "[GIT] unpushed commits are advisory for lifecycle preflight; count=2",
        ),
    ],
)
def test_git_non_clean_states_warn_instead_of_blocking(
    git: GitPreflightState,
    expected: str,
) -> None:
    result = LifecyclePreflightService().preflight(_input(git=git))

    assert result.ok is True
    assert result.blocked is None
    assert any(warning.startswith(expected) for warning in result.warnings)


def test_preflight_blocks_when_required_handoff_gate_fails() -> None:
    required = RequiredHandoff(
        source=".dadaia/handoff/dadaia-workspace/qa.handoff.json",
        document=_handoff(metrics={"commit_sha": "wrong", "task_group": "T-015-10"}),
        requirement=_handoff_requirement(),
        artifact_hash=HASH,
        max_age_seconds=600,
        age_seconds=10,
    )

    result = LifecyclePreflightService().preflight(
        _input(required_handoffs=(required,)),
    )

    assert result.ok is False
    assert result.blocked is not None
    assert result.blocked.reason == "required handoff gate failed"
    assert result.blocked.detail["handoff"] == ".dadaia/handoff/dadaia-workspace/qa.handoff.json"
    # v0.1.78 T-C / FR-C: this site used to default operator_command=None.
    assert result.blocked.operator_command is not None
    assert result.blocked.operator_command.startswith("dadaia reports")


# ---------------------------------------------------------------------------
# T-66-07 (FR6) — resume_run reports the real persisted run status (AC6.1/AC6.2)
# ---------------------------------------------------------------------------


class _FakeRunStore:
    """Minimal LifecycleRunStore fake — resume() returns a fixed run (AC6 unit level)."""

    def __init__(self, run: LifecycleRun) -> None:
        self._run = run

    def save(self, run: LifecycleRun) -> None:  # pragma: no cover - unused here
        raise NotImplementedError

    def load(self, run_id: str) -> LifecycleRun | None:  # pragma: no cover - unused here
        raise NotImplementedError

    def resume(self, run_id: str) -> LifecycleRun:
        return self._run

    def list_runs(self) -> list[LifecycleRun]:  # pragma: no cover - unused here
        raise NotImplementedError


def _run(
    *,
    status: LifecycleRunStatus,
    blocked: BlockedState | None = None,
) -> LifecycleRun:
    return LifecycleRun(
        run_id="run-1",
        context="dadaia-workspace",
        release_id="v0.1.66",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=status,
        current_step="implement",
        blocked=blocked,
    )


def test_resume_run_reports_blocked_with_real_reason_ac61() -> None:
    """AC6.1: a persisted BLOCKED run yields a BLOCKED command result carrying the
    run's own blocked.reason — never the unconditional OK."""
    blocked = BlockedState(
        reason="agent result missing artifact evidence",
        blocked_at_step="implement",
    )
    store = _FakeRunStore(_run(status=LifecycleRunStatus.BLOCKED, blocked=blocked))

    result = LifecyclePreflightService().resume_run(store, "run-1")

    assert result.status is LifecycleCommandStatus.BLOCKED
    assert "agent result missing artifact evidence" in result.message
    assert result.blocked is not None
    assert result.blocked.reason == "agent result missing artifact evidence"


@pytest.mark.parametrize(
    "status",
    [LifecycleRunStatus.RUNNING, LifecycleRunStatus.COMPLETED, LifecycleRunStatus.PENDING],
)
def test_resume_run_still_reports_ok_for_non_blocked_status_ac62(
    status: LifecycleRunStatus,
) -> None:
    """AC6.2: no regression for the already-correct non-blocked case."""
    store = _FakeRunStore(_run(status=status))

    result = LifecyclePreflightService().resume_run(store, "run-1")

    assert result.status is LifecycleCommandStatus.OK
    assert result.message == "resumed run-1"


def test_preflight_passes_when_all_cleanup_candidates_are_protected() -> None:
    """v0.1.72 FR3 (bug ``hygiene-preflight-blocks-protected-residuals``): candidates the
    cleaner itself protects (``current_release_evidence``) are NOT reclaimable waste — a
    gate must never require deleting evidence the deleter refuses to delete. The
    reporter's exact remote state: 12 candidates, all 12 protected ⇒ preflight passes."""
    result = LifecyclePreflightService().preflight(
        _input(hygiene=HygieneCounters(cleanup_candidate_count=12, protected_residual_count=12))
    )

    assert result.ok is True, result.blocked
    assert result.blocked is None
