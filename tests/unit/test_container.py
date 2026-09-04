"""Unit tests for container.py builder functions.

The two ``build_doctor_service`` tests go through PRODUCTION wiring — no injected
collaborator — and pin that the retired lock state (``states/ctx_locks``) is reaped whether
or not its recorded holder pid is alive: liveness is never consulted (NO-LOCKS).
"""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError


def _init_states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(json.dumps({"version": "1", "contexts": []}))
    return states


def _init_states_v2(tmp_path: Path) -> Path:
    """Initialize a v2 spec_contexts.json (the LOCK-GC path actually loads the store)."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True, exist_ok=True)
    (states / "spec_contexts.json").write_text(json.dumps({"schema_version": "2", "contexts": []}))
    return states


# ---------------------------------------------------------------------------
# build_*_service — WorkspaceNotInitializedError guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "builder",
    [
        container.build_spec_context_service,
        container.build_doctor_service,
        container.build_export_service,
    ],
)
def test_build_service_raises_when_not_initialized(tmp_path: Path, builder: object) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        builder(tmp_path)  # type: ignore[operator]


# ---------------------------------------------------------------------------
# build_*_service — succeeds when initialized (+ repos/public, which need no init)
# ---------------------------------------------------------------------------


def test_build_service_succeeds_table(tmp_path: Path) -> None:
    from dadaia_workspace.features.export.service import ExportService
    from dadaia_workspace.features.public.service import PublicAssetService
    from dadaia_workspace.features.repos.service import ReposService
    from dadaia_workspace.features.spec_context.doctor import DoctorService
    from dadaia_workspace.features.workspace.service import WorkspaceService

    # No initialization required.
    assert isinstance(container.build_workspace_service(tmp_path), WorkspaceService)
    assert isinstance(container.build_public_service(), PublicAssetService)
    assert isinstance(container.build_repos_service(), ReposService)

    _init_states(tmp_path)
    assert container.build_spec_context_service(tmp_path) is not None
    assert isinstance(container.build_export_service(tmp_path), ExportService)
    assert isinstance(container.build_doctor_service(tmp_path), DoctorService)

    # build_panel_service moved to cli.commands.panel_composition (F001, T-053-14).


# ---------------------------------------------------------------------------
# build_doctor_service through PRODUCTION wiring: residual lock state under
# states/ctx_locks is closed-canon slop, reaped whether the recorded holder pid is
# alive (this very test process) or dead — liveness is never consulted.
# ---------------------------------------------------------------------------

_GC_CTX = "containergcctx"


def _seed_stale_lock(tmp_path: Path, *, pid: int | None) -> Path:
    """Plant a TTL-expired lease record under ctx_locks/. Returns its path."""
    ctx_locks = tmp_path / ".dadaia" / "states" / "ctx_locks"
    ctx_locks.mkdir(parents=True, exist_ok=True)
    hb = (
        datetime.now(tz=UTC) - timedelta(seconds=kernel_tunables.PRESENCE_TTL_SECONDS + 600)
    ).isoformat()
    rec: dict[str, object] = {
        "context": _GC_CTX,
        "release": "v0.1.11",
        "session_id": "holder",
        "mode": "IMPLEMENTATION",
        "acquired_at": hb,
        "heartbeat": hb,
        "ttl": kernel_tunables.PRESENCE_TTL_SECONDS,
    }
    if pid is not None:
        rec["pid"] = pid
    path = ctx_locks / f"{_GC_CTX}.lock.json"
    path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return path


def test_build_doctor_service_reaps_retired_lock_state_with_a_live_holder(tmp_path: Path) -> None:
    """Residual lock state has no authority even when its recorded pid is live."""
    pytest.importorskip("fcntl")  # ctx-lock GC is POSIX-seamed like the gate.
    _init_states_v2(tmp_path)
    path = _seed_stale_lock(tmp_path, pid=os.getpid())

    doctor = container.build_doctor_service(tmp_path)

    retired = [f for f in doctor.scan() if f.code == "WS-states-slop"]
    assert retired

    doctor.fix()
    assert not path.exists()


def test_build_doctor_service_reaps_retired_lock_state_with_a_dead_holder(tmp_path: Path) -> None:
    """Residual lock state is removed without consulting holder liveness."""
    pytest.importorskip("fcntl")
    _init_states_v2(tmp_path)

    # Spawn a child and reap it so its pid is dead by the time the probe runs.
    dead_pid = os.fork() if hasattr(os, "fork") else None
    if dead_pid == 0:  # pragma: no cover — child path exits immediately.
        os._exit(0)
    if dead_pid is not None:
        os.waitpid(dead_pid, 0)
    else:  # No os.fork (non-POSIX): fall back to a pid unlikely to exist.
        dead_pid = 2147480000

    path = _seed_stale_lock(tmp_path, pid=dead_pid)
    doctor = container.build_doctor_service(tmp_path)

    retired = [f for f in doctor.scan() if f.code == "WS-states-slop"]
    assert retired

    actions = doctor.fix()
    assert not path.exists(), "TTL-expired dead-holder lease should be reclaimed by --fix"
    assert any("WS-states-slop" in a for a in actions)


# ---------------------------------------------------------------------------
# T-28-A-08 — governance layer composition (registry / store / resolver)
# ---------------------------------------------------------------------------
