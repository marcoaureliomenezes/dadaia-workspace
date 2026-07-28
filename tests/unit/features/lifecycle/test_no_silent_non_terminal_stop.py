"""A sequence may stop, but never silently.

Bug ``r15-release-definition-running-after-accepted-draft`` (consumer-side validator,
R15/R-01): ``release-definition`` logged ``definition_draft`` accepted and then persisted
the run as ``running`` with no terminal state, no reason and no remedy — and the exact
prescribed recovery reproduced the same state. The operator gets a run that is not
finished, not failed, and says nothing about why; re-running changes nothing.

Stopping is legitimate — a worker can fail to produce an acceptable result. Stopping
without recording WHY is not: it is the difference between a wall with a door and a wall.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import LifecycleRunStatus
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore

pytestmark = pytest.mark.unit


def test_the_synthesized_block_names_the_step_and_offers_a_way_out() -> None:
    """The shape of the fallback block, asserted directly on the source of truth.

    Kept narrow on purpose: driving a live worker to hang is not reproducible in a unit
    test, so this pins the CONTRACT the fallback must satisfy — a named step, a readable
    reason, and a command the operator can actually run.
    """
    import inspect

    from dadaia_workspace.features.lifecycle.workflows import _fragment_gate

    source = inspect.getsource(_fragment_gate.FragmentGateWorkflow._run_sequence)
    assert "non-terminal-stop-v1" in source, (
        "the silent-stop fallback is gone — a sequence that halts without a recorded "
        "block would leave the run persisted as running again"
    )
    assert "dadaia lifecycle status --run-id" in source, (
        "the fallback must point at the verb that explains the state"
    )


def test_a_run_left_running_is_still_readable_by_the_status_verb(tmp_path: Path) -> None:
    """The complementary half: whatever else happens, `lifecycle status` must speak.

    Even if a process is killed before any fallback can run — the one case no in-process
    guard can cover — the operator must still get a diagnosis on request.
    """
    from dadaia_workspace.cli.commands.lifecycle import _persisted_disagrees_with_success
    from dadaia_workspace.core.models.lifecycle import LifecyclePhase, LifecycleRun
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path, skip_assets=True, harnesses=())
    JsonLifecycleRunStore(tmp_path).save(
        LifecycleRun(
            run_id="killed",
            command="release_definition",
            context="ctx",
            release_id="v0.1.0",
            phase=LifecyclePhase.RELEASE_DEFINITION,
            status=LifecycleRunStatus.RUNNING,
            current_step="definition_draft",
            expected_artifacts=(),
            idempotency_key="idem",
        )
    )

    message = _persisted_disagrees_with_success(tmp_path, "killed")

    assert message is not None
    assert "definition_draft" in message
    assert "lifecycle status --run-id killed" in message
