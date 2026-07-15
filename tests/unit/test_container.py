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
    from dadaia_workspace.features.workflows.service import WorkflowsService
    from dadaia_workspace.features.workspace.service import WorkspaceService

    # No initialization required.
    assert isinstance(container.build_workspace_service(tmp_path), WorkspaceService)
    assert isinstance(container.build_public_service(), PublicAssetService)
    assert isinstance(container.build_repos_service(), ReposService)

    _init_states(tmp_path)
    assert container.build_spec_context_service(tmp_path) is not None
    assert container.build_academy_service(tmp_path) is not None
    assert isinstance(container.build_workflow_catalog_service(tmp_path), WorkflowsService)
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
# T-28-A-08 — governance layer composition (registry / store / resolver)
# ---------------------------------------------------------------------------


def test_build_workflow_model_profile_registry_catalog_and_policy_store(tmp_path: Path) -> None:
    catalog = container.build_workflow_model_profile_registry()
    impl = catalog.workflow("implementation_reviews")
    assert impl is not None
    assert [s.label for s in impl.steps] == [
        "implement",
        "review_qa",
        "review_security",
        "review_code",
        "close",
    ]

    with pytest.raises(WorkspaceNotInitializedError):
        container.build_workflow_model_policy_store(tmp_path)

    _init_states(tmp_path)
    store = container.build_workflow_model_policy_store(tmp_path)
    assert store.path == tmp_path / ".dadaia" / "states" / "workflow_model_policy.json"


def test_build_workflow_policy_resolver_defaults_and_overlay(tmp_path: Path) -> None:
    from dadaia_workspace.core.models.workflow_execution import PolicySource

    _init_states(tmp_path)
    resolver = container.build_workflow_policy_resolver(tmp_path)
    snapshot = resolver.resolve("implementation_reviews", context="default")
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
                    "workflows": {
                        "implementation_reviews": {"steps": {"implement": "codex-review-deep"}}
                    }
                }
            },
        }
    )
    store.save(overlay)

    overlay_resolver = container.build_workflow_policy_resolver(tmp_path)
    overlay_impl = overlay_resolver.resolve("implementation_reviews", context="default").step(
        "implement"
    )
    assert overlay_impl is not None
    assert overlay_impl.model_profile == "codex-review-deep"

    # An invalid (unparseable) overlay file raises rather than silently degrading.
    bad_ws = tmp_path.parent / (tmp_path.name + "-bad-overlay")
    _init_states(bad_ws)
    bad = bad_ws / ".dadaia" / "states" / "workflow_model_policy.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    from dadaia_workspace.core.models.workflow_execution import (
        WorkflowModelPolicyStoreError,
    )

    with pytest.raises(WorkflowModelPolicyStoreError):
        container.build_workflow_policy_resolver(bad_ws)


def test_build_lifecycle_pipeline_accepts_policy_snapshot(tmp_path: Path) -> None:
    _init_states(tmp_path)
    (tmp_path / "repos").mkdir(exist_ok=True)
    resolver = container.build_workflow_policy_resolver(tmp_path)
    snapshot = resolver.resolve("implementation_reviews", context="default")
    pipe = container.build_lifecycle_pipeline(
        tmp_path,
        context="dadaia-workspace",
        release_id="v0.1.28",
        policy_snapshot=snapshot,
    )
    assert pipe is not None
