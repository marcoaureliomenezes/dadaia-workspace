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


def test_json_store_loads_old_format_record_without_workflow_policy(tmp_path: Path) -> None:
    # M1 (T-28-A-05): a literal old-format record — current 'lifecycle-run-v1' schema,
    # NO 'workflow_policy' key — must still load. The schema version literal is unchanged.
    import json as _json

    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    store.root.mkdir(parents=True, exist_ok=True)
    legacy_payload = {
        "schema_version": "lifecycle-run-v1",
        "run": {
            "run_id": "legacy-1",
            "context": "dadaia-workspace",
            "release_id": "v0.1.15",
            "command": "implement",
            "phase": "implementation",
            "status": "running",
            "current_step": "implement",
            "expected_artifacts": [],
            "idempotency_key": "idem-1",
            "blocked": None,
            "injected_context": [],
        },
    }
    (store.root / "legacy-1.json").write_text(
        _json.dumps(legacy_payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    loaded = store.load("legacy-1")
    assert loaded is not None
    assert loaded.run_id == "legacy-1"
    assert loaded.workflow_policy is None


def test_json_store_loads_old_format_record_without_workflow_steps(tmp_path: Path) -> None:
    # A27 (T-30-D-04): an old-format record with NO 'workflow_steps' key still loads,
    # yielding an empty ledger. The 'lifecycle-run-v1' schema literal is unchanged.
    import json as _json

    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    store.root.mkdir(parents=True, exist_ok=True)
    legacy_payload = {
        "schema_version": "lifecycle-run-v1",
        "run": {
            "run_id": "legacy-2",
            "context": "dadaia-workspace",
            "release_id": "v0.1.29",
            "command": "release_definition",
            "phase": "release_definition",
            "status": "running",
            "current_step": "release_scope",
            "expected_artifacts": [],
            "idempotency_key": "idem-1",
            "blocked": None,
            "injected_context": [],
            "workflow_policy": None,
            # deliberately NO 'workflow_steps' key.
        },
    }
    (store.root / "legacy-2.json").write_text(
        _json.dumps(legacy_payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    loaded = store.load("legacy-2")
    assert loaded is not None
    assert len(loaded.workflow_steps) == 0


def test_json_store_persists_workflow_steps_ledger(tmp_path: Path) -> None:
    # A18 (T-30-D-04): the workflow-step ledger is persisted atomically as part of the run
    # record (LifecycleRun.to_dict serialises it; the store's temp+rename is atomic).
    from dadaia_workspace.core.models.workflow_handoff import (
        WorkflowStepLedger,
        WorkflowStepRecord,
    )

    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    record = WorkflowStepRecord(
        run_id="run-led",
        producer_step="release_scope",
        attempt=0,
        output_schema="release-scope-handoff-v1",
        payload_ref=".dadaia/runs/lifecycle/run-led/steps/release_scope-attempt-0.step-payload.json",
        content_hash="b" * 64,
        produced_at="2026-06-27T12:00:00Z",
        declared_consumers=("spec_create",),
    )
    run = LifecycleRun(
        run_id="run-led",
        context="dadaia-workspace",
        release_id="v0.1.30",
        command="release_definition",
        phase=LifecyclePhase.RELEASE_DEFINITION,
        status=LifecycleRunStatus.RUNNING,
        current_step="release_scope",
        workflow_steps=WorkflowStepLedger(records=(record,)),
    )

    store.save(run)
    loaded = store.load("run-led")

    assert loaded is not None
    assert loaded == run
    assert loaded.workflow_steps.find("release_scope", 0) is not None


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


def test_list_runs_returns_empty_when_no_runs(tmp_path: Path) -> None:
    store = JsonLifecycleRunStore(_workspace(tmp_path))
    assert store.list_runs() == []


def test_list_runs_returns_every_persisted_run(tmp_path: Path) -> None:
    store = JsonLifecycleRunStore(_workspace(tmp_path))
    store.save(_run("run-a"))
    store.save(_run("run-b"))

    runs = store.list_runs()

    assert {r.run_id for r in runs} == {"run-a", "run-b"}


def test_list_runs_skips_corrupt_files_without_raising(tmp_path: Path) -> None:
    # A corrupt run JSON must not break the panel run-history listing — it is skipped.
    store = JsonLifecycleRunStore(_workspace(tmp_path))
    store.save(_run("run-ok"))
    store.root.mkdir(parents=True, exist_ok=True)
    (store.root / "run-bad.json").write_text("{not json", encoding="utf-8")

    runs = store.list_runs()

    assert [r.run_id for r in runs] == ["run-ok"]


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


def test_refuses_repo_root_with_dadaia_and_repos_but_no_workspace_sentinel(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    (repo_root / ".dadaia").mkdir()
    (repo_root / "repos").mkdir()

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


def test_allows_self_hosting_workspace_root_with_git_and_dadaia(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / ".git").mkdir()
    (workspace / ".dadaia" / "states").mkdir(parents=True)
    (workspace / ".dadaia" / "states" / "spec_contexts.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (workspace / "repos").mkdir()

    store = JsonLifecycleRunStore(workspace)

    assert store.root == workspace / ".dadaia" / "states" / "lifecycle"
