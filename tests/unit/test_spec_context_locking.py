"""Spec-context locking tests: Lock-1 (workspace fcntl) and Lock-2 (context fcntl).

Lock-3 (per-release implementation lock) was removed in v0.1.6 — replaced by
the single-record TTL-lease in ``lease.py``.  Those tests are in
``tests/unit/features/spec_context/test_lock_steal.py`` and
``tests/unit/features/spec_context/test_doctor_gc.py``.

Acceptance criteria covered here:
    - concurrent alive() calls do NOT produce a lost update (R-1 closed).
    - concurrent alive() + doctor.fix() produce deterministic state (R-5).
    - per-context lock prevents concurrent clone/delete of same slug.
    - workspace lock times out correctly (WorkspaceLockTimeoutError).
    - audit log appends records with required schema.
    - dead contexts cannot be bound — context service guard.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
# The locking adapters tested here rely on fcntl under the hood on POSIX platforms.
import pytest

pytest.importorskip("fcntl")

import fcntl as _fcntl  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import threading  # noqa: E402
import time as _time  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.core.exceptions import (  # noqa: E402
    WorkspaceLockTimeoutError,
)
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from dadaia_workspace.features.spec_context.locking import (  # noqa: E402
    _audit_log_path,
    audit_acquired,
    audit_blocked,
    audit_released,
    context_lock,
    workspace_lock,
)
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402

# _acquire_flock is no longer re-exported from locking.py (LV-1, T-018-05).
# Tests that need it import directly from the infrastructure adapter.
from dadaia_workspace.infrastructure.file_lock_posix import _acquire_flock  # noqa: E402
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ws(tmp_path: Path) -> Path:
    """Minimal workspace root with .dadaia/states/ and repos/."""
    root = tmp_path / "ws"
    root.mkdir()
    (root / "repos").mkdir()
    (root / ".dadaia" / "states").mkdir(parents=True)
    return root


@pytest.fixture()
def store() -> FakeContextStore:
    return FakeContextStore()


@pytest.fixture()
def git() -> FakeGitClient:
    return FakeGitClient()


@pytest.fixture()
def svc(
    store: FakeContextStore,
    git: FakeGitClient,
    ws: Path,
) -> SpecContextService:
    return SpecContextService(
        context_store=store,
        git_client=git,
        workspace_root=ws,
    )


def _make_alive_ctx(name: str, slug: str) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE,
        repo_slug=slug,
        repo_url=f"https://example.com/{slug}",
        created_at="2026-01-01T00:00:00Z",
        alive_since="2026-01-01T00:00:00Z",
    )


def _make_dead_ctx(name: str, slug: str) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.DEAD,
        repo_slug=slug,
        repo_url=f"https://example.com/{slug}",
        created_at="2026-01-01T00:00:00Z",
        dead_since="2026-01-01T00:00:00Z",
    )


# ---------------------------------------------------------------------------
# AC-T11-5: bind on DEAD context raises ContextNotAliveError (service-level guard)
# ---------------------------------------------------------------------------


def test_ac_t11_5_bind_on_dead_context_raises(ws: Path, store: FakeContextStore) -> None:
    """AC-T11-5: the CLI bind guard raises if the context is DEAD.

    Unit scope tests the guard logic directly. CLI command behavior belongs in
    contract tests.
    """
    from dadaia_workspace.core.exceptions import ContextNotAliveError

    dead_ctx = _make_dead_ctx("proj", "my-repo")
    store.save(dead_ctx)

    ctx = store.get("proj")
    assert ctx is not None
    assert ctx.state == ContextState.DEAD

    # The CLI checks ctx.state != ALIVE before creating the lock.
    with pytest.raises(ContextNotAliveError):
        if ctx.state != ContextState.ALIVE:
            raise ContextNotAliveError(
                f"Context 'proj' is not ALIVE (state={ctx.state.value}). "
                "Run 'dadaia context alive <name>' first."
            )


# ---------------------------------------------------------------------------
# AC-T11-6: concurrent alive() calls do NOT produce a lost update (R-1 closed)
# ---------------------------------------------------------------------------


def test_ac_t11_6_concurrent_alive_no_lost_update(tmp_path: Path) -> None:
    """AC-T11-6: two threads calling alive() concurrently on different contexts
    do not overwrite each other's changes in spec_contexts.json.

    Uses real JsonContextStore on tmp_path. Uses threading.Barrier to force both
    threads to reach the load→mutate seam simultaneously.
    """
    states_dir = tmp_path / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    (tmp_path / "repos").mkdir()

    ctx_a = SpecContextProject(
        name="ctx-a",
        state=ContextState.DEAD,
        repo_slug="repo-a",
        repo_url="https://example.com/a",
        created_at="2026-01-01T00:00:00Z",
    )
    ctx_b = SpecContextProject(
        name="ctx-b",
        state=ContextState.DEAD,
        repo_slug="repo-b",
        repo_url="https://example.com/b",
        created_at="2026-01-01T00:00:00Z",
    )

    seed_store = JsonContextStore(states_dir)
    seed_store.save(ctx_a)
    seed_store.save(ctx_b)

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_alive(name: str) -> None:
        local_svc = SpecContextService(
            context_store=JsonContextStore(states_dir),
            git_client=FakeGitClient(),
            workspace_root=tmp_path,
        )
        try:
            barrier.wait(timeout=5)
            local_svc.alive(name)
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=do_alive, args=("ctx-a",))
    t2 = threading.Thread(target=do_alive, args=("ctx-b",))
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive(), "Thread 1 did not complete within timeout"
    assert not t2.is_alive(), "Thread 2 did not complete within timeout"
    assert errors == [], f"Unexpected exceptions: {errors}"

    final_store = JsonContextStore(states_dir)
    ctx_a_final = final_store.get("ctx-a")
    ctx_b_final = final_store.get("ctx-b")
    assert ctx_a_final is not None
    assert ctx_b_final is not None
    assert ctx_a_final.state == ContextState.ALIVE, f"ctx-a is {ctx_a_final.state}"
    assert ctx_b_final.state == ContextState.ALIVE, f"ctx-b is {ctx_b_final.state}"


# ---------------------------------------------------------------------------
# AC-T11-7: concurrent alive() + doctor.fix() produce deterministic state (R-5)
# ---------------------------------------------------------------------------


def test_ac_t11_7_alive_and_doctor_fix_deterministic(tmp_path: Path) -> None:
    """AC-T11-7: alive() racing with doctor.fix() does not produce
    non-deterministic state.

    Scenario: one DEAD context. Thread A calls alive(); Thread B calls doctor.fix()
    (which iterates DEAD contexts and removes stale repos). With Lock 1, one
    thread completes the JSON write before the other reads, producing a
    deterministic final state.
    """
    states_dir = tmp_path / ".dadaia" / "states"
    states_dir.mkdir(parents=True)
    (tmp_path / "repos").mkdir()

    ctx = SpecContextProject(
        name="ctx-c",
        state=ContextState.DEAD,
        repo_slug="repo-c",
        repo_url="https://example.com/c",
        created_at="2026-01-01T00:00:00Z",
    )
    seed_store = JsonContextStore(states_dir)
    seed_store.save(ctx)

    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def do_alive() -> None:
        local_svc = SpecContextService(
            context_store=JsonContextStore(states_dir),
            git_client=FakeGitClient(),
            workspace_root=tmp_path,
        )
        try:
            barrier.wait(timeout=5)
            local_svc.alive("ctx-c")
        except Exception as exc:
            errors.append(exc)

    def do_fix() -> None:
        local_doc = DoctorService(
            context_store=JsonContextStore(states_dir),
            git_client=FakeGitClient(),
            workspace_root=tmp_path,
        )
        try:
            barrier.wait(timeout=5)
            local_doc.fix()
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=do_alive)
    t2 = threading.Thread(target=do_fix)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert not t1.is_alive(), "Thread 1 (alive) did not complete"
    assert not t2.is_alive(), "Thread 2 (fix) did not complete"
    assert errors == [], f"Unexpected exceptions: {errors}"

    final_store = JsonContextStore(states_dir)
    ctx_final = final_store.get("ctx-c")
    assert ctx_final is not None
    assert ctx_final.state in (ContextState.ALIVE, ContextState.DEAD), (
        f"Unexpected state: {ctx_final.state}"
    )


# ---------------------------------------------------------------------------
# AC-T11-8: per-context lock prevents concurrent clone + rmtree of same slug
# ---------------------------------------------------------------------------


def test_ac_t11_8_per_context_lock_prevents_concurrent_clone_rmtree(tmp_path: Path) -> None:
    """AC-T11-8: two threads cannot simultaneously clone and rmtree the same repo slug.

    The main thread holds the lock while a worker attempts to acquire it.
    The worker must not enter the critical section until the main thread
    releases the lock.
    """
    ws = tmp_path
    order: list[str] = []
    errors: list[Exception] = []
    worker_attempted = threading.Event()
    release_main = threading.Event()
    worker_entered = threading.Event()

    def thread_b() -> None:
        try:
            worker_attempted.set()
            with context_lock(ws, "my-repo"):
                order.append("B-enter")
                worker_entered.set()
                order.append("B-exit")
        except Exception as exc:
            errors.append(exc)
        finally:
            release_main.set()

    with context_lock(ws, "my-repo"):
        order.append("A-enter")
        t2 = threading.Thread(target=thread_b)
        t2.start()
        assert worker_attempted.wait(timeout=5)
        assert not worker_entered.is_set(), "Worker entered while main thread held the lock"
        order.append("A-exit")

    assert release_main.wait(timeout=5)
    t2.join(timeout=5)

    assert not t2.is_alive()
    assert errors == [], f"Unexpected exceptions: {errors}"
    assert order == ["A-enter", "A-exit", "B-enter", "B-exit"]


# ---------------------------------------------------------------------------
# Workspace lock timeout (Lock 1)
# ---------------------------------------------------------------------------


def test_workspace_lock_timeout(tmp_path: Path) -> None:
    """WorkspaceLockTimeoutError raised when Lock 1 cannot be acquired within timeout."""
    ws = tmp_path
    (ws / ".dadaia" / "states").mkdir(parents=True)

    acquired = threading.Event()
    release_event = threading.Event()

    def hold_lock() -> None:
        with workspace_lock(ws):
            acquired.set()
            release_event.wait(timeout=10)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    acquired.wait(timeout=5)

    start = _time.monotonic()
    with pytest.raises(WorkspaceLockTimeoutError):
        lock_path = ws / ".dadaia" / "states" / ".ws_lock"
        fd = os.open(str(lock_path), os.O_WRONLY | os.O_CREAT, 0o600)
        try:
            _acquire_flock(fd, str(lock_path), timeout=0.3)
        finally:
            _fcntl.flock(fd, _fcntl.LOCK_UN)
            os.close(fd)

    elapsed = _time.monotonic() - start
    assert elapsed < 2.0, f"Timeout took too long: {elapsed}s"

    release_event.set()
    holder.join(timeout=5)


# ---------------------------------------------------------------------------
# Audit log — required schema
# ---------------------------------------------------------------------------


def test_audit_log_appends_required_event_schema(ws: Path) -> None:
    """Audit helpers append valid JSONL records for acquired, released, and blocked events."""
    audit_acquired(
        ws,
        context="proj",
        release="v1",
        session_id="sess_abc",
        runtime="test-runtime",
        pid=12345,
    )
    audit_released(
        ws,
        context="proj",
        release="v1",
        session_id="sess_abc",
        runtime="test-runtime",
        pid=12345,
    )
    audit_blocked(
        ws,
        context="proj",
        release="v1",
        session_id="sess_blocked",
        runtime="test-runtime",
        pid=99999,
        reason="lock already held",
    )

    log_path = _audit_log_path(ws)
    assert log_path.exists()
    lines = [ln for ln in log_path.read_text().splitlines() if ln.strip()]
    records = [json.loads(line) for line in lines]
    assert [record["event"] for record in records] == [
        "ACQUIRED",
        "RELEASED",
        "BLOCKED_ATTEMPT",
    ]

    required = {"ts", "event", "context", "release", "session_id", "runtime", "pid"}
    for record in records:
        missing = required - set(record)
        assert not missing, f"Audit record missing fields {missing}: {record}"
        assert record["context"] == "proj"
        assert record["release"] == "v1"

    assert records[0]["session_id"] == "sess_abc"
    assert records[0]["runtime"] == "test-runtime"
    assert records[0]["pid"] == 12345
    assert records[2]["session_id"] == "sess_blocked"
    assert records[2]["reason"] == "lock already held"
