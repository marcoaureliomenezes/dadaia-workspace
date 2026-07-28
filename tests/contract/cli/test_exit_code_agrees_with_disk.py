"""A success exit code must agree with the run state on disk.

Bug ``r11-release-definition-exits-success-interrupted`` (consumer-side validator, R11):
``release-definition`` exited 0 after an accepted ``definition_draft`` while the run
persisted as ``running`` — the in-memory result said completed, the store said
interrupted. Twice, reproducibly.

An exit code that disagrees with disk is worse than a plain failure: the caller believes
the step is done and moves on, and the next command trips over a run nobody knows is
unfinished. Disk wins, because disk is what every later step and every operator reads.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.cli.commands.lifecycle import _persisted_disagrees_with_success
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.contract


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, skip_assets=True, harnesses=())
    return tmp_path


def _save(workspace: Path, run_id: str, status: LifecycleRunStatus, step: str) -> None:
    JsonLifecycleRunStore(workspace).save(
        LifecycleRun(
            run_id=run_id,
            command="release_definition",
            context="ctx",
            release_id="v0.1.0",
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=status,
            current_step=step,
            expected_artifacts=(),
            idempotency_key="idem",
        )
    )


def test_a_run_left_running_refuses_the_success_verdict(workspace: Path) -> None:
    _save(workspace, "r-run", LifecycleRunStatus.RUNNING, "definition_draft")

    message = _persisted_disagrees_with_success(workspace, "r-run")

    assert message is not None, "the CLI would have reported OK for an unfinished run"
    assert "RUNNING" in message and "definition_draft" in message
    assert "lifecycle status --run-id r-run" in message, "must point at the inspection verb"


def test_a_completed_run_is_left_alone(workspace: Path) -> None:
    _save(workspace, "r-done", LifecycleRunStatus.COMPLETED, "definition_commit_gate")
    assert _persisted_disagrees_with_success(workspace, "r-done") is None


def test_an_unreadable_store_never_masks_the_commands_own_result(workspace: Path) -> None:
    """The check is a backstop; it must not invent a failure when it cannot read."""
    assert _persisted_disagrees_with_success(workspace, "never-persisted") is None
