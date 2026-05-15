"""Run-state persistence: atomicity, append-only events, idempotent resume."""

from pathlib import Path

from dadaia_workspace.core.models.run_state import (
    EventKind,
    RunEvent,
    RunManifest,
    RunStatus,
    StageState,
    StageStatus,
)
from dadaia_workspace.infrastructure.json_run_state_store import (
    JsonRunStateStore,
    make_run_id,
)


def _manifest(run_id: str) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        workflow_name="demo",
        workflow_version="0.1.0",
        context="ctx",
        runtime="cli",
        status=RunStatus.RUNNING,
        started_at="2026-01-01T00:00:00Z",
        finished_at=None,
        stages=(StageState(id="a", agent="product-engineer", status=StageStatus.PENDING),),
    )


def test_create_and_load(tmp_path: Path) -> None:
    store = JsonRunStateStore(tmp_path)
    run_id = make_run_id()
    store.create_run(_manifest(run_id))
    loaded = store.load_run(run_id)
    assert loaded.run_id == run_id
    assert loaded.stages[0].id == "a"


def test_events_append_only(tmp_path: Path) -> None:
    store = JsonRunStateStore(tmp_path)
    run_id = make_run_id()
    store.create_run(_manifest(run_id))
    for kind in (EventKind.STAGE_STARTED, EventKind.STAGE_COMPLETED):
        store.append_event(
            RunEvent(ts="2026-01-01T00:00:01Z", run_id=run_id, kind=kind, stage_id="a")
        )
    events = list(store.iter_events(run_id))
    assert [e.kind for e in events] == [EventKind.STAGE_STARTED, EventKind.STAGE_COMPLETED]


def test_atomic_update(tmp_path: Path) -> None:
    store = JsonRunStateStore(tmp_path)
    run_id = make_run_id()
    store.create_run(_manifest(run_id))
    updated = RunManifest(
        run_id=run_id,
        workflow_name="demo",
        workflow_version="0.1.0",
        context="ctx",
        runtime="cli",
        status=RunStatus.COMPLETED,
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:01:00Z",
        stages=(
            StageState(
                id="a",
                agent="product-engineer",
                status=StageStatus.COMPLETED,
                finished_at="2026-01-01T00:01:00Z",
            ),
        ),
    )
    store.update_manifest(updated)
    reloaded = store.load_run(run_id)
    assert reloaded.status == RunStatus.COMPLETED
    assert reloaded.finished_at == "2026-01-01T00:01:00Z"


def test_list_runs_returns_all(tmp_path: Path) -> None:
    store = JsonRunStateStore(tmp_path)
    store.create_run(_manifest(make_run_id()))
    store.create_run(_manifest(make_run_id()))
    assert len(store.list_runs()) == 2


def test_run_ids_are_unique() -> None:
    seen = {make_run_id() for _ in range(50)}
    assert len(seen) == 50
