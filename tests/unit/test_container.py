"""Unit tests for container.py builder functions.

CRIT: the two container pid-probe tests are the only production-wiring proof of
FR-W1-02 no-steal for LOCK-GC — kept verbatim, never merged away.
"""

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from tests.fixtures.harness_env import scrub_context_resolution_env


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
        container.build_academy_service,
        container.build_export_service,
        container.build_panel_service,
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
    assert container.build_academy_service(tmp_path) is not None
    assert isinstance(container.build_export_service(tmp_path), ExportService)
    assert isinstance(container.build_doctor_service(tmp_path), DoctorService)

    from dadaia_workspace.features.panel.service import PanelService

    assert isinstance(container.build_panel_service(tmp_path), PanelService)


# ---------------------------------------------------------------------------
# rc-1 code-review HIGH fix (T-011-02 follow-up): build_doctor_service must wire
# the PID-liveness probe so LOCK-GC honours the no-steal invariant (FR-W1-02).
#
# These tests go through PRODUCTION container wiring — NO injected probe lambda —
# so they pin the seam end-to-end. Against the UNFIXED container (DoctorService
# constructed without pid_probe -> None -> TTL-only LOCK-GC), the live-pid case
# below would FAIL: a TTL-expired record whose holder is os.getpid() (this very
# test process, demonstrably alive) would be reported reclaimable and deleted by
# --fix. The fix wires build_pid_probe() into the DoctorService.
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


def test_build_doctor_service_wires_pid_probe_live_holder_never_reclaimed(tmp_path: Path) -> None:
    """Residual lock state has no authority even when its recorded pid is live."""
    pytest.importorskip("fcntl")  # ctx-lock GC is POSIX-seamed like the gate.
    _init_states_v2(tmp_path)
    path = _seed_stale_lock(tmp_path, pid=os.getpid())

    doctor = container.build_doctor_service(tmp_path)

    retired = [i for i in doctor.check() if i.code == "RETIRED-LOCK-STATE"]
    assert retired

    doctor.fix()
    assert not path.exists()


def test_build_doctor_service_wires_pid_probe_dead_holder_reclaimed(tmp_path: Path) -> None:
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

    retired = [i for i in doctor.check() if i.code == "RETIRED-LOCK-STATE"]
    assert retired

    actions = doctor.fix()
    assert not path.exists(), "TTL-expired dead-holder lease should be reclaimed by --fix"
    assert any("RETIRED-LOCK-STATE" in a for a in actions)


# ---------------------------------------------------------------------------
# T-50-02 (SPEC v0.5.0 FR1) — container.resolve_context, the hooks-side seam onto the
# single context-resolution authority. Thin pass-through: pinned here as a direct
# behavioral proof, exercised indirectly (harness-real) by sdd_gate/sdd_post_gate.
#
# Bug specs-resolver-context-tests-flaky-under-xdist-full-suite: these three tests used
# to clear no ambient env at all. ``container.resolve_context`` delegates to the single
# resolution authority, whose ``_authority_workspace_root()`` honours ``WORKSPACE_ROOT``
# unconditionally (ahead of, and regardless of, ``monkeypatch.chdir()``) -- an inherited
# or concurrently-leaked ``WORKSPACE_ROOT``/``DADAIA_CONTEXT``/harness session-id var
# silently overrides these tests' own synthetic ``tmp_path`` scenarios.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_context_resolution_env(monkeypatch: pytest.MonkeyPatch) -> None:
    scrub_context_resolution_env(monkeypatch)


def test_resolve_context_seam_explicit_wins(tmp_path: Path) -> None:
    assert container.resolve_context("explicit-ctx") == "explicit-ctx"


def test_resolve_context_seam_target_path_beats_dadaia_context_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {"name": "x", "repo_slug": "x", "state": "alive"},
                    {"name": "y", "repo_slug": "y", "state": "alive"},
                ],
            }
        )
    )
    (tmp_path / "repos" / "x").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_CONTEXT", "y")

    target = tmp_path / "repos" / "x" / "specs" / "SPEC.md"
    assert container.resolve_context(target_path=target) == "x"


def test_resolve_context_seam_no_input_resolves_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plain = tmp_path / "not-a-workspace"
    plain.mkdir()
    monkeypatch.chdir(plain)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)

    assert container.resolve_context() is None


# ---------------------------------------------------------------------------
# T-28-A-08 — governance layer composition (registry / store / resolver)
# ---------------------------------------------------------------------------
