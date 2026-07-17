"""Compatibility exports for lifecycle run-store protocols."""

from __future__ import annotations

from dadaia_workspace.core.protocols.lifecycle_run_store import (
    LifecycleRunStore,
    LifecycleRunStoreError,
)

__all__ = ["LifecycleRunStore", "LifecycleRunStoreError", "refuse_completed_rerun"]


def refuse_completed_rerun(run_store: LifecycleRunStore, run_id: str) -> None:
    """Refuse to start a FRESH run over an already-COMPLETED run id.

    Shared idempotency guard for every workflow engine (bug
    completed-workflow-rerun-not-refused): a completed run is immutable history — a
    fresh invocation must take a fresh ``--run-id``. Restarting a BLOCKED/FAILED run id
    remains allowed (that is the documented recovery path); only COMPLETED refuses.
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
