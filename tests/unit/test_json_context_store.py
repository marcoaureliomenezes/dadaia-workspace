"""Unit tests for JsonContextStore (v3 schema: ALIVE/DEAD + associated_repos).

Intent: CONTRACT — A15.2, A15.3 (registry-schema half; the model half lives in
tests/unit/core/models/test_spec_context.py). v2→v3 is purely additive
(``associated_repos``), so — unlike the v1→v2 state-string rename — the store tolerates
a v2 file on read rather than hard-refusing it: a hard version gate with no repair path
reachable from every phase is exactly the bug class of
``memory-agent-tier-migration-deadlock`` (CRITICAL, v0.1.72), and the CLI wiring that
would supply that repair path is out of this task's write set.
"""

import json
from pathlib import Path

from dadaia_workspace.core.models.spec_context import (
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.stores import context_store


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


def test_crud_round_trips(tmp_path: Path) -> None:
    store = context_store(tmp_path)

    assert store.list_all() == []
    assert store.get("ghost") is None

    ctx = _make_ctx("alpha")
    store.save(ctx)
    assert store.get("alpha") == ctx

    b = _make_ctx("b")
    store.save(b)
    result = store.list_all()
    assert len(result) == 2
    assert {c.name for c in result} == {"alpha", "b"}

    updated = SpecContextProject(
        name="alpha",
        state=ContextState.ALIVE,
        repo_slug="alpha",
        repo_url="https://github.com/org/alpha",
        created_at="2026-01-01T00:00:00",
        alive_since="2026-06-01T00:00:00",
        dead_since=None,
        current_branch="main",
    )
    store.update(updated)
    fetched = store.get("alpha")
    assert fetched is not None
    assert fetched.state == ContextState.ALIVE
    assert fetched.alive_since == "2026-06-01T00:00:00"
    assert fetched.current_branch == "main"

    store.delete("alpha")
    assert store.get("alpha") is None
    remaining = store.list_all()
    assert {c.name for c in remaining} == {"b"}

    store.delete("ghost")  # must not raise (delete of nonexistent is a no-op)

    # Persistence survives a fresh store instance over the same tmp_path.
    store.save(_make_ctx("persist"))
    store2 = JsonContextStore(tmp_path)
    assert store2.get("persist") is not None


# ---------------------------------------------------------------------------
# FR15/A15.3: associated_repos round-trips through the one registry schema.
# ---------------------------------------------------------------------------


def test_associated_repos_round_trip_through_store(tmp_path: Path) -> None:
    store = context_store(tmp_path)
    ctx = SpecContextProject(
        name="withrepos",
        state=ContextState.ALIVE,
        repo_slug="withrepos",
        repo_url="https://github.com/org/withrepos",
        created_at="2026-01-01T00:00:00Z",
        associated_repos=(
            AssociatedRepo(slug="assoc-a", url="https://github.com/org/assoc-a"),
            AssociatedRepo(slug="assoc-b", url="https://github.com/org/assoc-b"),
        ),
    )
    store.save(ctx)

    fetched = store.get("withrepos")
    assert fetched is not None
    assert fetched.associated_repos == ctx.associated_repos

    raw = json.loads((tmp_path / "spec_contexts.json").read_text())
    row = raw["contexts"][0]
    assert row["associated_repos"] == [
        {"slug": "assoc-a", "url": "https://github.com/org/assoc-a"},
        {"slug": "assoc-b", "url": "https://github.com/org/assoc-b"},
    ]


# ---------------------------------------------------------------------------
# FR15/A15.2: a v2 registry (no associated_repos key) reads as behaviourally
# identical to a v3 registry with zero associated repos — no migration required
# to keep reading. See module docstring for why: the CLI repair path is out of
# scope here, so hard-gating v2 on read would reproduce a known deadlock class.
# ---------------------------------------------------------------------------


def test_v2_registry_loads_with_empty_associated_repos(tmp_path: Path) -> None:
    v2_payload = {
        "schema_version": "2",
        "contexts": [
            {
                "name": "legacy-ctx",
                "state": "alive",
                "repo_slug": "legacy-ctx",
                "repo_url": "https://github.com/org/legacy-ctx",
                "created_at": "2026-01-01T00:00:00Z",
                "alive_since": "2026-01-02T00:00:00Z",
                "dead_since": None,
                "current_branch": "main",
                # no "associated_repos" key — the real shape of a pre-FR15 file.
            }
        ],
    }
    (tmp_path / "spec_contexts.json").write_text(json.dumps(v2_payload), encoding="utf-8")
    store = JsonContextStore(tmp_path)

    fetched = store.get("legacy-ctx")
    assert fetched is not None
    assert fetched.associated_repos == ()
    assert fetched.all_repos() == (
        AssociatedRepo(slug="legacy-ctx", url="https://github.com/org/legacy-ctx"),
    )

    # list_all() must not raise SchemaVersionError for a plain v2 file either.
    assert [c.name for c in store.list_all()] == ["legacy-ctx"]


def test_a_fresh_store_writes_v3_rows_without_legacy_fields(tmp_path: Path) -> None:
    """AC-T10a-7: spec_contexts.json written by the store has no legacy fields —
    is_primary / activated_at never round-trip."""
    fresh_ws = tmp_path
    fresh_store = context_store(fresh_ws)
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
    fresh_store.save(ctx)
    fresh_ctx_file = fresh_ws / "spec_contexts.json"
    data = json.loads(fresh_ctx_file.read_text())
    row = data["contexts"][0]
    assert "is_primary" not in row
    assert "activated_at" not in row
    assert "alive_since" in row
    assert "dead_since" in row
    assert row["associated_repos"] == []
