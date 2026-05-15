"""Unit tests for JsonPrimaryContextStore."""

from pathlib import Path

from dadaia_workspace.infrastructure.json_primary_context_store import JsonPrimaryContextStore


def test_read_returns_none_when_file_absent(tmp_path: Path) -> None:
    store = JsonPrimaryContextStore(tmp_path)
    assert store.read() is None


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    store = JsonPrimaryContextStore(tmp_path)
    store.write("myctx", "myctx", Path("/specs/myctx"))
    data = store.read()
    assert data is not None
    assert data["name"] == "myctx"
    assert data["repo_slug"] == "myctx"
    assert data["specs_dir"] == "/specs/myctx"


def test_write_overwrites_previous(tmp_path: Path) -> None:
    store = JsonPrimaryContextStore(tmp_path)
    store.write("first", "first", Path("/specs/first"))
    store.write("second", "second", Path("/specs/second"))
    data = store.read()
    assert data is not None
    assert data["name"] == "second"


def test_clear_removes_file(tmp_path: Path) -> None:
    store = JsonPrimaryContextStore(tmp_path)
    store.write("myctx", "myctx", Path("/specs/myctx"))
    store.clear()
    assert store.read() is None


def test_clear_when_no_file_is_noop(tmp_path: Path) -> None:
    store = JsonPrimaryContextStore(tmp_path)
    store.clear()  # must not raise


def test_write_persists_to_disk(tmp_path: Path) -> None:
    store = JsonPrimaryContextStore(tmp_path)
    store.write("ctx", "slug", Path("/s"))
    store2 = JsonPrimaryContextStore(tmp_path)
    data = store2.read()
    assert data is not None
    assert data["name"] == "ctx"
