"""A lifecycle verb must not return leaving the run claiming to still be going.

Three separate reports are the same class arriving by different routes:

* ``r11-release-definition-exits-success-interrupted`` — exit 0, run persisted running;
* ``r15-release-definition-running-after-accepted-draft`` — accepted step, then running
  with no reason and no remedy;
* ``r20-release-definition-returns-success-while-running`` — returned while status stayed
  running at ``definition_draft``, and the printed recovery reproduced the condition.

Each earlier fix patched the route it was reported on. A class that keeps returning
through new routes needs a CHOKEPOINT, not another patch — so whatever happened inside
(completion, block, an exception that escaped, a worker that never answered), the command
now seals a still-RUNNING run into a BLOCKED one carrying a diagnosis and a command.

Terminal states are untouched. Only the ambiguous one is sealed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.cli.commands.lifecycle import _seal_non_terminal_run
from dadaia_workspace.core.models.lifecycle import (
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.unit


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


def test_a_running_run_is_sealed_into_a_blocked_one(workspace: Path) -> None:
    _save(workspace, "r-run", LifecycleRunStatus.RUNNING, "definition_draft")

    reason = _seal_non_terminal_run(workspace, "r-run")

    assert reason is not None and "definition_draft" in reason
    sealed = JsonLifecycleRunStore(workspace).load("r-run")
    assert sealed is not None
    assert sealed.status is LifecycleRunStatus.BLOCKED
    assert sealed.blocked is not None
    assert sealed.blocked.blocked_at_step == "definition_draft"
    assert "lifecycle status --run-id r-run" in (sealed.blocked.operator_command or "")


@pytest.mark.parametrize(
    "terminal",
    [LifecycleRunStatus.COMPLETED, LifecycleRunStatus.FAILED, LifecycleRunStatus.BLOCKED],
)
def test_a_terminal_run_is_left_exactly_as_it_is(workspace: Path, terminal) -> None:
    """The seal resolves ambiguity; it must never overwrite a decided outcome."""
    _save(workspace, "r-done", terminal, "close")

    assert _seal_non_terminal_run(workspace, "r-done") is None
    kept = JsonLifecycleRunStore(workspace).load("r-done")
    assert kept is not None and kept.status is terminal


def test_an_unknown_run_is_not_invented(workspace: Path) -> None:
    assert _seal_non_terminal_run(workspace, "never-existed") is None
