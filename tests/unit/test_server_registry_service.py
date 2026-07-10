"""Unit tests for ServerRegistryService.

Port-collision prevention rows preserved (dev-server-registry law): the live-pid
conflict raise is kept standalone below.
"""

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


def test_register_conflict_raises_port_conflict_error() -> None:
    """The dev-server-registry law: registering an occupied port with a live holder
    must never succeed — kept standalone (never merged with the overwrite cases)."""
    store = FakeServerRegistryStore()
    probe = FakeProcessProbe()
    probe._alive_pids.add(99)
    store.save(_entry(3000, "my-frontend", pid=99))
    svc = _svc(store, probe)
    with pytest.raises(PortConflictError, match="my-frontend"):
        svc.register(port=3000, project="my-frontend-wave6")


def test_register_saves_entry_with_url_default() -> None:
    store = FakeServerRegistryStore()
    svc = _svc(store)
    svc.register(port=3000, project="my-frontend")
    entry = store.get(3000)
    assert entry is not None
    assert entry.project == "my-frontend"
    assert entry.url == "http://localhost:3000"


def test_register_idempotent_stale_and_ttl_expired_overwrite() -> None:
    # Same project, same port ⇒ idempotent no-op.
    idem_store = FakeServerRegistryStore()
    idem_probe = FakeProcessProbe()
    idem_probe._alive_pids.add(99)
    idem_store.save(_entry(3000, "my-frontend", pid=99))
    idem_svc = _svc(idem_store, idem_probe)
    idem_svc.register(port=3000, project="my-frontend")  # must not raise
    assert idem_store.count() == 1

    # pid=99 is NOT in alive_pids → stale ⇒ overwritable.
    stale_store = FakeServerRegistryStore()
    stale_probe = FakeProcessProbe()
    stale_store.save(_entry(3000, "my-frontend", pid=99))
    stale_svc = _svc(stale_store, stale_probe)
    stale_svc.register(port=3000, project="my-frontend-wave6")
    stale_entry = stale_store.get(3000)
    assert stale_entry is not None and stale_entry.project == "my-frontend-wave6"

    # Expired TTL entry ⇒ overwritable.
    ttl_store = FakeServerRegistryStore()
    expired = PortEntry(
        port=3000,
        project="my-frontend",
        reserved_at="2020-01-01T00:00:00Z",
        expires_at="2020-01-01T08:00:00Z",  # expired
    )
    ttl_store.save(expired)
    ttl_svc = _svc(ttl_store)
    ttl_svc.register(port=3000, project="my-frontend-wave6")
    ttl_entry = ttl_store.get(3000)
    assert ttl_entry is not None and ttl_entry.project == "my-frontend-wave6"


# ------------------------------------------------------------------ release


def test_release_removes_and_release_all_for_project() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "my-frontend"))
    svc = _svc(store)
    svc.release(port=3000)
    assert store.get(3000) is None

    all_store = FakeServerRegistryStore()
    all_store.save(_entry(3000, "my-frontend"))
    all_store.save(_entry(3001, "my-frontend"))
    all_store.save(_entry(3002, "other"))
    all_svc = _svc(all_store)
    all_svc.release_all(project="my-frontend")
    assert all_store.get(3000) is None
    assert all_store.get(3001) is None
    assert all_store.get(3002) is not None


def test_release_wrong_project_and_nonexistent_port_raise() -> None:
    store = FakeServerRegistryStore()
    store.save(_entry(3000, "my-frontend"))
    svc = _svc(store)
    with pytest.raises(PortConflictError, match="my-frontend"):
        svc.release(port=3000, project="my-frontend-wave6")

    empty_svc = _svc()
    with pytest.raises(PortNotRegisteredError):
        empty_svc.release(port=9999)


# ------------------------------------------------------------------ list_entries


def test_list_entries_table() -> None:
    active_store = FakeServerRegistryStore()
    active_probe = FakeProcessProbe()
    active_probe._alive_pids.add(99)
    active_store.save(_entry(3000, "my-frontend", pid=99))
    active_result = _svc(active_store, active_probe).list_entries()
    assert len(active_result) == 1
    entry, status = active_result[0]
    assert entry.port == 3000
    assert status == PortStatus.ACTIVE

    stale_store = FakeServerRegistryStore()
    stale_probe = FakeProcessProbe()  # pid=99 NOT in alive_pids
    stale_store.save(_entry(3000, "my-frontend", pid=99))
    _, stale_status = _svc(stale_store, stale_probe).list_entries()[0]
    assert stale_status == PortStatus.STALE

    assert _svc().list_entries() == []

    filter_store = FakeServerRegistryStore()
    filter_store.save(_entry(3000, "my-frontend"))
    filter_store.save(_entry(3001, "my-service"))
    filtered = _svc(filter_store).list_entries(project="my-frontend")
    assert len(filtered) == 1
    assert filtered[0][0].project == "my-frontend"


# ------------------------------------------------------------------ clean


def test_clean_table() -> None:
    dead_store = FakeServerRegistryStore()
    dead_probe = FakeProcessProbe()  # pid=99 dead
    dead_store.save(_entry(3000, "my-frontend", pid=99))
    removed_dead = _svc(dead_store, dead_probe).clean()
    assert len(removed_dead) == 1
    assert removed_dead[0].port == 3000
    assert dead_store.get(3000) is None

    ttl_store = FakeServerRegistryStore()
    expired = PortEntry(
        port=3000,
        project="my-frontend",
        reserved_at="2020-01-01T00:00:00Z",
        expires_at="2020-01-01T08:00:00Z",
    )
    ttl_store.save(expired)
    removed_ttl = _svc(ttl_store).clean()
    assert len(removed_ttl) == 1

    dry_store = FakeServerRegistryStore()
    dry_probe = FakeProcessProbe()
    dry_store.save(_entry(3000, "my-frontend", pid=99))
    dry_removed = _svc(dry_store, dry_probe).clean(dry_run=True)
    assert len(dry_removed) == 1
    assert dry_store.get(3000) is not None  # not actually removed

    alive_store = FakeServerRegistryStore()
    alive_probe = FakeProcessProbe()
    alive_probe._alive_pids.add(99)
    alive_store.save(_entry(3000, "my-frontend", pid=99))
    alive_removed = _svc(alive_store, alive_probe).clean()
    assert alive_removed == []
    assert alive_store.get(3000) is not None


# ------------------------------------------------------------------ next_port


def test_next_port_table() -> None:
    base_port, base_is_base = _svc().next_port("my-service")
    assert base_port == 3073  # md5("my-service") base port
    assert base_is_base is True

    existing_store = FakeServerRegistryStore()
    existing_probe = FakeProcessProbe()
    existing_probe._alive_pids.add(99)
    existing_store.save(_entry(3073, "my-service", pid=99))
    existing_port, existing_is_base = _svc(existing_store, existing_probe).next_port("my-service")
    assert existing_port == 3073
    assert existing_is_base is True

    occupied_store = FakeServerRegistryStore()
    occupied_probe = FakeProcessProbe()
    occupied_probe._alive_pids.add(99)
    occupied_store.save(
        PortEntry(
            port=3073,
            project="other",
            reserved_at="2026-05-16T10:00:00Z",
            expires_at="2099-12-31T23:59:59Z",
            pid=99,
        )
    )
    inc_port, inc_is_base = _svc(occupied_store, occupied_probe).next_port("my-service")
    assert inc_port != 3073
    assert 3000 <= inc_port <= 3999
    assert inc_is_base is False

    custom_port, _ = _svc().next_port("my-service", min_port=4000, max_port=4099)
    assert 4000 <= custom_port <= 4099
