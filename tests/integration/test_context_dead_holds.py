"""Intent: CONTRACT — `context alive`/`context dead` over the whole repo set (main + associated).

- sa-context-dead-removes-repos-outside-the-reaper#C3 /
  sa-context-dead-removes-repos-outside-the-reaper#C4: a local branch carrying a commit origin lacks,
  in ANY repo of the set, refuses dead; sa-context-dead-removes-repos-outside-the-reaper#C2: a linked
  worktree registered by the repo or nested inside it refuses dead; AC1.10: any `wt/*`
  refuses dead with the owner's `worktree.py merge` fix, checked out or orphan, and
  rows the owner cannot read refuse with its fix; AC2.11: a refused hold refuses dead;
  sa-context-dead-removes-repos-outside-the-reaper#C7: a refusal touches nothing, the record stays ALIVE;
  sa-context-dead-removes-repos-outside-the-reaper#C1: otherwise each repo is HELD under `.dadaia/reaped/`.
- A16.1 (FR16 v0.4.4): alive clones the whole set, idempotently. A16.2: an untracked file
  or a remote-less repo anywhere in the set refuses dead before any repo acts.
- context-dead-destroys-associated-repo-without-url: dead back-fills each repo's URL from
  origin, refuses a repo it could never clone back; alive refuses a URL-less missing repo
  with a runnable fix line.
- context-dead-pushes-an-unborn-clone: an unborn clone (empty or holding files) is held,
  never pushed (WP-03 undid 934377e8's refusal).
- F-5 / AC-R7-01: a gitignored file is not untracked-for-review.
The refusal fix lines on the main repo are the refusal harness's Cases
(`test_refusal_fix_lines_clear_their_refusal.py`: untracked, secret_untracked, no_origin,
unpushed_side_branch, commits_no_remote).
Size: MEDIUM — real git and bare origins in tmp_path (the question is a git question).
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import replace
from functools import partial
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.container import scan_publish_candidates  # noqa: E402
from dadaia_workspace.core.exceptions import ContextStateError, RepoUrlMissingError  # noqa: E402
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import (  # noqa: E402
    DeadReviewRequiredError,
    DeadUnpushedCommitsError,
    SpecContextService,
)
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.stores import context_store, workspace_cli
from tests.helpers.privacy_fixtures import aws_key_shape

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
    (repo / ".gitignore").write_text(".worktrees/\nignored.txt\n")
    _git("add", "README.md", ".gitignore", cwd=repo)
    _git("commit", "-m", "init", cwd=repo)
    _git("push", "-u", "origin", "HEAD", cwd=repo)
    return bare


def _alive(
    tmp_path: Path, lib_url: str | None = None
) -> tuple[SpecContextService, JsonContextStore, Path]:
    """ALIVE `proj`: main repo `repos/main` + associated `repos/lib`, both published."""
    ws = tmp_path / "ws"
    repo = ws / "repos" / "main"
    bare = _published(tmp_path, repo)
    lib = _published(tmp_path, ws / "repos" / "lib")
    store = context_store(ws / ".dadaia" / "states")
    flow = {"work": "feature/"}  # the stub CLI names the set's gitflow to worktree.py list
    workspace_cli(ws, {"main_repo": "main", "associated_repos": [{"slug": "lib"}], "gitflow": flow})
    store.save(
        SpecContextProject(
            "proj", ContextState.ALIVE, "main", str(bare), "2026-09-27T00:00:00+00:00",
            associated_repos=(AssociatedRepo("lib", str(lib) if lib_url is None else lib_url),),
        )
    )  # fmt: skip
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


def _worktree(repo: Path) -> None:
    outside = repo.parents[2] / "wt"
    _git("worktree", "add", "-b", "wt", str(outside), cwd=repo)
    _git("push", "-u", "origin", "wt", cwd=repo)
    (outside / "uncommitted.txt").write_text("keep\n")


def _wt(repo: Path, *, checked_out: bool) -> None:
    """An UNPUSHED `wt/0.5.0a-impl` carrying a commit — `dadaia:`-locked in its canonical
    tree, or an orphan with none."""
    tree = repo.parents[1] / "worktrees" / repo.name / "0.5.0a-impl"
    _git("branch", "feature/0.5.0", cwd=repo)  # the work branch it is ahead of
    _git("worktree", "add", "-b", "wt/0.5.0a-impl", str(tree), cwd=repo)
    (tree / "w.txt").write_text("w\n")
    _git("add", "w.txt", cwd=tree)
    _git("-c", "user.name=T", "-c", "user.email=t@example.com", "commit", "-qm", "w", cwd=tree)
    if checked_out:
        _git("worktree", "lock", "--reason", "dadaia: impl", str(tree), cwd=repo)
    else:
        _git("worktree", "remove", str(tree), cwd=repo)


def _no_remote(repo: Path) -> None:
    _git("remote", "remove", "origin", cwd=repo)
    (repo / "notes.md").write_text("local only\n")
    _git("add", "notes.md", cwd=repo)
    _git("commit", "-m", "local only", cwd=repo)


def _url_less(repo: Path) -> None:
    shutil.rmtree(repo)
    _git("init", str(repo), cwd=repo.parent)


def _repos_outside(repo: Path) -> None:
    """`repos/` resolves outside the workspace: preflight passes, the hold refuses."""
    outside = repo.parents[2] / "outside"
    repo.parent.rename(outside)
    repo.parent.symlink_to(outside)


_REFUSALS = [
    pytest.param("main", _side_branch, DeadUnpushedCommitsError, r"fix: git -C \S+ -c \S+ push origin topic:refs/tags/archive/topic/[0-9a-f]{7}$", id="C3-side-branch-main"),
    pytest.param("lib", _side_branch, DeadUnpushedCommitsError, r"fix: git -C \S+ -c \S+ push origin topic:refs/tags/archive/topic/[0-9a-f]{7}$", id="C4-side-branch-lib"),
    pytest.param("main", _worktree, DeadUnpushedCommitsError, r"fix: git -C \S+ worktree remove ", id="C2-registered-worktree"),
    pytest.param("lib", partial(_wt, checked_out=True), DeadUnpushedCommitsError, r"fix: \S+ \S+worktree\.py merge \S+/worktrees/lib/0\.5\.0a-impl$", id="AC1.10-open-wt-worktree"),
    pytest.param("main", partial(_wt, checked_out=False), DeadUnpushedCommitsError, r"fix: \S+ \S+worktree\.py merge \S+/worktrees/main/0\.5\.0a-impl$", id="AC1.10-unpushed-orphan-wt"),
    pytest.param("main", lambda r: (r.parents[1] / ".dadaia/.venv/bin/dadaia").unlink(), DeadUnpushedCommitsError, r"no workspace CLI[\s\S]*fix: uvx dadaia-workspace init \S+/ws$", id="AC1.10-rows-unreadable-fails-closed"),
    pytest.param("lib", lambda r: (r / "leftover.txt").write_text("x\n"), DeadReviewRequiredError, r"lib[\s\S]*leftover\.txt", id="A16.2-untracked-in-lib"),
    pytest.param("lib", _no_remote, DeadUnpushedCommitsError, "lib", id="A16.2-local-commits-no-remote-in-lib"),
    pytest.param("main", _repos_outside, ContextStateError, r"skipped 'repos/main' \(outside the workspace\)$", id="AC2.11-hold-refused"),
    pytest.param("lib", _url_less, RepoUrlMissingError, r"fix: Operator action: add the clone URL of \S+/repos/lib as its origin remote", id="url-less-never-clone-back"),
]  # fmt: skip


@pytest.mark.parametrize(("offender", "plant", "error", "match"), _REFUSALS)
def test_dead_refuses_an_unrecoverable_repo_anywhere_in_the_set_and_touches_nothing(
    tmp_path: Path,
    offender: str,
    plant: Callable[[Path], object],
    error: type[Exception],
    match: str,
) -> None:
    """#C7: the refusal names the repo's fix; every repo stays, nothing is held, ALIVE."""
    service, store, repo = _alive(tmp_path, lib_url="" if plant is _url_less else None)
    plant(repo.parent / offender)

    with pytest.raises(error, match=match):
        service.dead("proj", commit=plant is _url_less)

    assert (repo / ".git").is_dir() and (repo.parent / "lib" / ".git").is_dir()
    assert not (tmp_path / "ws" / ".dadaia" / "reaped").exists()
    assert store.get("proj").state is ContextState.ALIVE  # type: ignore[union-attr]


def _unborn(repo: Path, *files: str) -> None:
    shutil.rmtree(repo)
    _git("init", str(repo), cwd=repo.parent)
    _git("remote", "add", "origin", str(repo.parents[2] / "vanished.git"), cwd=repo)
    for name in files:
        (repo / name).write_text("scaffold\n")


_HOLDS = [
    pytest.param(lambda r: None, "README.md", "init\n", False, id="C1-clean-set"),
    pytest.param(lambda r: (r / "ignored.txt").write_text(f"k={aws_key_shape()}\n"), "ignored.txt", None, False, id="gitignored-is-not-untracked"),
    pytest.param(_unborn, ".git/HEAD", None, False, id="unborn-empty-clone-no-push"),
    pytest.param(lambda r: _unborn(r, "AGENTS.md"), "AGENTS.md", "scaffold\n", True, id="unborn-clone-holding-files"),
]  # fmt: skip


@pytest.mark.parametrize(("plant", "held", "content", "commit"), _HOLDS)
def test_dead_holds_every_repo_of_the_set_under_reaped(
    tmp_path: Path, plant: Callable[[Path], object], held: str, content: str | None, commit: bool
) -> None:
    """#C1: each repo leaves `repos/` and is held byte-intact; the record turns DEAD."""
    service, store, repo = _alive(tmp_path)
    plant(repo.parent / "lib")

    service.dead("proj", commit=commit)

    reaped = tmp_path / "ws" / ".dadaia" / "reaped"
    assert [p.read_text() for p in reaped.glob("*/repos/main/README.md")] == ["init\n"]
    kept = list(reaped.glob(f"*/repos/lib/{held}"))
    assert len(kept) == 1 and (content is None or kept[0].read_text() == content)
    assert not repo.exists() and not (repo.parent / "lib").exists()
    assert store.get("proj").state is ContextState.DEAD  # type: ignore[union-attr]


def test_c2_a_nested_foreign_worktree_is_refused_and_its_fix_clears_it(tmp_path: Path) -> None:
    """A gitignored linked worktree of ANOTHER repo nested in the checkout: the hold
    would skip it, so dead refuses up front instead of recording DEAD with the repo on
    disk; the fix line (its command, the kept directory appended) clears the refusal."""
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
    fix = str(refused.value).rsplit("fix: ", 1)[1]
    move = f"{fix.split('`')[1]} {tmp_path / 'kept'}"
    # Git runs from the common git dir, never inside the tree it moves: Windows refuses
    # to rename a process's cwd (sa-context-dead-removes-repos-outside-the-reaper).
    assert Path(move.split()[2]).samefile(other / ".git"), fix
    subprocess.run(move, shell=True, check=True, capture_output=True)  # noqa: S602
    service.dead("proj")
    assert (tmp_path / "kept" / "uncommitted.txt").read_text() == "keep\n"
    assert store.get("proj").state is ContextState.DEAD  # type: ignore[union-attr]


def test_alive_dead_alive_keeps_every_repo_obtainable(tmp_path: Path) -> None:
    """A16.1 + context-dead-destroys-associated-repo-without-url: a lib registered with no
    URL gets origin's URL back-filled by dead; alive then re-clones the whole set, and a
    second alive (clone into a populated dir would fail) is a no-op."""
    service, store, repo = _alive(tmp_path, lib_url="")

    dead = service.dead("proj", commit=True)
    service.alive("proj")
    again = service.alive("proj")

    assert dead.associated_repos == (AssociatedRepo("lib", str(tmp_path / "lib.git")),)
    assert again.state is ContextState.ALIVE and again.associated_repos == dead.associated_repos
    assert (repo / "README.md").is_file() and (repo.parent / "lib" / "README.md").is_file()


def test_alive_refuses_a_legacy_url_less_missing_repo_with_a_fix_line(tmp_path: Path) -> None:
    service, store, repo = _alive(tmp_path, lib_url="")
    service.dead("proj")
    store.update(replace(store.get("proj"), associated_repos=(AssociatedRepo("lib", ""),)))  # type: ignore[type-var]

    with pytest.raises(RepoUrlMissingError) as refused:
        service.alive("proj")

    # the operator's clone, which alive then adopts, its origin back-filled
    clone = f"Operator action: clone the 'lib' repository into {repo.parent / 'lib'}"
    assert str(refused.value).endswith(f"fix: {clone}")
    assert store.get("proj").state == ContextState.DEAD  # type: ignore[union-attr]
