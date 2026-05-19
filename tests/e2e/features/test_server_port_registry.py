"""E2E acceptance tests — Dev Server Port Registry (US-REG-001 to US-REG-007)."""

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


def test_us1_agent_registers_port_before_starting_server(tmp_path: Path) -> None:
    """US-REG-001: Reservar porta antes de subir servidor."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(11111)
    svc = _build_svc(ws, probe)

    entry = svc.register(port=3000, project="portifolio", pid=11111, description="Flask")

    assert entry.port == 3000
    assert entry.project == "portifolio"
    assert entry.url == "http://localhost:3000"
    assert entry.pid == 11111

    entries = svc.list_entries()
    assert len(entries) == 1
    _, status = entries[0]
    assert status == PortStatus.ACTIVE

    registry_file = ws / ".dadaia" / "states" / "server_registry.json"
    assert registry_file.exists()


def test_us1_conflict_raises_when_port_occupied(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([11111, 22222])
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=11111)
    with pytest.raises(PortConflictError) as exc_info:
        svc.register(port=3000, project="portifolio-wave6", pid=22222)
    assert "portifolio" in str(exc_info.value)

    entries = svc.list_entries()
    assert len(entries) == 1


def test_us2_next_port_returns_deterministic_base(tmp_path: Path) -> None:
    """US-REG-002: Obter próxima porta de forma determinística."""
    ws = _init_workspace(tmp_path)
    svc = _build_svc(ws, FakeProcessProbe())

    port, is_base = svc.next_port("dadaia-bots")
    assert port == 3537
    assert is_base is True


def test_us2_next_port_idempotent_when_registered(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    svc = _build_svc(ws, probe)

    svc.register(port=3537, project="dadaia-bots", pid=99)

    port1, _ = svc.next_port("dadaia-bots")
    port2, _ = svc.next_port("dadaia-bots")
    assert port1 == port2 == 3537


def test_us2_next_port_increments_when_base_occupied(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(88)
    svc = _build_svc(ws, probe)

    svc.register(port=3537, project="other-project", pid=88)
    port, is_base = svc.next_port("dadaia-bots")
    assert port != 3537
    assert is_base is False


def test_us3_list_all_registered_servers(tmp_path: Path) -> None:
    """US-REG-003: Consultar registro completo de portas."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([1, 2, 3])
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=1)
    svc.register(port=3001, project="portifolio", pid=2, description="Vite")
    svc.register(port=3537, project="dadaia-bots", pid=3)

    entries = svc.list_entries()
    assert len(entries) == 3
    projects = {e.project for e, _ in entries}
    assert projects == {"portifolio", "dadaia-bots"}

    _, s = entries[0]
    assert s == PortStatus.ACTIVE


def test_us3_list_empty_returns_empty_list(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    svc = _build_svc(ws, FakeProcessProbe())
    assert svc.list_entries() == []


def test_us4_release_port_on_shutdown(tmp_path: Path) -> None:
    """US-REG-004: Liberar porta ao encerrar servidor."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.update([1, 2])
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=1)
    svc.register(port=3001, project="portifolio", pid=2)

    svc.release(port=3000)

    entries = svc.list_entries()
    assert len(entries) == 1
    assert entries[0][0].port == 3001

    with pytest.raises(PortNotRegisteredError):
        svc.release(port=3000)


def test_us5_show_project_url(tmp_path: Path) -> None:
    """US-REG-005: Consultar URL de projeto específico."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    svc = _build_svc(ws, probe)

    svc.register(port=3003, project="dd-chain-explorer", pid=99)
    result = svc.show_project("dd-chain-explorer")

    assert len(result) == 1
    entry, status = result[0]
    assert entry.url == "http://localhost:3003"
    assert status == PortStatus.ACTIVE


def test_us5_show_project_empty_returns_empty_list(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    svc = _build_svc(ws, FakeProcessProbe())
    assert svc.show_project("dd-chain-explorer") == []


def test_us6_clean_removes_stale_entries(tmp_path: Path) -> None:
    """US-REG-006: Limpar entradas obsoletas."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=99)
    removed = svc.clean()
    assert len(removed) == 1
    assert removed[0].port == 3000
    assert svc.list_entries() == []


def test_us6_clean_dry_run_does_not_remove(tmp_path: Path) -> None:
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    svc = _build_svc(ws, probe)

    svc.register(port=3000, project="portifolio", pid=99)
    removed = svc.clean(dry_run=True)
    assert len(removed) == 1
    assert len(svc.list_entries()) == 1


def test_us7_skill_file_exists_in_public(tmp_path: Path) -> None:
    """US-REG-007: Skill file exists in public/skills/dev-server-registry/."""
    import dadaia_workspace

    pkg_dir = Path(dadaia_workspace.__file__).parent
    skill_file = pkg_dir / "public" / "skills" / "dev-server-registry" / "SKILL.md"
    assert skill_file.exists(), f"Missing: {skill_file}"
    content = skill_file.read_text()
    assert "dadaia server list" in content
    assert "dadaia server next" in content
    assert "dadaia server register" in content
    assert "dadaia server release" in content


def test_registry_persists_across_service_restarts(tmp_path: Path) -> None:
    """Registry survives process restart (reads from disk)."""
    ws = _init_workspace(tmp_path)
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)

    svc_a = _build_svc(ws, probe)
    svc_a.register(port=3000, project="portifolio", pid=99)

    svc_b = _build_svc(ws, probe)
    entries = svc_b.list_entries()
    assert len(entries) == 1
    assert entries[0][0].port == 3000
