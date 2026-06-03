"""Unit tests for ServerRegistryService."""

import pytest

from dadaia_workspace.core.exceptions import PortConflictError, PortNotRegisteredError
from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.features.server_registry.service import ServerRegistryService
from tests.fakes import FakeProcessProbe, FakeServerRegistryStore


def _svc(
    store: FakeServerRegistryStore | None = None, probe: FakeProcessProbe | None = None
) -> ServerRegistryService:
    return ServerRegistryService(
        store=store or FakeServerRegistryStore(),
        probe=probe or FakeProcessProbe(),
    )


def _entry(port: int = 3000, project: str = "my-frontend", pid: int | None = None) -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2099-12-31T23:59:59Z",  # far future — not stale by TTL
        pid=pid,
    )


# ------------------------------------------------------------------ register


def test_register_saves_entry() -> None:
    store = FakeServerRegistryStore()
    svc = _svc(store)
    svc.register(port=3000, project="my-frontend")
    assert store.get(3000) is not None
    assert store.get(3000).project == "my-frontend"  # type: ignore[union-attr]


def test_register_sets_url_default() -> None:
    store = FakeServerRegistryStore()
    svc = _svc(store)
    svc.register(port=3000, project="my-frontend")
    entry = store.get(3000)
    assert entry is not None
    assert entry.url == "http://localhost:3000"


def test_register_conflict_raises_port_conflict_error() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    with pytest.raises(PortConflictError, match="my-frontend"):
        svc.register(port=3000, project="my-frontend-wave6")


def test_register_same_project_same_port_is_idempotent() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    svc.register(port=3000, project="my-frontend")  # must not raise
    assert store.count() == 1


def test_register_stale_entry_can_be_overwritten() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    # pid=99 is NOT in alive_pids → stale
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    svc.register(port=3000, project="my-frontend-wave6")
    assert store.get(3000).project == "my-frontend-wave6"  # type: ignore[union-attr]


def test_register_expired_ttl_entry_can_be_overwritten() -> None:
    store = FakeServerRegistryStore()
    expired = PortEntry(
        port=3000,
        project="my-frontend",
        reserved_at="2020-01-01T00:00:00Z",
        expires_at="2020-01-01T08:00:00Z",  # expired
    )
    store.save(expired)
    svc = _svc(store)
    svc.register(port=3000, project="my-frontend-wave6")
    assert store.get(3000).project == "my-frontend-wave6"  # type: ignore[union-attr]


# ------------------------------------------------------------------ release


def test_release_removes_entry() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "my-frontend"))
    svc = _svc(store)
    svc.release(port=3000)
    assert store.get(3000) is None


def test_release_with_wrong_project_raises() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "my-frontend"))
    svc = _svc(store)
    with pytest.raises(PortConflictError, match="my-frontend"):
        svc.release(port=3000, project="my-frontend-wave6")


def test_release_nonexistent_port_raises() -> None:
    svc = _svc()
    with pytest.raises(PortNotRegisteredError):
        svc.release(port=9999)


def test_release_all_for_project() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "my-frontend"))
    store.save(_entry(3001, "my-frontend"))
    store.save(_entry(3002, "other"))
    svc = _svc(store)
    svc.release_all(project="my-frontend")
    assert store.get(3000) is None
    assert store.get(3001) is None
    assert store.get(3002) is not None


# ------------------------------------------------------------------ list_entries


def test_list_entries_returns_with_status() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    result = svc.list_entries()
    assert len(result) == 1
    entry, status = result[0]
    assert entry.port == 3000
    assert status == PortStatus.ACTIVE


def test_list_entries_marks_dead_pid_as_stale() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()  # pid=99 NOT in alive_pids
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    result = svc.list_entries()
    _, status = result[0]
    assert status == PortStatus.STALE


def test_list_entries_empty_registry() -> None:
    assert _svc().list_entries() == []


def test_list_entries_filter_by_project() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "my-frontend"))
    store.save(_entry(3001, "my-service"))
    svc = _svc(store)
    result = svc.list_entries(project="my-frontend")
    assert len(result) == 1
    assert result[0][0].project == "my-frontend"


# ------------------------------------------------------------------ clean


def test_clean_removes_stale_pid_entries() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()  # pid=99 dead
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    removed = svc.clean()
    assert len(removed) == 1
    assert removed[0].port == 3000
    assert store.get(3000) is None


def test_clean_removes_expired_ttl_entries() -> None:
    store = FakeServerRegistryStore()
    expired = PortEntry(
        port=3000,
        project="my-frontend",
        reserved_at="2020-01-01T00:00:00Z",
        expires_at="2020-01-01T08:00:00Z",
    )
    store.save(expired)
    svc = _svc(store)
    removed = svc.clean()
    assert len(removed) == 1


def test_clean_dry_run_does_not_modify_store() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    removed = svc.clean(dry_run=True)
    assert len(removed) == 1
    assert store.get(3000) is not None  # not actually removed


def test_clean_keeps_alive_entries() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    removed = svc.clean()
    assert removed == []
    assert store.get(3000) is not None


# ------------------------------------------------------------------ next_port


def test_next_port_returns_base_hash_port_when_free() -> None:
    svc = _svc()
    port, is_base = svc.next_port("my-service")
    assert port == 3073  # md5("my-service") base port
    assert is_base is True


def test_next_port_returns_existing_if_already_registered() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3073, "my-service", pid=99))
    svc = _svc(store, probe)
    port, is_base = svc.next_port("my-service")
    assert port == 3073
    assert is_base is True


def test_next_port_increments_when_base_occupied_by_other() -> None:
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    # Occupy my-service base port (3073) with a different project
    store.save(
        PortEntry(
            port=3073,
            project="other",
            reserved_at="2026-05-16T10:00:00Z",
            expires_at="2099-12-31T23:59:59Z",
            pid=99,
        )
    )
    svc = _svc(store, probe)
    port, is_base = svc.next_port("my-service")
    assert port != 3073
    assert port >= 3000
    assert port <= 3999
    assert is_base is False


def test_next_port_respects_custom_range() -> None:
    svc = _svc()
    port, _ = svc.next_port("my-service", min_port=4000, max_port=4099)
    assert 4000 <= port <= 4099
