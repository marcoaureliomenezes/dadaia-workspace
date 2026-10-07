"""``core.invocation`` — the single session/context/root/Bind resolution authority.

0.5.1 K1 ("One Invocation"): the rung table asserts observable outcomes
through :func:`invocation.resolve`, never internal ladder state. Also covers
``sdd-gate-memory-phase-resolves-empty-when-cwd-is-a-linked-worktree-outside-repos``: a nested
sentinel-bearing sandbox under cwd never shadows the workspace that owns the write target.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.core import invocation
from dadaia_workspace.core.exceptions import SchemaVersionError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root


def _mk_ws(tmp_path: Path, *contexts: tuple[str, str, tuple[str, ...]]) -> Path:
    """A workspace registering each ``(slug, name, associated)`` context ALIVE, repos on disk."""
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    entries = []
    for slug, name, associated in contexts or (("proj", "proj", ()),):
        (ws / "repos" / slug / "specs").mkdir(parents=True)
        for repo in associated:
            (ws / "repos" / repo).mkdir(parents=True)
        entry = {"name": name, "repo_slug": slug, "state": "alive"}
        entries.append({**entry, "associated_repos": [{"slug": s} for s in associated]})
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": entries}), encoding="utf-8"
    )
    return ws


def _ctx(slug: str, name: str | None = None, *associated: str) -> tuple[str, str, tuple[str, ...]]:
    return (slug, name or slug, associated)


XY = (_ctx("x"), _ctx("y"))
PROJ_OTHER = (_ctx("proj"), _ctx("other"))


@pytest.mark.parametrize(
    ("given", "then"),
    [
        pytest.param({"contexts": XY, "session": ("y", 0), "env": {"DADAIA_CONTEXT": "y"}, "target": "repos/x/specs/TASKS.md", "explicit": "explicit-ctx"}, {"context_name": "explicit-ctx", "rung": "explicit"}, id="explicit_wins_over_target_env_and_session"),
        pytest.param({"contexts": XY, "env": {"DADAIA_CONTEXT": "y"}, "target": "repos/x/specs/releases/v1/TASKS.md"}, {"context_name": "x", "rung": "target_path"}, id="rung0_target_path_wins_over_dadaia_context"),
        pytest.param({"contexts": (_ctx("beta-repo", "alpha-context"),), "target": "repos/beta-repo/specs/SPEC.md"}, {"context_name": "alpha-context", "repo_slug": "beta-repo", "rung": "target_path"}, id="rung0_target_path_maps_slug_to_name_via_registry"),
        pytest.param({"contexts": XY, "env": {"DADAIA_CONTEXT": "y"}, "target": "specs/bugs/bugs.jsonl"}, {"context_name": "y", "rung": "bind"}, id="rung0_target_outside_repo_falls_through_to_env"),
        pytest.param({"env": {"DADAIA_CONTEXT": "proj"}}, {"context_name": "proj", "rung": "bind"}, id="rung_env_dadaia_context_alone"),
        pytest.param({"contexts": PROJ_OTHER, "session": ("other", 0), "env": {"DADAIA_CONTEXT": "proj"}}, {"context_name": "other", "bind.context_name": "other"}, id="sa-bind-has-two-stores#S1 record wins over env for a session with an id"),
        pytest.param({"contexts": PROJ_OTHER, "session": ("proj", 0), "cwd": "repos/other"}, {"context_name": "proj", "rung": "bind"}, id="rung_session_wins_over_cwd"),
        pytest.param({"contexts": PROJ_OTHER, "session": ("proj", 90000), "cwd": "repos/other"}, {"context_name": "other", "rung": "cwd"}, id="rung_session_stale_falls_through_to_cwd"),
        pytest.param({"contexts": (_ctx("other"),), "session": ("deleted-ctx", 0), "cwd": "repos/other"}, {"context_name": "other", "rung": "cwd"}, id="rung_session_deleted_context_guard_falls_through_to_cwd"),
        pytest.param({"cwd": "repos/proj/specs"}, {"context_name": "proj", "rung": "cwd"}, id="rung_cwd_alone_resolves"),
        pytest.param({"contexts": (_ctx("beta-repo", "alpha-context"),), "cwd": "repos/beta-repo/specs"}, {"context_name": "alpha-context", "repo_slug": "beta-repo"}, id="rung_cwd_maps_slug_to_name_via_registry"),
        pytest.param({"cwd": None}, {"workspace_root": None, "session_id": None, "context_name": None, "repo_slug": None, "specs_dir": None, "bind.context_name": None, "rung": "none"}, id="nothing_resolves_missing_workspace"),
        pytest.param({"contexts": (_ctx("dadaia-workspace"),), "nested": ".dadaia/tmp/agent-x/worktree", "target": "repos/dadaia-workspace/specs/memory/atom.md"}, {"context_name": "dadaia-workspace", "workspace_root": "ws", "specs_dir": "repos/dadaia-workspace/specs"}, id="open_bug_linked_worktree_outside_repos_root_resolves_from_target"),
        pytest.param({"contexts": (_ctx("proj"), _ctx("other", None, "other-infra")), "env": {"DADAIA_CONTEXT": "other"}, "cwd": "repos/proj"}, {"bind.context_name": "other", "bind.repos": frozenset({"other", "other-infra"})}, id="bind_carries_the_context_scope_main_plus_associated"),
        pytest.param({"cwd": "repos/proj"}, {"bind.context_name": None, "bind.repos": frozenset()}, id="bind_is_empty_when_the_session_never_bound_even_inside_a_repo"),
    ],
)  # fmt: skip
def test_resolve_scenarios(tmp_path: Path, given: dict[str, Any], then: dict[str, Any]) -> None:
    """Each rung wins over the ones below it; a stale or deleted session falls through."""
    ws = _mk_ws(tmp_path, *given.get("contexts", ()))
    env = dict(given.get("env", {}))
    if session := given.get("session"):
        ctx, age = session
        seen = (datetime.now(tz=UTC) - timedelta(seconds=age)).isoformat()
        record = {
            "session_id": "sid",
            "context": ctx,
            "mode": "READ",
            "last_seen_at": seen,
        }
        (ws / ".dadaia" / "sessions" / "sid.json").write_text(json.dumps(record), encoding="utf-8")
        env["CLAUDE_CODE_SESSION_ID"] = "sid"
    cwd = ws / given.get("cwd", "") if given.get("cwd", "") is not None else tmp_path
    if nested := given.get("nested"):
        cwd = ws / nested
        (cwd / ".dadaia" / "states").mkdir(parents=True)
        (cwd / ".dadaia" / "states" / "spec_contexts.json").write_text('{"contexts": []}', "utf-8")
        assert resolve_workspace_root(cwd) == cwd.resolve()  # the trap is real for a cwd walk
    target = ws / given["target"] if "target" in given else None
    inv = invocation.resolve(explicit=given.get("explicit"), target_path=target, env=env, cwd=cwd)
    for attr, expected in then.items():
        actual = inv.bind if attr.startswith("bind.") else inv
        actual = getattr(actual, attr.removeprefix("bind."))
        if attr in ("workspace_root", "specs_dir") and expected is not None:
            expected = (ws / ("" if expected == "ws" else expected)).resolve()
        assert actual == expected, (attr, inv)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        pytest.param({"CLAUDE_CODE_SESSION_ID": "harness-env"}, "harness-env", id="harness_env"),
        pytest.param({"CODEX_SESSION_ID": "codex", "DADAIA_SESSION_ID": "explicit"}, "explicit", id="dadaia_override_first"),
        pytest.param({}, "", id="empty_when_nothing_resolves"),
        pytest.param({"CODEX_THREAD_ID": "thread-1"}, "thread-1", id="codex_thread_id_resolves_when_no_codex_session_id"),
        pytest.param({"CODEX_SESSION_ID": "sess-1", "CODEX_THREAD_ID": "thread-1"}, "sess-1", id="codex_session_id_preferred_over_codex_thread_id"),
    ],
)  # fmt: skip
def test_resolve_session_id_precedence(env: dict[str, str], expected: str) -> None:
    """DADAIA_SESSION_ID > harness env > ""; env only — bind sees no payload (review F1)."""
    assert invocation.resolve_session_id(env) == expected


def test_context_name_for_repo_slug_maps_main_associated_and_legacy_repo_field(
    tmp_path: Path,
) -> None:
    """A16.4: a main slug maps to its context name, an associated slug to its OWNING context;
    a legacy ``repo`` field still maps."""
    ws = _mk_ws(tmp_path, _ctx("beta-repo", "alpha-context"), _ctx("other", None, "assoc-repo"))
    assert invocation.context_name_for_repo_slug(ws, "beta-repo") == "alpha-context"
    assert invocation.context_name_for_repo_slug(ws, "assoc-repo") == "other"
    legacy = {"schema_version": "2", "contexts": [{"name": "alpha-context", "repo": "beta-repo"}]}
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(json.dumps(legacy), "utf-8")
    assert invocation.context_name_for_repo_slug(ws, "beta-repo") == "alpha-context"


def test_an_unowned_repo_resolves_no_context(tmp_path: Path) -> None:
    """sa-context-repo-mapping-falls-back-to-the-name#B1: repos/foo on disk, owned by no
    registered context: the mapping answers None and resolve() from repos/foo binds no
    context named after the directory (DELETE-LOSER: the three name-fallback tests)."""
    ws = _mk_ws(tmp_path)
    (ws / "repos" / "foo").mkdir()
    assert invocation.context_name_for_repo_slug(ws, "foo") is None
    assert invocation.repo_slug_for_context(ws, "foo") is None
    inv = invocation.resolve(env={}, cwd=ws / "repos" / "foo")
    assert inv.context_name is None and inv.specs_dir is None


@pytest.mark.parametrize(
    "body",
    ['{"contexts": [{"na', "{}", '{"contexts": ' + "[" * 100_000],
    ids=["truncated", "empty-object", "deep-nesting"],
)
def test_an_unreadable_registry_refuses_never_answers_no_context(tmp_path: Path, body: str) -> None:
    """AC3.9 (rewrites sa-context-repo-mapping-falls-back-to-the-name#B4's fail-soft leg):
    the name list, the slug mapping and the bind each raise REG-SCHEMA's refusal; the gate
    maps it to no bind (test_sdd_gate)."""
    ws = _mk_ws(tmp_path)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text(body, "utf-8")
    for read in (
        lambda: invocation.alive_context_names(ws),
        lambda: invocation.context_name_for_repo_slug(ws, "proj"),
        lambda: invocation.resolve_bind(ws, None, {"DADAIA_CONTEXT": "proj"}),
    ):
        with pytest.raises(SchemaVersionError, match="Operator action: rewrite"):
            read()


def test_resolve_specs_dir_explicit_wins_else_cwd_inside_a_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit root wins even with no bound context; otherwise cwd inside a repo resolves."""
    (tmp_path / "explicit-specs").mkdir()
    assert (
        invocation.resolve_specs_dir(str(tmp_path / "explicit-specs"))
        == (tmp_path / "explicit-specs").resolve()
    )
    ws = _mk_ws(tmp_path)
    monkeypatch.chdir(ws / "repos" / "proj")
    assert invocation.resolve_specs_dir(None) == (ws / "repos" / "proj" / "specs").resolve()


def test_resolve_specs_dir_refuses_a_symlinked_explicit_root(tmp_path: Path) -> None:
    """A symlinked explicit specs root is refused, never followed."""
    (tmp_path / "real-specs").mkdir()
    (tmp_path / "linked-specs").symlink_to(tmp_path / "real-specs", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        invocation.resolve_specs_dir(str(tmp_path / "linked-specs"))


class TestAliveContextNames:
    """F008 (20260830 audit): the registry read family has ONE home — invocation."""

    def test_alive_filter_yields_context_names(self, tmp_path: Path) -> None:
        """Only ALIVE entries (case-insensitive) yield their name."""
        states = tmp_path / ".dadaia" / "states"
        states.mkdir(parents=True)
        contexts = [
            {"name": "pretty", "repo_slug": "actual-dir", "state": "alive"},
            {"name": "gone", "repo_slug": "gone-dir", "state": "dead"},
            {"name": "bare", "state": "ALIVE"},
        ]
        (states / "spec_contexts.json").write_text(json.dumps({"contexts": contexts}), "utf-8")
        assert invocation.alive_context_names(tmp_path) == ["pretty", "bare"]


def test_a_row_without_a_main_slug_has_no_specs_tree(tmp_path: Path) -> None:
    """J2.S6.T5 (review F7): a hand-edited ALIVE row whose main slug is empty or absent maps
    to no ``repos/<slug>/specs`` tree; the other ALIVE contexts still do."""
    ws = _mk_ws(tmp_path)
    path = ws / ".dadaia" / "states" / "spec_contexts.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["contexts"] += [{"name": "blank", "repo_slug": "", "state": "alive"},
                         {"name": "bare", "state": "alive"}]  # fmt: skip
    path.write_text(json.dumps(data), encoding="utf-8")

    assert invocation.alive_context_trees(ws) == {"proj": ws / "repos" / "proj" / "specs"}
    assert invocation.repo_slug_for_context(ws, "blank") is None
    assert invocation.alive_context_names(ws) == ["proj", "blank", "bare"]
