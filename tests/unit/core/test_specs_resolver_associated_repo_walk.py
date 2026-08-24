"""FR16 (v0.4.4, T-044-27) A16.4 — a resolution walk from inside an associated repo
resolves the CONTEXT, never a second context of its own.

Intent: CONTRACT — A16.4.

``core.specs_resolver.context_name_for_repo_slug`` is the registry inverse
``resolve_context``'s rung 0/rung 3 use to map a ``repos/<slug>/`` directory to the
owning context's NAME. Before this task it matched only a context's MAIN
``repo_slug``; an associated repo's slug fell through to the "unmatched" branch, which
returns the slug itself as if it were a context name — the associated repo would then
be (mis)treated as its own context, and downstream ``specs_dir`` resolution would land
on the associated repo's OWN ``specs/`` (exactly what A16.3/FR19/G13 forbid). This
suite pins the fix: the SAME inverse lookup now also matches ``associated_repos``,
never a second resolution path (A15.3).

Purely additive: this file does not modify ``test_specs_resolver_resolve_context.py``
(the pinned FR1 rung-ladder suite) — it reuses the same fixture conventions locally.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core import specs_resolver
from tests.fixtures.harness_env import CONTEXT_RESOLUTION_ENV_VARS, scrub_context_resolution_env

_ENV_VARS_TO_CLEAR = CONTEXT_RESOLUTION_ENV_VARS


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Neutralize every rung-0/1/2 env var — see the sibling FR1 suite for the full
    rationale (ambient WORKSPACE_ROOT / session-id leak across xdist workers)."""
    scrub_context_resolution_env(monkeypatch)


def _mk_ws_with_associated_repo(
    tmp_path: Path,
    *,
    main_slug: str = "main-repo",
    main_name: str = "proj",
    assoc_slug: str = "assoc-repo",
) -> Path:
    """A minimal initialized workspace: one registered context with ONE associated repo.

    Mirrors the on-disk registry shape ``infrastructure.json_context_store._to_dict``
    writes (``associated_repos: [{"slug": ..., "url": ...}]``) — the exact JSON this
    fix reads.
    """
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "3",
                "contexts": [
                    {
                        "name": main_name,
                        "repo_slug": main_slug,
                        "state": "alive",
                        "associated_repos": [
                            {"slug": assoc_slug, "url": "https://example.invalid/assoc.git"}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "repos" / main_slug / "specs").mkdir(parents=True)
    (tmp_path / "repos" / assoc_slug).mkdir(parents=True)
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    return tmp_path


def test_context_name_for_repo_slug_matches_an_associated_repo_slug(tmp_path: Path) -> None:
    ws = _mk_ws_with_associated_repo(tmp_path, main_slug="main-repo", main_name="proj")

    assert specs_resolver.context_name_for_repo_slug(ws, "assoc-repo") == "proj"
    # The main repo's own slug still resolves too — additive, not a replacement.
    assert specs_resolver.context_name_for_repo_slug(ws, "main-repo") == "proj"


def test_context_name_for_repo_slug_still_falls_back_when_no_match_at_all(
    tmp_path: Path,
) -> None:
    ws = _mk_ws_with_associated_repo(tmp_path)

    assert specs_resolver.context_name_for_repo_slug(ws, "no-such-slug") == "no-such-slug"


def test_context_name_for_repo_slug_tolerates_missing_associated_repos_key(
    tmp_path: Path,
) -> None:
    """A v2 registry entry (pre-FR15, no ``associated_repos`` key at all) must not
    crash the lookup — it simply never matches an associated slug."""
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {"schema_version": "2", "contexts": [{"name": "proj", "repo_slug": "main-repo"}]}
        ),
        encoding="utf-8",
    )

    assert specs_resolver.context_name_for_repo_slug(tmp_path, "main-repo") == "proj"
    assert specs_resolver.context_name_for_repo_slug(tmp_path, "ghost-slug") == "ghost-slug"


def test_resolve_context_walk_from_inside_associated_repo_resolves_the_owning_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A16.4: rung 3 (cwd-based walk) from inside ``repos/<associated-slug>/`` resolves
    the context name, never the associated repo's own slug as a second context."""
    ws = _mk_ws_with_associated_repo(tmp_path, main_slug="main-repo", main_name="proj")
    monkeypatch.chdir(ws / "repos" / "assoc-repo")

    assert specs_resolver.resolve_context() == "proj"


def test_resolve_context_target_path_inside_associated_repo_resolves_the_owning_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A16.4: rung 0 (explicit write TARGET) under ``repos/<associated-slug>/`` also
    resolves the owning context — the same inverse lookup serves both rungs."""
    ws = _mk_ws_with_associated_repo(tmp_path, main_slug="main-repo", main_name="proj")
    monkeypatch.chdir(ws)
    target = ws / "repos" / "assoc-repo" / "some-file.txt"

    assert specs_resolver.resolve_context(target_path=target) == "proj"


def test_resolve_specs_dir_from_associated_repo_resolves_the_main_repos_specs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A16.3/A16.4 end to end: once the context name resolves correctly, the specs/
    dir resolution (the gate/memory consumer) lands on the MAIN repo's specs/, never
    the associated repo's own (nonexistent, by construction) specs/ tree."""
    ws = _mk_ws_with_associated_repo(tmp_path, main_slug="main-repo", main_name="proj")
    monkeypatch.chdir(ws / "repos" / "assoc-repo")

    resolved = specs_resolver.resolve_specs_dir(None)

    assert resolved == (ws / "repos" / "main-repo" / "specs").resolve()
