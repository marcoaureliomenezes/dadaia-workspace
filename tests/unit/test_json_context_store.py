"""Unit tests for JsonContextStore (v2 schema: ALIVE/DEAD)."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import SchemaVersionError
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def _make_ctx(
    name: str = "myctx",
    state: ContextState = ContextState.DEAD,
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=name,
        repo_url=f"https://github.com/org/{name}",
        created_at="2026-01-01T00:00:00",
        alive_since=None,
        dead_since=None,
        current_branch=None,
    )


def test_list_all_empty_when_no_file(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    assert store.list_all() == []


def test_get_returns_none_when_not_found(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    assert store.get("ghost") is None


def test_save_and_get_roundtrip(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    ctx = _make_ctx("alpha")
    store.save(ctx)
    assert store.get("alpha") == ctx


def test_save_multiple_and_list_all(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    a = _make_ctx("a")
    b = _make_ctx("b")
    store.save(a)
    store.save(b)
    result = store.list_all()
    assert len(result) == 2
    assert {c.name for c in result} == {"a", "b"}


def test_update_replaces_existing(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    ctx = _make_ctx("myctx", state=ContextState.DEAD)
    store.save(ctx)
    updated = SpecContextProject(
        name="myctx",
        state=ContextState.ALIVE,
        repo_slug="myctx",
        repo_url="https://github.com/org/myctx",
        created_at="2026-01-01T00:00:00",
        alive_since="2026-06-01T00:00:00",
        dead_since=None,
        current_branch="main",
    )
    store.update(updated)
    fetched = store.get("myctx")
    assert fetched is not None
    assert fetched.state == ContextState.ALIVE
    assert fetched.alive_since == "2026-06-01T00:00:00"
    assert fetched.current_branch == "main"


def test_delete_removes_context(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    ctx = _make_ctx("todel")
    store.save(ctx)
    store.delete("todel")
    assert store.get("todel") is None
    assert store.list_all() == []


def test_delete_nonexistent_is_noop(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    store.delete("ghost")  # must not raise


def test_save_persists_to_disk(tmp_path: Path) -> None:
    store = JsonContextStore(tmp_path)
    store.save(_make_ctx("persist"))
    store2 = JsonContextStore(tmp_path)
    assert store2.get("persist") is not None


# ---------------------------------------------------------------------------
# AC-T10a-5: Loading a schema_version="1" file raises SchemaVersionError
# ---------------------------------------------------------------------------


def test_load_v1_schema_version_raises_schema_version_error(tmp_path: Path) -> None:
    """AC-T10a-5: schema_version "1" must raise SchemaVersionError with 'dadaia migrate'."""
    ctx_file = tmp_path / "spec_contexts.json"
    v1_data = {
        "schema_version": "1",
        "contexts": [
            {
                "name": "old-ctx",
                "state": "ativo",
                "repo_slug": "old-ctx",
                "repo_url": "https://github.com/org/old-ctx",
                "is_primary": False,
                "created_at": "2026-01-01T00:00:00Z",
                "activated_at": "2026-05-01T00:00:00Z",
            }
        ],
    }
    ctx_file.write_text(json.dumps(v1_data), encoding="utf-8")
    store = JsonContextStore(tmp_path)
    with pytest.raises(SchemaVersionError) as exc_info:
        store.list_all()
    assert "dadaia migrate" in str(exc_info.value)


def test_load_v1_version_key_raises_schema_version_error(tmp_path: Path) -> None:
    """AC-T10a-5 (variant): v1 'version' key also raises SchemaVersionError."""
    ctx_file = tmp_path / "spec_contexts.json"
    v1_data = {
        "version": "1",
        "contexts": [],
    }
    ctx_file.write_text(json.dumps(v1_data), encoding="utf-8")
    store = JsonContextStore(tmp_path)
    with pytest.raises(SchemaVersionError) as exc_info:
        store.list_all()
    assert "dadaia migrate" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-T10a-6: Loading a file with state "ativo" raises SchemaVersionError
# ---------------------------------------------------------------------------


def test_load_ativo_state_raises_schema_version_error(tmp_path: Path) -> None:
    """AC-T10a-6: state 'ativo' in any context row must raise SchemaVersionError."""
    ctx_file = tmp_path / "spec_contexts.json"
    legacy_data = {
        "schema_version": "2",  # claims v2 but has legacy state values
        "contexts": [
            {
                "name": "bad-ctx",
                "state": "ativo",
                "repo_slug": "bad-ctx",
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": None,
                "dead_since": None,
            }
        ],
    }
    ctx_file.write_text(json.dumps(legacy_data), encoding="utf-8")
    store = JsonContextStore(tmp_path)
    with pytest.raises(SchemaVersionError) as exc_info:
        store.list_all()
    assert "dadaia migrate" in str(exc_info.value)


def test_load_inativo_state_raises_schema_version_error(tmp_path: Path) -> None:
    """AC-T10a-6 (variant): state 'inativo' also raises SchemaVersionError."""
    ctx_file = tmp_path / "spec_contexts.json"
    legacy_data = {
        "contexts": [
            {
                "name": "bad-ctx",
                "state": "inativo",
                "repo_slug": "bad-ctx",
                "repo_url": "",
                "created_at": "2026-01-01T00:00:00Z",
            }
        ],
    }
    ctx_file.write_text(json.dumps(legacy_data), encoding="utf-8")
    store = JsonContextStore(tmp_path)
    with pytest.raises(SchemaVersionError) as exc_info:
        store.list_all()
    assert "dadaia migrate" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-T10a-7: Written JSON must not contain is_primary or activated_at
# ---------------------------------------------------------------------------


def test_written_json_has_no_is_primary_or_activated_at(tmp_path: Path) -> None:
    """AC-T10a-7: spec_contexts.json written by the store has no legacy fields."""
    store = JsonContextStore(tmp_path)
    ctx = SpecContextProject(
        name="myctx",
        state=ContextState.ALIVE,
        repo_slug="myctx",
        repo_url="https://github.com/org/myctx",
        created_at="2026-01-01T00:00:00Z",
        alive_since="2026-05-01T00:00:00Z",
        dead_since=None,
        current_branch="main",
    )
    store.save(ctx)
    ctx_file = tmp_path / "spec_contexts.json"
    data = json.loads(ctx_file.read_text())
    row = data["contexts"][0]
    assert "is_primary" not in row
    assert "activated_at" not in row
    assert data["schema_version"] == "2"
    assert "alive_since" in row
    assert "dead_since" in row
