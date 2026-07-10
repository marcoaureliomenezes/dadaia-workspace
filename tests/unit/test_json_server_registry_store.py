"""Unit tests for JsonServerRegistryStore."""

import json
from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore


def _entry(port: int = 3000, project: str = "my-project") -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2026-05-16T18:00:00Z",
    )


def test_crud_round_trips(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)

    assert store.list_all() == []
    assert store.get(8000) is None

    entry = _entry(3000)
    store.save(entry)
    fetched = store.get(3000)
    assert fetched is not None
    assert fetched.port == 3000
    assert fetched.project == "my-project"

    # Persistence survives a fresh store instance.
    store2 = JsonServerRegistryStore(tmp_path)
    assert store2.get(3000) is not None

    store.update(_entry(3000, "new-project"))
    updated = store.get(3000)
    assert updated is not None and updated.project == "new-project"

    store.delete(3000)
    assert store.get(3000) is None
    assert store.list_all() == []

    store.delete(9999)  # must not raise (delete of nonexistent is a no-op)


def test_list_all_sorted_and_optional_fields_preserved(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3002))
    store.save(_entry(3000))
    store.save(_entry(3001))
    ports = [e.port for e in store.list_all()]
    assert ports == [3000, 3001, 3002]

    optional_dir = tmp_path / "optional"
    optional_dir.mkdir()
    optional_store = JsonServerRegistryStore(optional_dir)
    entry = PortEntry(
        port=3000,
        project="my-project",
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2026-05-16T18:00:00Z",
        url="http://0.0.0.0:3000",
        pid=12345,
        description="Vite dev server",
    )
    optional_store.save(entry)
    fetched = optional_store.get(3000)
    assert fetched is not None
    assert fetched.url == "http://0.0.0.0:3000"
    assert fetched.pid == 12345
    assert fetched.description == "Vite dev server"


def test_atomic_write_no_tmp_left_and_version_field_written(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000))

    tmp_file = tmp_path / "server_registry.tmp"
    assert not tmp_file.exists()

    raw = json.loads((tmp_path / "server_registry.json").read_text())
    assert raw["version"] == "1"
