"""Unit tests for lifecycle run-state stores.

Repo-root refusal prevents ``.dadaia/`` inside repos — workspace-boundary law, kept as the
full fixture set as params.
"""

from __future__ import annotations

import json as _json
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
    (tmp_path / ".dadaia").mkdir(parents=True, exist_ok=True)
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


def test_json_store_persists_under_canonical_states_lifecycle_and_load_round_trips(
    tmp_path: Path,
) -> None:
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    run = _run()

    store.save(run)

    assert store.root == workspace / ".dadaia" / "states" / "lifecycle"
    assert (store.root / "run-1.json").is_file()
    assert store.load("run-1") == run

    # Positive contrast for the repo-root refusal matrix below: a genuine self-hosting
    # workspace root (carrying its OWN .git AND .dadaia AND repos/) is allowed.
    self_hosting = tmp_path / "self-hosting-workspace"
    self_hosting.mkdir()
    (self_hosting / ".git").mkdir()
    (self_hosting / ".dadaia" / "states").mkdir(parents=True)
    (self_hosting / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (self_hosting / "repos").mkdir()
    self_hosting_store = JsonLifecycleRunStore(self_hosting)
    assert self_hosting_store.root == self_hosting / ".dadaia" / "states" / "lifecycle"


# ---------------------------------------------------------------------------
# ① legacy back-compat param: no-workflow_policy / no-workflow_steps keys still load
# ---------------------------------------------------------------------------


def _legacy_no_workflow_policy() -> dict[str, object]:
    return {
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


def _legacy_no_workflow_steps() -> dict[str, object]:
    return {
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


def test_legacy_back_compat_matrix(tmp_path: Path) -> None:
    """M1 (T-28-A-05): a literal old-format record with NO 'workflow_policy' key still
    loads; A27 (T-30-D-04): NO 'workflow_steps' key still loads, yielding an empty ledger.
    The 'lifecycle-run-v1' schema literal is unchanged in both cases."""
    workspace = _workspace(tmp_path)
    store = JsonLifecycleRunStore(workspace)
    store.root.mkdir(parents=True, exist_ok=True)

    (store.root / "legacy-1.json").write_text(
        _json.dumps(_legacy_no_workflow_policy(), indent=2, sort_keys=True), encoding="utf-8"
    )
    loaded1 = store.load("legacy-1")
    assert loaded1 is not None
    assert loaded1.run_id == "legacy-1"
    assert loaded1.workflow_policy is None

    (store.root / "legacy-2.json").write_text(
        _json.dumps(_legacy_no_workflow_steps(), indent=2, sort_keys=True), encoding="utf-8"
    )
    loaded2 = store.load("legacy-2")
    assert loaded2 is not None
    assert len(loaded2.workflow_steps) == 0


# ---------------------------------------------------------------------------
# ② ledger persists atomically + runs-location root
# ---------------------------------------------------------------------------


def test_ledger_persists_atomically_and_runs_location_root(tmp_path: Path) -> None:
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

    # The alternate 'runs' location root also persists correctly.
    runs_store = JsonLifecycleRunStore(_workspace(tmp_path / "runs-variant"), location="runs")
    runs_store.save(_run("run-2"))
    assert runs_store.root == (tmp_path / "runs-variant") / ".dadaia" / "runs" / "lifecycle"
    assert runs_store.load("run-2") == _run("run-2")


# ---------------------------------------------------------------------------
# ③ error param: resume idempotent / save-replaces / missing-resume / corrupt / traversal /
#    list_runs-skips-corrupt
# ---------------------------------------------------------------------------


def test_resume_idempotent_save_replaces_list_skips_corrupt_and_error_matrix(
    tmp_path: Path,
) -> None:
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

    replacement = _run(status=LifecycleRunStatus.COMPLETED)
    store.save(replacement)
    assert store.load("run-1") == replacement

    empty_store = JsonLifecycleRunStore(_workspace(tmp_path / "empty"))
    assert empty_store.list_runs() == []

    multi_store = JsonLifecycleRunStore(_workspace(tmp_path / "multi"))
    multi_store.save(_run("run-a"))
    multi_store.save(_run("run-b"))
    assert {r.run_id for r in multi_store.list_runs()} == {"run-a", "run-b"}

    # A corrupt run JSON must not break the panel run-history listing — it is skipped.
    corrupt_store = JsonLifecycleRunStore(_workspace(tmp_path / "corrupt"))
    corrupt_store.save(_run("run-ok"))
    corrupt_store.root.mkdir(parents=True, exist_ok=True)
    (corrupt_store.root / "run-bad.json").write_text("{not json", encoding="utf-8")
    assert [r.run_id for r in corrupt_store.list_runs()] == ["run-ok"]

    # error param: missing resume / corrupt state / path traversal.
    missing_workspace = _workspace(tmp_path / "missing")
    with pytest.raises(LifecycleRunStoreError, match="not found") as missing_exc:
        JsonLifecycleRunStore(missing_workspace).resume("missing")
    assert "missing.json" in str(missing_exc.value)

    corrupt_workspace = _workspace(tmp_path / "corrupt-state")
    state = corrupt_workspace / ".dadaia" / "states" / "lifecycle" / "run-1.json"
    state.parent.mkdir(parents=True)
    state.write_text("{not json", encoding="utf-8")
    with pytest.raises(LifecycleRunStoreError, match="corrupt lifecycle run state") as corrupt_exc:
        JsonLifecycleRunStore(corrupt_workspace).load("run-1")
    assert str(state) in str(corrupt_exc.value)

    traversal_workspace = _workspace(tmp_path / "traversal")
    with pytest.raises(LifecycleRunStoreError, match="invalid lifecycle run id"):
        JsonLifecycleRunStore(traversal_workspace).load("../escape")


# ---------------------------------------------------------------------------
# ④ repo-root refusal param (6 tree shapes) + self-hosting-workspace allowed
# ---------------------------------------------------------------------------


def _plain_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()
    return repo_root


def _repo_root_with_dadaia(tmp_path: Path) -> Path:
    repo_root = _plain_repo_root(tmp_path)
    (repo_root / ".dadaia").mkdir()
    return repo_root


def _repo_root_with_dadaia_and_repos(tmp_path: Path) -> Path:
    repo_root = _repo_root_with_dadaia(tmp_path)
    (repo_root / "repos").mkdir()
    return repo_root


def _nested_subdirectory(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    nested = repo_root / "src" / "pkg"
    nested.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    return nested


def _nested_subdirectory_with_dadaia(tmp_path: Path) -> Path:
    nested = _nested_subdirectory(tmp_path)
    (nested / ".dadaia").mkdir()
    return nested


_REFUSAL_CASES = (
    ("plain-repo-root", _plain_repo_root),
    ("repo-root-with-dadaia", _repo_root_with_dadaia),
    ("repo-root-with-dadaia-and-repos-no-sentinel", _repo_root_with_dadaia_and_repos),
    ("nested-subdirectory", _nested_subdirectory),
    ("nested-subdirectory-with-dadaia", _nested_subdirectory_with_dadaia),
)


@pytest.mark.parametrize(
    "build_root", [c[1] for c in _REFUSAL_CASES], ids=[c[0] for c in _REFUSAL_CASES]
)
def test_repo_root_refusal_matrix(tmp_path: Path, build_root) -> None:
    target = build_root(tmp_path)
    with pytest.raises(LifecycleRunStoreError, match="repository tree"):
        JsonLifecycleRunStore(target)
