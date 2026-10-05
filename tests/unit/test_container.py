"""The container builders guard initialization and wire production
collaborators; ``build_doctor_service`` reaps retired lock state (``states/ctx_locks``)
whatever its recorded holder pid — liveness is never consulted (NO-LOCKS)."""

import json
import os
from pathlib import Path

import pytest

from dadaia_workspace import container
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.features.export.service import ExportService
from dadaia_workspace.features.import_.service import ImportService
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.spec_context.doctor import DoctorService
from dadaia_workspace.features.workspace.service import WorkspaceService


def _init_states(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(json.dumps({"schema_version": "2", "contexts": []}))
    return states


@pytest.mark.parametrize(
    "builder",
    [
        container.build_spec_context_service,
        container.build_doctor_service,
        container.build_export_service,
        container.build_import_service,
    ],
)
def test_build_service_raises_when_not_initialized(tmp_path: Path, builder: object) -> None:
    """A workspace-bound builder refuses an uninitialized root."""
    with pytest.raises(WorkspaceNotInitializedError):
        builder(tmp_path)  # type: ignore[operator]


def test_build_service_succeeds_table(tmp_path: Path) -> None:
    """Workspace and public builders need no init; the rest build once initialized."""
    assert isinstance(container.build_workspace_service(tmp_path), WorkspaceService)
    assert isinstance(container.build_public_service(), PublicAssetService)
    _init_states(tmp_path)
    assert container.build_spec_context_service(tmp_path) is not None
    assert isinstance(container.build_export_service(tmp_path), ExportService)
    assert isinstance(container.build_import_service(tmp_path), ImportService)
    assert isinstance(container.build_doctor_service(tmp_path), DoctorService)


@pytest.mark.parametrize("pid", [os.getpid(), 2_147_480_000], ids=["live-holder", "dead-holder"])
def test_build_doctor_service_reaps_retired_lock_state_whatever_the_holder(
    tmp_path: Path, pid: int
) -> None:
    """Residual lock state is closed-canon slop; fix() removes it without a liveness probe."""
    lock = _init_states(tmp_path) / "ctx_locks" / "ctx.lock.json"
    lock.parent.mkdir()
    lock.write_text(json.dumps({"context": "ctx", "session_id": "holder", "pid": pid}), "utf-8")
    doctor = container.build_doctor_service(tmp_path)
    assert any(f.code == "WS-states-slop" for f in doctor.scan())
    assert any("WS-states-slop" in action for action in doctor.fix())
    assert not lock.exists()
