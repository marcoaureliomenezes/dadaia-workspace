"""A finished run must not be un-finished by a late writer.

Bug ``r14-implementation-recovery-reverts-terminal-run`` (consumer-side validator, R14):
after implementation reported ``completed``, an orphaned driver from an earlier attempt
finished its own work and wrote the SAME run id back to ``running``. Recovery then blocked
with "active release mismatch" and ``ACTIVE.md`` regressed to ``release: none`` — a
finished release became an unfinished one, and the operator was left with a tree that
contradicted itself.

Last-writer-wins is right for most state and wrong for this: reaching a terminal state is
a fact, not an opinion. A straggler that was already obsolete when it started must not be
able to erase it. This is not a lock — nothing waits, nothing is refused to a caller doing
new work; it is monotonicity of one field, which is what makes concurrent drivers safe to
ACCEPT rather than something to prevent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

pytestmark = pytest.mark.unit


def _run(status: LifecycleRunStatus, step: str) -> LifecycleRun:
    return LifecycleRun(
        run_id="r-1",
        command="implementation_reviews",
        context="ctx",
        release_id="v0.1.0",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=status,
        current_step=step,
        expected_artifacts=(),
        idempotency_key="idem",
    )


def test_a_completed_run_cannot_be_reverted_to_running(tmp_path: Path) -> None:
    store = JsonLifecycleRunStore(tmp_path)
    store.save(_run(LifecycleRunStatus.COMPLETED, "close"))

    store.save(_run(LifecycleRunStatus.RUNNING, "implement"))

    reloaded = store.load("r-1")
    assert reloaded is not None
    assert reloaded.status is LifecycleRunStatus.COMPLETED, (
        "an orphaned driver un-finished a completed run; reaching a terminal state is a "
        "fact, not the latest opinion"
    )
    assert reloaded.current_step == "close", "the terminal step must survive too"


def test_a_running_run_still_advances_normally(tmp_path: Path) -> None:
    """Guard: monotonicity must not freeze a run that is legitimately progressing."""
    store = JsonLifecycleRunStore(tmp_path)
    store.save(_run(LifecycleRunStatus.RUNNING, "implement"))
    store.save(_run(LifecycleRunStatus.RUNNING, "review_combined"))
    store.save(_run(LifecycleRunStatus.COMPLETED, "close"))

    reloaded = store.load("r-1")
    assert reloaded is not None
    assert reloaded.status is LifecycleRunStatus.COMPLETED


def test_a_terminal_run_can_still_be_replaced_by_another_terminal_state(
    tmp_path: Path,
) -> None:
    """Terminal → terminal is a real transition (e.g. a closure that later fails audit).

    Only the un-finishing direction is refused; freezing every terminal record would make
    legitimate corrections impossible.
    """
    store = JsonLifecycleRunStore(tmp_path)
    store.save(_run(LifecycleRunStatus.COMPLETED, "close"))
    store.save(_run(LifecycleRunStatus.FAILED, "close"))

    reloaded = store.load("r-1")
    assert reloaded is not None
    assert reloaded.status is LifecycleRunStatus.FAILED
