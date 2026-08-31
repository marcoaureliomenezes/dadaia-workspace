"""``core.invocation`` — the single session/context/root/mode resolution authority.

Intent: CONTRACT — release 0.5.1 candidate K1 ("One Invocation"). Replaces, at the new
deepened interface, the eight deciders / three sid ladders / four staleness rules the
deepening audit (2026-08-28) named: ``tests/unit/core/test_specs_resolver.py``,
``test_specs_resolver_resolve_context.py``, ``test_specs_resolver_associated_repo_walk.py``,
``test_specs_resolver_delete_bind.py``, ``tests/unit/core/test_session_env.py``,
``tests/unit/hooks/test_common_sid_precedence.py``. Per the deepening discipline
(``codebase-design/DEEPENING.md`` — "replace, don't layer"): these tables assert
observable outcomes through :func:`~dadaia_workspace.core.invocation.resolve`'s single
interface, not internal ladder state, so they describe behavior rather than pinning any
one of the deleted implementations.

Also covers the open bug ``sdd-gate-memory-phase-resolves-empty-when-cwd-is-a-linked-
worktree-outside-repos``: a cwd sitting inside a nested, independently sentinel-bearing
sandbox workspace must never shadow the real workspace root that owns an explicit write
target — the root is resolved from the TARGET first, not from cwd, whenever a target is
known.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import typer

from dadaia_workspace.core import invocation
from dadaia_workspace.core.invocation import Invocation
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root
from tests.fixtures.harness_env import scrub_context_resolution_env

# --------------------------------------------------------------------------- fixture builders


def _mk_ws(tmp_path: Path, *, slug: str = "proj", name: str | None = None) -> Path:
    """A minimal initialized workspace with one registered ALIVE context."""
    ws = tmp_path / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [{"name": name or slug, "repo_slug": slug, "state": "alive"}],
            }
        ),
        encoding="utf-8",
    )
    (ws / "repos" / slug / "specs").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    return ws


def _register_context(
    ws: Path, *, slug: str, name: str | None = None, associated: list[str] | None = None
) -> None:
    """Add a second registered context (optionally with associated repos) + its repo dir."""
    registry = ws / ".dadaia" / "states" / "spec_contexts.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    entry: dict[str, object] = {"name": name or slug, "repo_slug": slug, "state": "alive"}
    if associated:
        entry["associated_repos"] = [{"slug": s} for s in associated]
        for s in associated:
            (ws / "repos" / s).mkdir(parents=True, exist_ok=True)
    data["contexts"].append(entry)
    registry.write_text(json.dumps(data), encoding="utf-8")
    (ws / "repos" / slug / "specs").mkdir(parents=True, exist_ok=True)


def _write_session(
    ws: Path,
    session_id: str,
    context: str,
    *,
    mode: str = "READ",
    age_seconds: int = 0,
    ttl: int = 300,
) -> None:
    """Seed ``sessions/<id>.json`` as ``bind`` would, with a controllable heartbeat age."""
    last_seen = (datetime.now(tz=UTC) - timedelta(seconds=age_seconds)).isoformat()
    (ws / ".dadaia" / "sessions" / f"{session_id}.json").write_text(
        json.dumps(
            {
                "session_id": session_id,
                "context": context,
                "mode": mode,
                "last_seen_at": last_seen,
                "ttl_seconds": ttl,
            }
        ),
        encoding="utf-8",
    )


def _write_release(specs_dir: Path, release_id: str, phase: str) -> None:
    release_dir = specs_dir / "releases" / release_id
    release_dir.mkdir(parents=True, exist_ok=True)
    (release_dir / "RELEASE.json").write_text(
        json.dumps(
            {
                "schema": "release-state-v1",
                "release": release_id,
                "phase": phase,
                "rc": 1,
                "defined": None,
                "implemented": None,
                "shipped": None,
                "audited": None,
                "log": [],
            }
        ),
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- resolve() — the table


@dataclass(frozen=True)
class Scenario:
    name: str
    build: Callable[[Path], dict[str, object]]
    check: Callable[[Invocation], bool]


def _explicit_wins(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="x")
    _register_context(ws, slug="y")
    sid = "sess-explicit"
    _write_session(ws, sid, "y")
    target = ws / "repos" / "x" / "specs" / "TASKS.md"
    return {
        "explicit": "explicit-ctx",
        "target_path": target,
        "env": {"DADAIA_CONTEXT": "y", "CLAUDE_CODE_SESSION_ID": sid},
        "cwd": ws,
    }


def _target_path_beats_env(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="x")
    _register_context(ws, slug="y")
    target = ws / "repos" / "x" / "specs" / "releases" / "v1" / "TASKS.md"
    return {"target_path": target, "env": {"DADAIA_CONTEXT": "y"}, "cwd": ws}


def _target_path_maps_slug_to_name(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="beta-repo", name="alpha-context")
    target = ws / "repos" / "beta-repo" / "specs" / "SPEC.md"
    return {"target_path": target, "env": {}, "cwd": ws}


def _target_path_outside_repo_falls_to_env(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="x")
    _register_context(ws, slug="y")
    target = ws / "specs" / "bugs" / "bugs.jsonl"
    return {"target_path": target, "env": {"DADAIA_CONTEXT": "y"}, "cwd": ws}


def _env_alone_resolves(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    return {"env": {"DADAIA_CONTEXT": "proj"}, "cwd": ws}


def _env_wins_over_session(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    _register_context(ws, slug="other")
    sid = "sess-env-wins"
    _write_session(ws, sid, "other")
    return {"env": {"DADAIA_CONTEXT": "proj", "CLAUDE_CODE_SESSION_ID": sid}, "cwd": ws}


def _session_wins_over_cwd(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    _register_context(ws, slug="other")
    sid = "sess-ahead-of-cwd"
    _write_session(ws, sid, "proj")
    return {"env": {"CLAUDE_CODE_SESSION_ID": sid}, "cwd": ws / "repos" / "other"}


def _stale_session_falls_through_to_cwd(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    _register_context(ws, slug="other")
    sid = "sess-stale"
    _write_session(ws, sid, "proj", age_seconds=4000, ttl=300)
    return {"env": {"CLAUDE_CODE_SESSION_ID": sid}, "cwd": ws / "repos" / "other"}


def _deleted_context_guard_falls_through(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="other")
    sid = "sess-deleted-ctx"
    _write_session(ws, sid, "deleted-ctx")
    return {"env": {"CLAUDE_CODE_SESSION_ID": sid}, "cwd": ws / "repos" / "other"}


def _cwd_alone_resolves(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    return {"env": {}, "cwd": ws / "repos" / "proj" / "specs"}


def _cwd_maps_slug_to_name(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="beta-repo", name="alpha-context")
    return {"env": {}, "cwd": ws / "repos" / "beta-repo" / "specs"}


def _nothing_resolves(tmp_path: Path) -> dict[str, object]:
    plain = tmp_path / "not-a-workspace"
    plain.mkdir()
    return {"env": {}, "cwd": plain}


def _open_bug_linked_worktree_outside_repos(tmp_path: Path) -> dict[str, object]:
    """The open bug's exact repro: cwd is a linked worktree parked under
    ``.dadaia/tmp/`` that carries its OWN independent sentinel; the write target lives
    under the REAL outer workspace's ``repos/<slug>/specs/memory/``. Root must resolve
    to the OUTER workspace (the one that owns the target), not the inner one — proven
    below by first asserting the inner sentinel is genuinely a trap for a cwd-only walk.
    """
    outer = _mk_ws(tmp_path, slug="dadaia-workspace")
    nested = outer / ".dadaia" / "tmp" / "agent-x" / "worktree"
    nested_states = nested / ".dadaia" / "states"
    nested_states.mkdir(parents=True)
    (nested_states / "spec_contexts.json").write_text(
        json.dumps({"schema_version": "2", "contexts": []}), encoding="utf-8"
    )
    # Sanity: a cwd-only walk from `nested` really would land on the WRONG (inner) root.
    assert resolve_workspace_root(nested) == nested.resolve()

    target = outer / "repos" / "dadaia-workspace" / "specs" / "memory" / "atom.md"
    return {"target_path": target, "env": {}, "cwd": nested}


def _read_mode_from_session_record(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    sid = "sess-read-mode"
    _write_session(ws, sid, "proj", mode="READ")
    return {"env": {"CLAUDE_CODE_SESSION_ID": sid}, "cwd": ws / "repos" / "proj"}


def _dadaia_mode_env_overrides_session_record(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    sid = "sess-mode-override"
    _write_session(ws, sid, "proj", mode="IMPLEMENTATION")
    return {
        "env": {"CLAUDE_CODE_SESSION_ID": sid, "DADAIA_MODE": "READ"},
        "cwd": ws / "repos" / "proj",
    }


def _missing_mode_defaults_implementation(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    return {"env": {}, "cwd": ws / "repos" / "proj"}


def _release_phase_resolved(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    _write_release(ws / "repos" / "proj" / "specs", "0.5.1", "IMPLEMENTATION")
    return {"env": {}, "cwd": ws / "repos" / "proj"}


def _release_phase_none_when_ambiguous(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    specs_dir = ws / "repos" / "proj" / "specs"
    _write_release(specs_dir, "0.5.0", "CLOSURE")
    _write_release(specs_dir, "0.5.1", "DEFINITION")
    return {"env": {}, "cwd": ws / "repos" / "proj"}


def _release_phase_none_when_no_releases_dir(tmp_path: Path) -> dict[str, object]:
    ws = _mk_ws(tmp_path, slug="proj")
    return {"env": {}, "cwd": ws / "repos" / "proj"}


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "explicit_wins_over_target_env_and_session",
        _explicit_wins,
        lambda inv: inv.context_name == "explicit-ctx" and inv.rung == "explicit",
    ),
    Scenario(
        "rung0_target_path_wins_over_dadaia_context",
        _target_path_beats_env,
        lambda inv: inv.context_name == "x" and inv.rung == "target_path",
    ),
    Scenario(
        "rung0_target_path_maps_slug_to_name_via_registry",
        _target_path_maps_slug_to_name,
        lambda inv: (
            inv.context_name == "alpha-context"
            and inv.repo_slug == "beta-repo"
            and inv.rung == "target_path"
        ),
    ),
    Scenario(
        "rung0_target_outside_repo_falls_through_to_env",
        _target_path_outside_repo_falls_to_env,
        lambda inv: inv.context_name == "y" and inv.rung == "env",
    ),
    Scenario(
        "rung_env_dadaia_context_alone",
        _env_alone_resolves,
        lambda inv: inv.context_name == "proj" and inv.rung == "env",
    ),
    Scenario(
        "rung_env_wins_over_live_session_record",
        _env_wins_over_session,
        lambda inv: inv.context_name == "proj" and inv.rung == "env",
    ),
    Scenario(
        "rung_session_wins_over_cwd",
        _session_wins_over_cwd,
        lambda inv: inv.context_name == "proj" and inv.rung == "session",
    ),
    Scenario(
        "rung_session_stale_falls_through_to_cwd",
        _stale_session_falls_through_to_cwd,
        lambda inv: inv.context_name == "other" and inv.rung == "cwd",
    ),
    Scenario(
        "rung_session_deleted_context_guard_falls_through_to_cwd",
        _deleted_context_guard_falls_through,
        lambda inv: inv.context_name == "other" and inv.rung == "cwd",
    ),
    Scenario(
        "rung_cwd_alone_resolves",
        _cwd_alone_resolves,
        lambda inv: inv.context_name == "proj" and inv.rung == "cwd",
    ),
    Scenario(
        "rung_cwd_maps_slug_to_name_via_registry",
        _cwd_maps_slug_to_name,
        lambda inv: inv.context_name == "alpha-context" and inv.repo_slug == "beta-repo",
    ),
    Scenario(
        "nothing_resolves_missing_workspace",
        _nothing_resolves,
        lambda inv: (
            inv.workspace_root is None
            and inv.session_id is None
            and inv.context_name is None
            and inv.repo_slug is None
            and inv.specs_dir is None
            and inv.mode == "IMPLEMENTATION"
            and inv.release == "none"
            and inv.phase == ""
            and inv.rung == "none"
        ),
    ),
    Scenario(
        "open_bug_linked_worktree_outside_repos_root_resolves_from_target",
        _open_bug_linked_worktree_outside_repos,
        lambda inv: (
            inv.context_name == "dadaia-workspace"
            and inv.workspace_root is not None
            and inv.workspace_root.name != "worktree"
            and inv.specs_dir is not None
            and inv.specs_dir.is_dir()
        ),
    ),
    Scenario(
        "mode_read_from_session_record",
        _read_mode_from_session_record,
        lambda inv: inv.mode == "READ",
    ),
    Scenario(
        "mode_dadaia_mode_env_overrides_session_record",
        _dadaia_mode_env_overrides_session_record,
        lambda inv: inv.mode == "READ",
    ),
    Scenario(
        "mode_missing_defaults_to_implementation",
        _missing_mode_defaults_implementation,
        lambda inv: inv.mode == "IMPLEMENTATION",
    ),
    Scenario(
        "release_phase_resolved_from_release_json",
        _release_phase_resolved,
        lambda inv: inv.release == "0.5.1" and inv.phase == "IMPLEMENTATION",
    ),
    Scenario(
        "release_phase_none_when_two_release_dirs_are_ambiguous",
        _release_phase_none_when_ambiguous,
        lambda inv: inv.release == "none" and inv.phase == "",
    ),
    Scenario(
        "release_phase_none_when_no_releases_dir",
        _release_phase_none_when_no_releases_dir,
        lambda inv: inv.release == "none" and inv.phase == "",
    ),
)


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_resolve_scenarios(tmp_path: Path, scenario: Scenario) -> None:
    kwargs = scenario.build(tmp_path)
    inv = invocation.resolve(**kwargs)  # type: ignore[arg-type]
    assert scenario.check(inv), f"{scenario.name}: unexpected Invocation {inv!r}"


# --------------------------------------------------------------------------- session id precedence


@pytest.mark.parametrize(
    ("name", "env", "payload", "default", "expected"),
    [
        (
            "payload_sid_beats_inherited_claude_env",
            {"CLAUDE_CODE_SESSION_ID": "stale-inherited"},
            {"session_id": "live-payload"},
            None,
            "live-payload",
        ),
        (
            "payload_sid_beats_inherited_codex_env",
            {"CODEX_SESSION_ID": "stale-inherited"},
            {"session_id": "live-payload"},
            None,
            "live-payload",
        ),
        (
            "dadaia_override_stays_first",
            {"DADAIA_SESSION_ID": "explicit-override"},
            {"session_id": "live-payload"},
            None,
            "explicit-override",
        ),
        (
            "env_fallback_without_payload",
            {"CLAUDE_CODE_SESSION_ID": "harness-env"},
            {},
            None,
            "harness-env",
        ),
        (
            "stdin_field_when_no_env",
            {},
            {"session_id": "from-stdin"},
            None,
            "from-stdin",
        ),
        (
            "dadaia_override_beats_codex_and_stdin",
            {"CODEX_SESSION_ID": "codex-sid", "DADAIA_SESSION_ID": "explicit"},
            {"session_id": "x"},
            None,
            "explicit",
        ),
        (
            "default_when_nothing_resolves",
            {},
            {},
            "workspace",
            "workspace",
        ),
        (
            "codex_thread_id_resolves_when_no_codex_session_id",
            {"CODEX_THREAD_ID": "thread-abc123"},
            {},
            None,
            "thread-abc123",
        ),
        (
            "codex_session_id_preferred_over_codex_thread_id",
            {"CODEX_SESSION_ID": "codex-sess-1", "CODEX_THREAD_ID": "thread-abc123"},
            {},
            None,
            "codex-sess-1",
        ),
    ],
)
def test_resolve_session_id_precedence(
    name: str,
    env: dict[str, str],
    payload: dict[str, object],
    default: str | None,
    expected: str,
) -> None:
    kwargs: dict[str, object] = {"default": default} if default is not None else {}
    assert invocation.resolve_session_id(payload, env, **kwargs) == expected  # type: ignore[arg-type]


# --------------------------------------------------------------------------- context_name_for_repo_slug


def test_context_name_for_repo_slug_resolves_matching_entry(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path, slug="beta-repo", name="alpha-context")
    assert invocation.context_name_for_repo_slug(ws, "beta-repo") == "alpha-context"


def test_context_name_for_repo_slug_matches_an_associated_repo(tmp_path: Path) -> None:
    """A16.4: a slug that matches an ASSOCIATED repo resolves the OWNING context's
    name, never a second context of its own."""
    ws = _mk_ws(tmp_path, slug="main-repo", name="proj")
    _register_context(ws, slug="other", associated=["assoc-repo"])
    assert invocation.context_name_for_repo_slug(ws, "assoc-repo") == "other"


def test_context_name_for_repo_slug_falls_back_to_slug_when_unmatched(tmp_path: Path) -> None:
    ws = _mk_ws(tmp_path, slug="proj")
    assert invocation.context_name_for_repo_slug(ws, "no-such-slug") == "no-such-slug"


def test_context_name_for_repo_slug_falls_back_to_slug_when_registry_missing(
    tmp_path: Path,
) -> None:
    assert invocation.context_name_for_repo_slug(tmp_path, "proj") == "proj"


def test_context_name_for_repo_slug_falls_back_to_slug_when_registry_corrupt(
    tmp_path: Path,
) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text("{not json", encoding="utf-8")
    assert invocation.context_name_for_repo_slug(tmp_path, "proj") == "proj"


def test_context_name_for_repo_slug_accepts_legacy_repo_field(tmp_path: Path) -> None:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {"schema_version": "2", "contexts": [{"name": "alpha-context", "repo": "beta-repo"}]}
        ),
        encoding="utf-8",
    )
    assert invocation.context_name_for_repo_slug(tmp_path, "beta-repo") == "alpha-context"


# --------------------------------------------------------------------------- resolve_specs_dir (CLI seam)


@pytest.fixture(autouse=True)
def _isolate_process_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """``resolve_specs_dir``/``resolve_context_specs_dir`` read ``os.environ``/``Path.cwd()``
    directly (the CLI-ambient seam) — scrub the ambient channel so these tests are
    hermetic under xdist (mirrors the pre-K1 fixture's own rationale)."""
    scrub_context_resolution_env(monkeypatch)


def test_resolve_specs_dir_explicit_wins_even_without_a_bound_context(tmp_path: Path) -> None:
    target = tmp_path / "explicit-specs"
    target.mkdir()
    assert invocation.resolve_specs_dir(str(target)) == target.resolve()


def test_resolve_specs_dir_refuses_a_symlinked_explicit_root(tmp_path: Path) -> None:
    real = tmp_path / "real-specs"
    real.mkdir()
    link = tmp_path / "linked-specs"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(typer.BadParameter, match="symlink"):
        invocation.resolve_specs_dir(str(link))


def test_resolve_specs_dir_raises_when_nothing_resolves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plain = tmp_path / "not-a-workspace"
    plain.mkdir()
    monkeypatch.chdir(plain)
    with pytest.raises(typer.BadParameter, match="Could not resolve specs_dir"):
        invocation.resolve_specs_dir(None)


def test_resolve_specs_dir_resolves_from_cwd_inside_a_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _mk_ws(tmp_path, slug="proj")
    monkeypatch.chdir(ws / "repos" / "proj")
    assert invocation.resolve_specs_dir(None) == (ws / "repos" / "proj" / "specs").resolve()


class TestAliveContextSlugs:
    """F008 (20260830 audit): the registry read family has ONE home — invocation.
    ctx_inject's private ``_alive_context_names`` parser is deleted; the hook imports
    :func:`invocation.alive_context_slugs`. Intent: contract; size: unit."""

    def test_alive_filter_and_slug_preference(self, tmp_path: Path) -> None:
        states = tmp_path / ".dadaia" / "states"
        states.mkdir(parents=True)
        (states / "spec_contexts.json").write_text(
            json.dumps(
                {
                    "schema_version": "2",
                    "contexts": [
                        {"name": "pretty", "repo_slug": "actual-dir", "state": "alive"},
                        {"name": "gone", "repo_slug": "gone-dir", "state": "dead"},
                        {"name": "bare", "state": "ALIVE"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        assert invocation.alive_context_slugs(tmp_path) == ["actual-dir", "bare"]

    def test_fail_soft_on_missing_or_malformed(self, tmp_path: Path) -> None:
        assert invocation.alive_context_slugs(tmp_path) == []
        states = tmp_path / ".dadaia" / "states"
        states.mkdir(parents=True)
        (states / "spec_contexts.json").write_text("{not json", encoding="utf-8")
        assert invocation.alive_context_slugs(tmp_path) == []

    def test_hook_has_no_private_registry_parser(self) -> None:
        from dadaia_workspace.hooks import ctx_inject

        assert not hasattr(ctx_inject, "_alive_context_names")
