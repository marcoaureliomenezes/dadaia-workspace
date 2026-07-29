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
    # The remedy is the RESUME of this run's own workflow, pasteable verbatim — not a
    # pointer to another verb the operator would then have to read and act on.
    remedy = sealed.blocked.operator_command or ""
    assert remedy.startswith("dadaia lifecycle release-definition"), remedy
    assert "--run-id r-run" in remedy and "--resume-from definition_draft" in remedy


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


def test_the_status_verb_seals_a_run_whose_driver_was_killed(workspace: Path) -> None:
    """Bug r21-killed-driver-leaves-running-ledger.

    The end-of-verb chokepoint cannot fire when the driver is KILLED — no in-process code
    runs at all. I knew that and wrote a test SAYING so, then relied on `lifecycle status`
    to merely describe the wreck. The validator killed a driver and found exactly that: a
    ledger stuck on running, and a recovery in prose.

    The verb that runs AFTER the death is the only one that can still resolve it, so it
    now seals as well as reports.
    """
    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app

    _save(workspace, "killed", LifecycleRunStatus.RUNNING, "definition_draft")

    result = CliRunner().invoke(
        app, ["lifecycle", "status", "--run-id", "killed", "--workspace", str(workspace)]
    )

    assert result.exit_code == 0, result.output
    sealed = JsonLifecycleRunStore(workspace).load("killed")
    assert sealed is not None and sealed.status is LifecycleRunStatus.BLOCKED, (
        "inspecting a killed run described it and left it ambiguous on disk"
    )
    assert "dadaia lifecycle release-definition" in result.output, (
        f"the recovery must be a pasteable command, not prose:\n{result.output}"
    )
    assert "--resume-from definition_draft" in result.output


@pytest.mark.parametrize(
    ("command", "verb"),
    [
        ("pipeline", "implementation-reviews"),
        ("release_definition", "release-definition"),
        ("backlog_definition", "backlog-definition"),
        ("audit", "audit"),
    ],
)
def test_the_recovery_names_the_verb_that_actually_ran(command: str, verb: str) -> None:
    """Bug r22-lifecycle-status-pipeline-recovery-wrong-verb — a regression I introduced.

    The implementation workflow persists ``command="pipeline"``. My map did not carry it,
    so the fallback GUESSED and handed an implementation run a ``release-definition``
    command. A wrong command is worse than no command: the operator runs it, and it does
    something else entirely.
    """
    import types

    from dadaia_workspace.cli.commands.lifecycle import _resume_command_for

    run = types.SimpleNamespace(command=command, context="ctx", release_id="v0.1.0", run_id="rid")
    assert _resume_command_for(run, "step").startswith(f"dadaia lifecycle {verb} ")


def test_an_unknown_command_does_not_invent_a_verb() -> None:
    """Guessing is what caused the defect; the fallback must be real and runnable."""
    import types

    from dadaia_workspace.cli.commands.lifecycle import _resume_command_for

    run = types.SimpleNamespace(
        command="something-new", context="ctx", release_id="v0.1.0", run_id="rid"
    )
    assert _resume_command_for(run, "step") == "dadaia lifecycle status --run-id rid"


def test_the_seal_fires_even_when_the_body_raises(workspace: Path) -> None:
    """Bug r22-codex-sandbox-invalid-mode-traceback (the ledger half).

    The previous guard sat AFTER the workflow returned, so it never fired when the
    workflow RAISED — an invalid Codex sandbox mode aborted step two and left the ledger
    running with no block. Same class, yet another route; a guarantee that depends on the
    body succeeding is not a guarantee, which is what `finally` is for.
    """
    from dadaia_workspace.cli.commands.lifecycle import _sealing_run

    _save(workspace, "boom", LifecycleRunStatus.RUNNING, "backlog_author")

    with pytest.raises(RuntimeError):
        with _sealing_run(workspace, "boom"):
            raise RuntimeError("the worker blew up mid-step")

    sealed = JsonLifecycleRunStore(workspace).load("boom")
    assert sealed is not None and sealed.status is LifecycleRunStatus.BLOCKED
    assert sealed.blocked is not None and sealed.blocked.operator_command
