"""Compatibility exports for lifecycle run-store protocols."""

from __future__ import annotations

from dadaia_workspace.core.protocols.lifecycle_run_store import (
    LifecycleRunStore,
    LifecycleRunStoreError,
)

__all__ = [
    "LifecycleRunStore",
    "LifecycleRunStoreError",
    "emit_progress",
    "refuse_blocked_restart",
    "refuse_completed_rerun",
]


def refuse_completed_rerun(run_store: LifecycleRunStore, run_id: str) -> None:
    """Refuse to start a FRESH run over an already-COMPLETED run id.

    Shared idempotency guard for every workflow engine (bug
    completed-workflow-rerun-not-refused): a completed run is immutable history — a
    fresh invocation must take a fresh ``--run-id``. A BLOCKED run is guarded
    separately by :func:`refuse_blocked_restart`; only COMPLETED refuses here.
    """
    from dadaia_workspace.core.exceptions import CompletedRunRerunError
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus

    prior = run_store.load(run_id)
    if prior is not None and prior.status is LifecycleRunStatus.COMPLETED:
        raise CompletedRunRerunError(
            f"lifecycle run '{run_id}' already COMPLETED; re-running a completed run is "
            "refused. Pass a fresh --run-id for new work (a blocked run may be resumed "
            "with --resume-from)."
        )


def refuse_blocked_restart(run_store: LifecycleRunStore, run_id: str) -> None:
    """Refuse to silently RESTART a BLOCKED or interrupted RUNNING run id from step one.

    Re-running the identical command after a block is the most natural thing an operator
    does, and it used to discard the run's recorded block — its reason, its findings, and
    the ``operator_command`` prescribing the recovery — then re-execute from the first
    step. On a live run that also spends real worker budget re-doing accepted work
    (bug r10-release-resume-blocked-run-restarts-and-loses-remedy, reported by the
    consumer-side validator when a plan_review block vanished and the release restarted at
    spec_create).

    Starting over is still allowed; it just has to be deliberate — a fresh ``--run-id``.
    The refusal quotes the recorded remedy so the operator sees the resume command in the
    same breath as the refusal.
    """
    from dadaia_workspace.core.exceptions import BlockedRunRestartError
    from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus

    prior = run_store.load(run_id)
    if prior is None or prior.status not in (
        LifecycleRunStatus.BLOCKED,
        LifecycleRunStatus.RUNNING,
    ):
        return
    if prior.status is LifecycleRunStatus.RUNNING:
        # An INTERRUPTED run (driver killed, worker orphaned, machine died) is left
        # `running` with no block and therefore no remedy: the operator sees a run that
        # is not finished, not failed, and offers no guidance, and re-running the command
        # silently restarts from step one (bug r11-interrupt-leaves-release-run-running,
        # reported by the consumer-side validator). The recovery is the same as for a
        # block — resume from where it stopped — so say so.
        step = prior.current_step or "<step>"
        raise BlockedRunRestartError(
            f"lifecycle run {run_id!r} is still RUNNING at step {step!r} — it was "
            "interrupted before reaching a terminal state (a killed driver or an orphaned "
            "worker leaves this). Re-running it without --resume-from would restart from "
            "the first step and redo accepted work. Resume it: --resume-from "
            f"{step} — or pass a fresh --run-id to start over deliberately."
        )
    blocked = prior.blocked
    remedy = (blocked.operator_command if blocked else None) or (
        f"re-run with --resume-from {blocked.blocked_at_step}" if blocked else None
    )
    where = f" at step '{blocked.blocked_at_step}'" if blocked else ""
    raise BlockedRunRestartError(
        f"lifecycle run {run_id!r} is BLOCKED{where}; re-running it without --resume-from "
        "would restart from the first step and discard that block, its findings and its "
        "prescribed recovery. Resume it"
        + (f": {remedy}" if remedy else " with --resume-from <step>")
        + " — or pass a fresh --run-id to start over deliberately. Reason: "
        + ((blocked.reason if blocked else "") or "(none recorded)")
    )


def emit_progress(message: str) -> None:
    """One human progress line on STDERR (bug
    release-definition-codex-hangs-after-spec-create, visibility half): a live
    multi-minute workflow must never be silent — validators kill healthy workers.
    stdout stays machine-pure for --json consumers.
    """
    import sys

    print(f"[lifecycle] {message}", file=sys.stderr, flush=True)
