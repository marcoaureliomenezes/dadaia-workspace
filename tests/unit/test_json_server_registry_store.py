"""Unit tests for JsonServerRegistryStore."""

from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.infrastructure.json_server_registry_store import JsonServerRegistryStore


def _entry(port: int = 3000, project: str = "portifolio") -> PortEntry:
    return PortEntry(
        port=port,
        project=project,
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2026-05-16T18:00:00Z",
    )


def test_list_all_empty_when_no_file(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    assert store.list_all() == []


def test_get_returns_none_when_missing(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    assert store.get(8000) is None


def test_save_and_get_roundtrip(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    entry = _entry(3000)
    store.save(entry)
    fetched = store.get(3000)
    assert fetched is not None
    assert fetched.port == 3000
    assert fetched.project == "portifolio"


def test_save_persists_to_disk(tmp_path: Path) -> None:
    JsonServerRegistryStore(tmp_path).save(_entry(3000))
    store2 = JsonServerRegistryStore(tmp_path)
    assert store2.get(3000) is not None


def test_update_replaces_entry(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000, "old-project"))
    store.update(_entry(3000, "new-project"))
    assert store.get(3000).project == "new-project"  # type: ignore[union-attr]


def test_delete_removes_entry(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000))
    store.delete(3000)
    assert store.get(3000) is None
    assert store.list_all() == []


def test_delete_nonexistent_is_noop(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.delete(9999)  # must not raise


def test_list_all_sorted_by_port(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3002))
    store.save(_entry(3000))
    store.save(_entry(3001))
    ports = [e.port for e in store.list_all()]
    assert ports == [3000, 3001, 3002]


def test_optional_fields_preserved(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    entry = PortEntry(
        port=3000,
        project="portifolio",
        reserved_at="2026-05-16T10:00:00Z",
        expires_at="2026-05-16T18:00:00Z",
        url="http://0.0.0.0:3000",
        pid=12345,
        description="Vite dev server",
    )
    store.save(entry)
    fetched = store.get(3000)
    assert fetched is not None
    assert fetched.url == "http://0.0.0.0:3000"
    assert fetched.pid == 12345
    assert fetched.description == "Vite dev server"


def test_atomic_write_no_tmp_file_remains(tmp_path: Path) -> None:
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000))
    tmp_file = tmp_path / "server_registry.tmp"
    assert not tmp_file.exists()


def test_version_field_written_to_disk(tmp_path: Path) -> None:
    import json
    store = JsonServerRegistryStore(tmp_path)
    store.save(_entry(3000))
    raw = json.loads((tmp_path / "server_registry.json").read_text())
    assert raw["version"] == "1"
