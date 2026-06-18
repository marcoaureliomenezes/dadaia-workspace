"""Unit tests for lifecycle run-state stores."""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.lifecycle import (
    BlockedState,
    LifecyclePhase,
    LifecycleRun,
    LifecycleRunStatus,
)
from dadaia_workspace.features.lifecycle.run_store import LifecycleRunStoreError
from dadaia_workspace.infrastructure.json_lifecycle_run_store import JsonLifecycleRunStore


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / ".dadaia").mkdir()
    return tmp_path


def _run(
    run_id: str = "run-1",
    *,
    status: LifecycleRunStatus = LifecycleRunStatus.RUNNING,
    blocked: BlockedState | None = None,
) -> LifecycleRun:
    return LifecycleRun(
        run_id=run_id,
        context="dadaia-workspace",
        release_id="v0.1.15",
        command="implement",
        phase=LifecyclePhase.IMPLEMENTATION,
        status=status,
        current_step="preflight",
        expected_artifacts=(".dadaia/handoff/dadaia-workspace/qa.handoff.json",),
        idempotency_key="idem-1",
        blocked=blocked,
    )


def test_json_store_persists_under_canonical_states_lifecycle(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    run = _run()

    store.save(run)

    assert store.root == workspace / ".dadaia" / "states" / "lifecycle"
    assert (store.root / "run-1.json").is_file()
    assert store.load("run-1") == run


def test_json_store_can_persist_under_runs_lifecycle(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace, location="runs")
    run = _run("run-2")

    store.save(run)

    assert store.root == workspace / ".dadaia" / "runs" / "lifecycle"
    assert store.load("run-2") == run


def test_resume_is_idempotent_and_does_not_rewrite_state(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    blocked = BlockedState(
        reason="push requires operator",
        blocked_at_step="push",
        resume_token="resume-1",
        operator_command="git push",
    )
    run = _run(status=LifecycleRunStatus.BLOCKED, blocked=blocked)
    store.save(run)
    state_path = store.root / "run-1.json"
    before = state_path.read_text(encoding="utf-8")

    first = store.resume("run-1")
    second = store.resume("run-1")

    assert first == run
    assert second == run
    assert state_path.read_text(encoding="utf-8") == before


def test_save_replaces_existing_run_state(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    store.save(_run(status=LifecycleRunStatus.RUNNING))
    replacement = _run(status=LifecycleRunStatus.COMPLETED)

    store.save(replacement)

    assert store.load("run-1") == replacement


def test_missing_resume_raises_actionable_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)

    with pytest.raises(LifecycleRunStoreError, match="not found") as exc:
        store.resume("missing")

    assert "missing.json" in str(exc.value)


def test_corrupt_run_state_raises_actionable_error(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    state = workspace / ".dadaia" / "states" / "lifecycle" / "run-1.json"
    state.parent.mkdir(parents=True)
    state.write_text("{not json", encoding="utf-8")

    with pytest.raises(LifecycleRunStoreError, match="corrupt lifecycle run state") as exc:
        JsonLifecycleRunStore(workspace).load("run-1")

    assert str(state) in str(exc.value)


def test_invalid_run_id_rejects_path_traversal(tmp_path: Path) -> None:
    store = JsonLifecycleRunStore(_workspace(tmp_path))

    with pytest.raises(LifecycleRunStoreError, match="invalid lifecycle run id"):
        store.load("../escape")


def test_refuses_to_create_dadaia_inside_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    with pytest.raises(LifecycleRunStoreError, match="repository tree"):
        JsonLifecycleRunStore(repo_root)


def test_refuses_repo_root_even_when_dadaia_already_exists(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".dadaia").mkdir()

    with pytest.raises(LifecycleRunStoreError, match="repository tree"):
        JsonLifecycleRunStore(repo_root)


def test_refuses_subdirectory_inside_repo_tree(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    nested = repo_root / "src" / "pkg"
    nested.mkdir(parents=True)
    (repo_root / ".git").mkdir()

    with pytest.raises(LifecycleRunStoreError, match="repository tree"):
        JsonLifecycleRunStore(nested)


def test_refuses_subdirectory_inside_repo_tree_even_with_nested_dadaia(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    nested = repo_root / "src" / "pkg"
    nested.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (nested / ".dadaia").mkdir()

    with pytest.raises(LifecycleRunStoreError, match="repository tree"):
        JsonLifecycleRunStore(nested)
