"""Unit tests for JsonContextStore."""

from pathlib import Path

from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore


def _make_ctx(
    name: str = "myctx",
    state: ContextState = ContextState.INATIVO,
    is_primary: bool = False,
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=state,
        repo_slug=name,
        repo_url=f"https://github.com/org/{name}",
        is_primary=is_primary,
        created_at="2026-01-01T00:00:00",
        activated_at=None,
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
    ctx = _make_ctx("myctx", state=ContextState.INATIVO)
    store.save(ctx)
    updated = SpecContextProject(
        name="myctx",
        state=ContextState.ATIVO,
        repo_slug="myctx",
        repo_url="https://github.com/org/myctx",
        is_primary=True,
        created_at="2026-01-01T00:00:00",
        activated_at="2026-06-01T00:00:00",
        current_branch="main",
    )
    store.update(updated)
    fetched = store.get("myctx")
    assert fetched is not None
    assert fetched.state == ContextState.ATIVO
    assert fetched.is_primary is True
    assert fetched.activated_at == "2026-06-01T00:00:00"
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
