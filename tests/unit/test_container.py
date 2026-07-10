"""Unit tests for container.py builder functions.

CRIT: the two container pid-probe tests are the only production-wiring proof of
FR-W1-02 no-steal for LOCK-GC — kept verbatim, never merged away.
"""

import json
import os
import sys
import types
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
        container.build_academy_service,
        container.build_export_service,
        container.build_orchestration_catalog_service,
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
    from dadaia_workspace.features.workflows.service import WorkflowsService
    from dadaia_workspace.features.workspace.service import WorkspaceService

    # No initialization required.
    assert isinstance(container.build_workspace_service(tmp_path), WorkspaceService)
    assert isinstance(container.build_public_service(), PublicAssetService)
    assert isinstance(container.build_repos_service(), ReposService)

    _init_states(tmp_path)
    assert container.build_spec_context_service(tmp_path) is not None
    assert container.build_academy_service(tmp_path) is not None
    assert isinstance(container.build_orchestration_catalog_service(tmp_path), WorkflowsService)
    assert isinstance(container.build_export_service(tmp_path), ExportService)
    assert isinstance(container.build_doctor_service(tmp_path), DoctorService)

    from dadaia_workspace.features.panel.service import PanelService

    assert isinstance(container.build_panel_service(tmp_path), PanelService)


# ---------------------------------------------------------------------------
# _agent_catalog
# ---------------------------------------------------------------------------


def test_agent_catalog_empty_and_sorted(tmp_path: Path) -> None:
    assert container._agent_catalog(tmp_path) == ()

    agents_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "product-engineer.md").write_text("# Product Engineer")
    (agents_dir / "software-architect.md").write_text("# Software Architect")
    assert container._agent_catalog(tmp_path) == ("product-engineer", "software-architect")


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
        datetime.now(tz=UTC) - timedelta(seconds=kernel_tunables.LEASE_TTL_SECONDS + 600)
    ).isoformat()
    rec: dict[str, object] = {
        "context": _GC_CTX,
        "release": "v0.1.11",
        "session_id": "holder",
        "mode": "IMPLEMENTATION",
        "acquired_at": hb,
        "heartbeat": hb,
        "ttl": kernel_tunables.LEASE_TTL_SECONDS,
    }
    if pid is not None:
        rec["pid"] = pid
    path = ctx_locks / f"{_GC_CTX}.lock.json"
    path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return path


def test_build_doctor_service_wires_pid_probe_live_holder_never_reclaimed(tmp_path: Path) -> None:
    """Production wiring: a TTL-expired lease held by the LIVE test pid is NEVER reclaimed.

    Exercises container.build_doctor_service() with the real OsProcessProbe — no lambda.
    os.getpid() is demonstrably alive, so the probe must veto LOCK-GC. Against the unfixed
    container (pid_probe=None, TTL-only) this record would be reported + deleted by --fix.
    """
    pytest.importorskip("fcntl")  # ctx-lock GC is POSIX-seamed like the gate.
    _init_states_v2(tmp_path)
    path = _seed_stale_lock(tmp_path, pid=os.getpid())

    doctor = container.build_doctor_service(tmp_path)

    lock_gc = [i for i in doctor.check() if i.code == "LOCK-GC"]
    assert lock_gc == [], (
        "live-pid holder must NOT be reported reclaimable through production container "
        "wiring — build_doctor_service must inject the PID-liveness probe (FR-W1-02)"
    )

    doctor.fix()
    assert path.exists(), "live-pid TTL-expired lease must NEVER be deleted by --fix"
    stored = json.loads(path.read_text())
    assert stored["session_id"] == "holder"


def test_build_doctor_service_wires_pid_probe_dead_holder_reclaimed(tmp_path: Path) -> None:
    """Production wiring: a TTL-expired lease held by a DEAD pid is reported + reclaimed.

    Companion to the live-holder case. Uses a pid that is virtually certain to be dead
    (a freshly spawned child that has already exited), proving the probe does not over-veto:
    genuinely-dead holders are still garbage-collected by --fix.
    """
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

    lock_gc = [i for i in doctor.check() if i.code == "LOCK-GC"]
    assert lock_gc, "TTL-expired dead-holder lease must be reported LOCK-GC via container wiring"

    actions = doctor.fix()
    assert not path.exists(), "TTL-expired dead-holder lease should be reclaimed by --fix"
    assert any("LOCK-GC" in a for a in actions)


# ---------------------------------------------------------------------------
# Platform adapter selection — T-018-08
# ---------------------------------------------------------------------------


def test_select_lock_adapter_returns_posix_when_has_fcntl(monkeypatch: pytest.MonkeyPatch) -> None:
    """With has_fcntl=True, _select_lock_adapter() returns the POSIX adapter module.

    Monkeypatches PLATFORM so the test is platform-neutral (runs on Linux).
    Does NOT use importorskip — this test exercises the selection logic directly.
    """
    from dadaia_workspace.core.platform import Capabilities

    # The POSIX adapter module imports fcntl at module load; on Windows it cannot
    # be imported at all, so selecting it is meaningless there — skip.
    pytest.importorskip("fcntl")

    posix_caps = Capabilities.detect("linux")
    assert posix_caps.has_fcntl is True  # pre-condition

    monkeypatch.setattr("dadaia_workspace.container.PLATFORM", posix_caps, raising=False)
    # Ensure the PLATFORM import inside _select_lock_adapter sees the patch.
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", posix_caps)

    import dadaia_workspace.infrastructure.file_lock_posix as _posix_mod

    adapter = container._select_lock_adapter()
    assert adapter is _posix_mod, (
        f"Expected file_lock_posix adapter, got {adapter!r}. "
        "Container must route to POSIX adapter when PLATFORM.has_fcntl is True."
    )


def test_select_lock_adapter_returns_windows_when_not_has_fcntl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With has_fcntl=False, _select_lock_adapter() returns the Windows adapter module.

    Monkeypatches PLATFORM to simulate Windows capabilities, and injects a fake
    'dadaia_workspace.infrastructure.file_lock_windows' module into sys.modules to
    prevent the module-level Windows platform guard from raising on Linux.
    """
    import importlib.util

    from dadaia_workspace.core.platform import Capabilities

    win_caps = Capabilities.detect("win32")
    assert win_caps.has_fcntl is False  # pre-condition
    monkeypatch.setattr("dadaia_workspace.core.platform.PLATFORM", win_caps)

    module_key = "dadaia_workspace.infrastructure.file_lock_windows"

    if importlib.util.find_spec("fcntl") is None:
        # Real Windows runner: the Windows adapter imports cleanly (no module-level
        # guard fires), so assert the genuinely-selected module by name. Avoids the
        # fake-vs-real identity fragility of sys.modules injection on Windows.
        adapter = container._select_lock_adapter()
        assert adapter.__name__ == module_key, (
            f"Expected {module_key} adapter, got {adapter!r}. "
            "Container must route to the Windows adapter when has_fcntl is False."
        )
    else:
        # Linux/macOS: the real module raises PlatformCapabilityError at import time
        # (it is Windows-only), so inject a stub to exercise the selection branch.
        _fake_windows_mod = types.ModuleType(module_key)
        _fake_windows_mod.__spec__ = None  # type: ignore[attr-defined]
        original = sys.modules.pop(module_key, None)
        sys.modules[module_key] = _fake_windows_mod
        try:
            adapter = container._select_lock_adapter()
            assert adapter is _fake_windows_mod, (
                f"Expected file_lock_windows adapter, got {adapter!r}. "
                "Container must route to Windows adapter when PLATFORM.has_fcntl is False."
            )
        finally:
            sys.modules.pop(module_key, None)
            if original is not None:
                sys.modules[module_key] = original


# ---------------------------------------------------------------------------
# T-28-A-08 — governance layer composition (registry / store / resolver)
# ---------------------------------------------------------------------------


def test_build_workflow_model_profile_registry_returns_catalog() -> None:
    catalog = container.build_workflow_model_profile_registry()
    impl = catalog.workflow("implementation")
    assert impl is not None
    assert [s.label for s in impl.steps] == [
        "implement",
        "review_qa",
        "review_security",
        "review_code",
    ]


def test_build_workflow_model_policy_store_guard_and_canonical_path(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        container.build_workflow_model_policy_store(tmp_path)

    _init_states(tmp_path)
    store = container.build_workflow_model_policy_store(tmp_path)
    assert store.path == tmp_path / ".dadaia" / "states" / "workflow_model_policy.json"


def test_build_workflow_policy_resolver_defaults_and_overlay(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.workflow_execution import PolicySource

    _init_states(tmp_path)
    resolver = container.build_workflow_policy_resolver(tmp_path)
    snapshot = resolver.resolve("implementation", context="default")
    impl = snapshot.step("implement")
    assert impl is not None
    assert impl.source is PolicySource.LIBRARY_DEFAULT
    assert impl.model_profile == "codex-implementation-standard"

    store = container.build_workflow_model_policy_store(tmp_path)
    overlay = store.parse(
        {
            "schema_version": "workflow-model-policy-v1",
            "policy_id": "default",
            "contexts": {
                "default": {
                    "workflows": {"implementation": {"steps": {"implement": "codex-review-deep"}}}
                }
            },
        }
    )
    store.save(overlay)

    overlay_resolver = container.build_workflow_policy_resolver(tmp_path)
    overlay_impl = overlay_resolver.resolve("implementation", context="default").step("implement")
    assert overlay_impl is not None
    assert overlay_impl.model_profile == "codex-review-deep"


def test_build_workflow_policy_resolver_invalid_overlay_raises(tmp_path: Path) -> None:
    _init_states(tmp_path)
    bad = tmp_path / ".dadaia" / "states" / "workflow_model_policy.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    from dadaia_workspace.core.models.workflow_execution import (
        WorkflowModelPolicyStoreError,
    )

    with pytest.raises(WorkflowModelPolicyStoreError):
        container.build_workflow_policy_resolver(tmp_path)


def test_build_lifecycle_pipeline_accepts_policy_snapshot(tmp_path: Path) -> None:
    _init_states(tmp_path)
    (tmp_path / "repos").mkdir(exist_ok=True)
    resolver = container.build_workflow_policy_resolver(tmp_path)
    snapshot = resolver.resolve("implementation", context="default")
    pipe = container.build_lifecycle_pipeline(
        tmp_path,
        context="dadaia-workspace",
        release_id="v0.1.28",
        policy_snapshot=snapshot,
    )
    assert pipe is not None
