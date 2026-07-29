"""What the command told the operator and what the ledger says must be the same thing.

Bug ``r22-release-definition-completes-with-consumes-bind-error`` (validator R22 / R-05):
a real release-definition run persisted ``definition_commit_gate:ok`` and
``lifecycle status`` reported ``COMPLETED``, while the command itself printed ``BLOCKED``
and exited 3 because the SPEC's ``**Consumes:**`` slug was not a live backlog item.

Both halves were individually right. The workflow did complete; the post-step did fail;
the command correctly refused to call that a success. What was missing is that nothing
wrote the refusal back. So the operator was told BLOCKED, went to look, and every
subsequent reader — ``lifecycle status``, the panel, the next preflight — said the run
had finished cleanly. Between the two, the ledger wins by default, because it is what
tooling reads.

``_persisted_disagrees_with_success`` already guarded the other direction (the command
claims success, the ledger says otherwise). This is the mirror, and the mirror is the
worse one: a false COMPLETED lets the next phase start on a definition that never
consumed its backlog.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.cli.commands.lifecycle import _seal_post_step_failure
from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.unit

_ERROR = "ConsumesBindError: **Consumes:** slug 'none' is not a live backlog item"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, skip_assets=True, harnesses=())
    return tmp_path


def _save(workspace: Path, run_id: str, status: LifecycleRunStatus) -> None:
    JsonLifecycleRunStore(workspace).save(
        LifecycleRun(
            run_id=run_id,
            command="release_definition",
            context="ctx",
            release_id="v0.1.0",
            phase=LifecyclePhase.IMPLEMENTATION,
            status=status,
            current_step="definition_commit_gate",
            expected_artifacts=(),
            idempotency_key="idem",
        )
    )


def test_a_completed_run_whose_post_step_failed_is_sealed_blocked(workspace: Path) -> None:
    _save(workspace, "r-05", LifecycleRunStatus.COMPLETED)

    _seal_post_step_failure(workspace, "r-05", _ERROR)

    sealed = JsonLifecycleRunStore(workspace).load("r-05")
    assert sealed is not None
    assert sealed.status is LifecycleRunStatus.FAILED, (
        "the command told the operator BLOCKED and exited 3 while the ledger every other "
        "reader consults still said the run completed"
    )
    assert sealed.blocked is not None
    assert "Consumes" in sealed.blocked.reason
    assert sealed.blocked.blocked_at_step == "definition_commit_gate"


def test_the_seal_prescribes_a_pasteable_command(workspace: Path) -> None:
    _save(workspace, "r-05b", LifecycleRunStatus.COMPLETED)

    _seal_post_step_failure(workspace, "r-05b", _ERROR)

    sealed = JsonLifecycleRunStore(workspace).load("r-05b")
    assert sealed is not None and sealed.blocked is not None
    remedy = sealed.blocked.operator_command or ""
    assert remedy.startswith("dadaia lifecycle release-definition"), remedy
    assert "--run-id r-05b" in remedy


def test_the_seal_does_not_fight_the_monotonicity_rule(workspace: Path) -> None:
    """FAILED, never BLOCKED — and the reason is not cosmetic.

    The store refuses to move a run OUT of a terminal state, which is what makes
    concurrent drivers safe to accept rather than something to prevent
    (``r14-implementation-recovery-reverts-terminal-run``). Sealing to BLOCKED would have
    been silently dropped by that rule and this whole guard would have done nothing — the
    exact shape of a fix that looks applied and is not.
    """
    _save(workspace, "r-05d", LifecycleRunStatus.COMPLETED)

    _seal_post_step_failure(workspace, "r-05d", _ERROR)

    sealed = JsonLifecycleRunStore(workspace).load("r-05d")
    assert sealed is not None
    assert sealed.status is not LifecycleRunStatus.COMPLETED, "the seal was silently dropped"
    assert sealed.status in {LifecycleRunStatus.FAILED}


def test_a_run_that_is_already_blocked_is_left_alone(workspace: Path) -> None:
    """A recorded block is the more specific diagnosis; never overwrite it with this one."""
    store = JsonLifecycleRunStore(workspace)
    store.save(
        LifecycleRun(
            run_id="r-05c",
            command="release_definition",
            context="ctx",
            release_id="v0.1.0",
            phase=LifecyclePhase.BLOCKED,
            status=LifecycleRunStatus.BLOCKED,
            current_step="definition_review",
            expected_artifacts=(),
            idempotency_key="idem",
            blocked=BlockedState(
                reason="the review rejected the plan on its dependency table",
                blocked_at_step="definition_review",
                operator_command="dadaia lifecycle release-definition --run-id r-05c",
            ),
        )
    )
    before = store.load("r-05c")

    _seal_post_step_failure(workspace, "r-05c", _ERROR)

    after = store.load("r-05c")
    assert after is not None and before is not None
    assert after.blocked == before.blocked


def test_an_unknown_run_is_not_invented(workspace: Path) -> None:
    _seal_post_step_failure(workspace, "never-existed", _ERROR)
    assert JsonLifecycleRunStore(workspace).load("never-existed") is None
