"""E2E acceptance tests — Dev Server Port Registry (US-REG-001 to US-REG-007).

US-REG-007 (skill file presence + content asserts) is folded into
``test_public_pipeline.TestContentConsistency`` — presence is pinned by the one derived
skill-inventory oracle (``tests.helpers.skill_inventory_oracle.skill_names``, v0.4.5 FR4)
and the content asserts (dadaia server list/next/register/release) are folded into the
merged content-consistency check there.

Intent: CONTRACT — US-REG-001..007 (dev server port registry)
Owner: software-engineer
"""

from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PortConflictError, PortNotRegisteredError
from dadaia_workspace.core.models.server_registry import PortStatus
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from tests.fakes import FakeProcessProbe


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def _build_svc(workspace: Path, probe: FakeProcessProbe) -> ServerRegistryService:
    states = workspace / ".dadaia" / "states"
    return ServerRegistryService(
        store=JsonServerRegistryStore(states),
        probe=probe,
    )


def test_us1_register_before_starting_server_and_conflict_on_occupied_port(
    tmp_path: Path,
) -> None:
    """US-REG-001: reserve a port before starting a server, and a second register on
    the same port with a live pid conflicts."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([11111, 22222])
    svc = _build_svc(ws, probe)

    entry = svc.register(port=3000, project="my-frontend", pid=11111, description="Flask")

    assert entry.port == 3000
    assert entry.project == "my-frontend"
    assert entry.url == "http://localhost:3000"
    assert entry.pid == 11111

    entries = svc.list_entries()
    assert len(entries) == 1
    _, status = entries[0]
    assert status == PortStatus.ACTIVE

    registry_file = ws / ".dadaia" / "states" / "server_registry.json"
    assert registry_file.exists()

    with pytest.raises(PortConflictError) as exc_info:
        svc.register(port=3000, project="my-frontend-wave6", pid=22222)
    assert "my-frontend" in str(exc_info.value)
    assert len(svc.list_entries()) == 1


def test_us2_next_port_deterministic_idempotent_and_increments_on_conflict(
    tmp_path: Path,
) -> None:
    """US-REG-002: next_port is deterministic on a fresh registry, idempotent once
    registered, and increments past the base when the base port is occupied."""
    ws = _init_workspace(tmp_path)
    svc = _build_svc(ws, FakeProcessProbe())

    port, is_base = svc.next_port("my-service")
    assert port == 3073
    assert is_base is True

    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    svc2 = _build_svc(ws, probe)
    svc2.register(port=3073, project="my-service", pid=99)

    port1, _ = svc2.next_port("my-service")
    port2, _ = svc2.next_port("my-service")
    assert port1 == port2 == 3073

    probe2 = FakeProcessProbe()
    probe2._alive_pids.add(88)
    ws2 = _init_workspace(tmp_path / "ws2")
    svc3 = _build_svc(ws2, probe2)
    svc3.register(port=3073, project="other-project", pid=88)
    conflicted_port, conflicted_is_base = svc3.next_port("my-service")
    assert conflicted_port != 3073
    assert conflicted_is_base is False


def test_us3_list_and_us5_show_project(tmp_path: Path) -> None:
    """US-REG-003: list all registered servers (and empty). US-REG-005: show a
    specific project's URL (and empty)."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([1, 2, 3])
    svc = _build_svc(ws, probe)

    assert svc.list_entries() == []
    assert svc.show_project("my-api") == []

    svc.register(port=3000, project="my-frontend", pid=1)
    svc.register(port=3001, project="my-frontend", pid=2, description="Vite")
    svc.register(port=3003, project="my-api", pid=3)

    entries = svc.list_entries()
    assert len(entries) == 3
    projects = {e.project for e, _ in entries}
    assert projects == {"my-frontend", "my-api"}
    _, s = entries[0]
    assert s == PortStatus.ACTIVE

    result = svc.show_project("my-api")
    assert len(result) == 1
    entry, status = result[0]
    assert entry.url == "http://localhost:3003"
    assert status == PortStatus.ACTIVE


def test_us4_release_port_on_shutdown(tmp_path: Path) -> None:
    """US-REG-004: liberar porta ao encerrar servidor."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([1, 2])
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="my-frontend", pid=1)
    svc.register(port=3001, project="my-frontend", pid=2)

    svc.release(port=3000)

    entries = svc.list_entries()
    assert len(entries) == 1
    assert entries[0][0].port == 3001

    with pytest.raises(PortNotRegisteredError):
        svc.release(port=3000)


def test_us6_clean_removes_stale_entries_and_dry_run_does_not(tmp_path: Path) -> None:
    """US-REG-006: clean removes stale entries; a dry-run leaves them in place."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="my-frontend", pid=99)
    removed = svc.clean(dry_run=True)
    assert len(removed) == 1
    assert len(svc.list_entries()) == 1

    removed = svc.clean()
    assert len(removed) == 1
    assert removed[0].port == 3000
    assert svc.list_entries() == []


def test_registry_persists_across_service_restarts(tmp_path: Path) -> None:
    """Registry survives process restart (reads from disk)."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)

    svc_a = _build_svc(ws, probe)
    svc_a.register(port=3000, project="my-frontend", pid=99)

    svc_b = _build_svc(ws, probe)
    entries = svc_b.list_entries()
    assert len(entries) == 1
    assert entries[0][0].port == 3000
