"""Intent: CONTRACT — sa-context-dead-removes-repos-outside-the-reaper (0.5.0 WP-03, AC1.2).

`context dead` refuses a repo whose loss is unrecoverable — a local branch carrying a
commit neither origin nor HEAD holds (sa-context-dead-removes-repos-outside-the-reaper#C3), a linked worktree registered by the repo or
nested inside it (sa-context-dead-removes-repos-outside-the-reaper#C2) — over every repo of the set (sa-context-dead-removes-repos-outside-the-reaper#C4), touching nothing and leaving
the record ALIVE (sa-context-dead-removes-repos-outside-the-reaper#C7); otherwise it HOLDS each repo under `.dadaia/reaped/` (sa-context-dead-removes-repos-outside-the-reaper#C1).
Size: MEDIUM — real git and a bare origin in tmp_path (the question is a git question).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.container import scan_publish_candidates  # noqa: E402
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    DeadUnpushedCommitsError,
    SpecContextService,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.stores import context_store

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True)


def _published(tmp_path: Path, repo: Path) -> Path:
    bare = tmp_path / f"{repo.name}.git"
    _git("init", "--bare", "-b", "main", str(bare), cwd=tmp_path)
    repo.parent.mkdir(parents=True, exist_ok=True)
    _git("clone", str(bare), str(repo), cwd=tmp_path)
    _git("config", "user.email", "t@example.com", cwd=repo)
    _git("config", "user.name", "T", cwd=repo)
    (repo / "README.md").write_text("init\n")
    (repo / ".gitignore").write_text(".worktrees/\n")
    _git("add", "README.md", ".gitignore", cwd=repo)
    _git("commit", "-m", "init", cwd=repo)
    _git("push", "-u", "origin", "HEAD", cwd=repo)
    return bare


def _alive(
    tmp_path: Path, *, lib: bool = False
) -> tuple[SpecContextService, JsonContextStore, Path]:
    ws = tmp_path / "ws"
    repo = ws / "repos" / "main"
    bare = _published(tmp_path, repo)
    assoc = (AssociatedRepo("lib", str(_published(tmp_path, ws / "repos" / "lib"))),)
    store = context_store(ws / ".dadaia" / "states")
    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.ALIVE,
            repo_slug="main",
            repo_url=str(bare),
            created_at="2026-09-27T00:00:00+00:00",
            associated_repos=assoc if lib else (),
        )
    )
    service = SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=ws,
        install_hooks=lambda _repo: None,
        secret_scan=scan_publish_candidates,
    )
    return service, store, repo


def _side_branch(repo: Path) -> None:
    _git("switch", "-c", "topic", cwd=repo)
    (repo / "t.txt").write_text("work\n")
    _git("add", "t.txt", cwd=repo)
    _git("commit", "-m", "topic work", cwd=repo)
    _git("switch", "main", cwd=repo)


@pytest.mark.parametrize("offender", ["main", "lib"])
def test_c3_c4_an_unpushed_side_branch_in_any_repo_is_refused(
    tmp_path: Path, offender: str
) -> None:
    service, store, repo = _alive(tmp_path, lib=True)
    _side_branch(repo.parent / offender)

    with pytest.raises(DeadUnpushedCommitsError, match=r"fix: git -C \S+ push -u origin topic"):
        service.dead("proj")

    assert (repo / ".git").is_dir() and (repo.parent / "lib" / ".git").is_dir()
    assert not (tmp_path / "ws" / ".dadaia" / "reaped").exists()
    assert store.get("proj").state is ContextState.ALIVE  # type: ignore[union-attr]


def test_c2_a_registered_linked_worktree_is_refused(tmp_path: Path) -> None:
    service, store, repo = _alive(tmp_path)
    outside = tmp_path / "wt"
    _git("worktree", "add", "-b", "wt", str(outside), cwd=repo)
    _git("push", "-u", "origin", "wt", cwd=repo)
    (outside / "uncommitted.txt").write_text("keep\n")

    with pytest.raises(DeadUnpushedCommitsError, match=r"fix: git -C \S+ worktree remove "):
        service.dead("proj")

    assert (outside / "uncommitted.txt").read_text() == "keep\n"
    assert store.get("proj").state is ContextState.ALIVE  # type: ignore[union-attr]


def test_c3_a_clean_pushed_repo_is_held_never_deleted(tmp_path: Path) -> None:
    service, store, repo = _alive(tmp_path)
    ws = repo.parents[1]

    service.dead("proj")

    held = list((ws / ".dadaia" / "reaped").glob("*/repos/main/README.md"))
    assert [p.read_text() for p in held] == ["init\n"]
    assert not repo.exists()
    assert store.get("proj").state is ContextState.DEAD  # type: ignore[union-attr]


def test_c2_a_nested_foreign_worktree_is_refused_and_its_fix_clears_it(tmp_path: Path) -> None:
    """A gitignored linked worktree of ANOTHER repo nested in the checkout: the hold
    would skip it, so dead refuses up front instead of recording DEAD with the repo on
    disk; the fix line (verbatim, <keep-dir> filled) clears the refusal."""
    service, store, repo = _alive(tmp_path)
    other = tmp_path / "other"
    _published(tmp_path, other)
    nested = repo / ".worktrees" / "wt"
    _git("worktree", "add", "-b", "wt", str(nested), cwd=other)
    (nested / "uncommitted.txt").write_text("keep\n")

    with pytest.raises(DeadUnpushedCommitsError) as refused:
        service.dead("proj")

    assert (nested / "uncommitted.txt").read_text() == "keep\n"
    assert store.get("proj").state is ContextState.ALIVE  # type: ignore[union-attr]
    fix = str(refused.value).rsplit("fix: ", 1)[1].replace("<keep-dir>", str(tmp_path / "kept"))
    subprocess.run(fix, shell=True, check=True, capture_output=True)  # noqa: S602
    service.dead("proj")
    assert (tmp_path / "kept" / "uncommitted.txt").read_text() == "keep\n"
    assert store.get("proj").state is ContextState.DEAD  # type: ignore[union-attr]
