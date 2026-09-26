"""FR16 (v0.4.4, T-044-27) — ALIVE/DEAD covers every repo in the set.

Intent: CONTRACT — A16.1, A16.2 (A16.3's clean-clone half: test_context_alive_writes_nothing.py).

Drives the REAL ``GitSubprocessClient`` against real git repos + bare remotes in
``tmp_path`` (never real network, never a real venv), mirroring the existing
``test_dead_review_gate.py`` conventions.
alive()/dead() now iterate ``SpecContextProject.all_repos()`` — main repo first, then
every associated repo in order (the one accessor, A15.3) — this suite proves that loop
end to end: real clones, real untracked-file detection, real commit/push, real rmtree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.invocation import repo_owner

pytest.importorskip("fcntl")

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
from tests.fakes import FakeContextStore  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _run(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, capture_output=True, check=True)


def _bare_remote(parent: Path, name: str) -> Path:
    bare = parent / name
    bare.mkdir(parents=True)
    _run(["git", "init", "--bare", str(bare)])
    return bare


def _clone_with_initial_commit(
    remote: Path, dest: Path, extra: dict[str, str] | None = None
) -> None:
    _run(["git", "clone", str(remote), str(dest)])
    _run(["git", "config", "user.email", "test@example.com"], cwd=dest)
    _run(["git", "config", "user.name", "Test"], cwd=dest)
    (dest / "README.md").write_text("init\n")
    for rel, content in (extra or {}).items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _run(["git", "add", "-A"], cwd=dest)
    _run(["git", "commit", "-m", "init"], cwd=dest)
    _run(["git", "push", "-u", "origin", "HEAD"], cwd=dest)


def _commit_count(path: Path) -> int:
    out = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"], cwd=path, capture_output=True, text=True, check=True
    )
    return int(out.stdout.strip())


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "repos").mkdir(parents=True)
    return root


def _make_service(workspace_root: Path) -> tuple[SpecContextService, FakeContextStore]:
    store = FakeContextStore()
    service = SpecContextService(
        repo_owner=repo_owner,
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
        install_hooks=lambda _repo: None,
    )
    return service, store


# ------------------------------------------------------------------ A16.1


def test_alive_clones_main_and_associated_repos_idempotently(
    tmp_path: Path, workspace_root: Path
) -> None:
    """A16.1: N=2 associated repos leaves N+1=3 repos on disk; re-running is idempotent.

    A real ``git clone`` into an already-populated destination fails — if the loop
    re-cloned anything already on disk, the second ``alive()`` call would raise.
    """
    main_remote = _bare_remote(tmp_path, "main-remote.git")
    assoc1_remote = _bare_remote(tmp_path, "assoc1-remote.git")
    assoc2_remote = _bare_remote(tmp_path, "assoc2-remote.git")
    _clone_with_initial_commit(main_remote, tmp_path / "seed-main")
    _clone_with_initial_commit(assoc1_remote, tmp_path / "seed-assoc1")
    _clone_with_initial_commit(assoc2_remote, tmp_path / "seed-assoc2")

    service, store = _make_service(workspace_root)
    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.DEAD,
            repo_slug="main-repo",
            repo_url=str(main_remote),
            created_at="2026-08-23T00:00:00+00:00",
            associated_repos=(
                AssociatedRepo(slug="assoc1-repo", url=str(assoc1_remote)),
                AssociatedRepo(slug="assoc2-repo", url=str(assoc2_remote)),
            ),
        )
    )

    main_path = workspace_root / "repos" / "main-repo"
    assoc1_path = workspace_root / "repos" / "assoc1-repo"
    assoc2_path = workspace_root / "repos" / "assoc2-repo"

    ctx = service.alive("proj")

    assert ctx.state == ContextState.ALIVE
    assert main_path.exists() and assoc1_path.exists() and assoc2_path.exists()
    assert ctx.associated_repos == (
        AssociatedRepo(slug="assoc1-repo", url=str(assoc1_remote)),
        AssociatedRepo(slug="assoc2-repo", url=str(assoc2_remote)),
    )

    # Re-run: idempotent. If the loop tried to re-clone any of these, `git clone`
    # into a non-empty destination raises and this call would fail.
    ctx2 = service.alive("proj")
    assert ctx2.state == ContextState.ALIVE
    assert main_path.exists() and assoc1_path.exists() and assoc2_path.exists()
    assert ctx2.associated_repos == ctx.associated_repos


# ------------------------------------------------------------------ A16.3


# ------------------------------------------------------------------ A16.2


def test_dead_refuses_on_untracked_file_in_associated_repo_naming_it_no_partial_dead(
    tmp_path: Path, workspace_root: Path
) -> None:
    """A16.2: dead() refuses when an associated repo has an unreviewed untracked
    file, naming it, and touches NOTHING in the set — checked before any repo acts."""
    main_remote = _bare_remote(tmp_path, "main-remote.git")
    assoc1_remote = _bare_remote(tmp_path, "assoc1-remote.git")
    assoc2_remote = _bare_remote(tmp_path, "assoc2-remote.git")
    _clone_with_initial_commit(main_remote, tmp_path / "seed-main")
    _clone_with_initial_commit(assoc1_remote, tmp_path / "seed-assoc1")
    _clone_with_initial_commit(assoc2_remote, tmp_path / "seed-assoc2")

    service, store = _make_service(workspace_root)
    main_path = workspace_root / "repos" / "main-repo"
    assoc1_path = workspace_root / "repos" / "assoc1-repo"
    assoc2_path = workspace_root / "repos" / "assoc2-repo"
    _run(["git", "clone", str(main_remote), str(main_path)])
    _run(["git", "clone", str(assoc1_remote), str(assoc1_path)])
    _run(["git", "clone", str(assoc2_remote), str(assoc2_path)])
    (assoc2_path / "leftover.txt").write_text("operator forgot to gitignore this\n")

    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.ALIVE,
            repo_slug="main-repo",
            repo_url=str(main_remote),
            created_at="2026-08-23T00:00:00+00:00",
            alive_since="2026-08-23T00:00:00+00:00",
            associated_repos=(
                AssociatedRepo(slug="assoc1-repo", url=str(assoc1_remote)),
                AssociatedRepo(slug="assoc2-repo", url=str(assoc2_remote)),
            ),
        )
    )

    with pytest.raises(DeadReviewRequiredError) as exc:
        service.dead("proj")

    assert "assoc2-repo" in str(exc.value)
    assert "leftover.txt" in str(exc.value)
    # No partial dead: every repo in the set is untouched, context still ALIVE.
    assert main_path.exists() and assoc1_path.exists() and assoc2_path.exists()
    assert (assoc2_path / "leftover.txt").exists()
    assert store.get("proj") is not None
    assert store.get("proj").state == ContextState.ALIVE  # type: ignore[union-attr]
    for remote in (main_remote, assoc1_remote, assoc2_remote):
        log = subprocess.run(
            ["git", "log", "--oneline"], cwd=remote, capture_output=True, text=True
        )
        assert "auto-sync before dead" not in log.stdout


def test_dead_refuses_on_associated_repo_with_local_commits_and_no_remote(
    tmp_path: Path, workspace_root: Path
) -> None:
    """A16.2 (the 'unpushed' trigger): an associated repo with local-only commits and
    NO remote at all refuses dead() with DeadUnpushedCommitsError, naming it, and
    leaves the whole set (including the otherwise-clean main repo) untouched."""
    main_remote = _bare_remote(tmp_path, "main-remote.git")
    _clone_with_initial_commit(main_remote, tmp_path / "seed-main")

    service, store = _make_service(workspace_root)
    main_path = workspace_root / "repos" / "main-repo"
    _run(["git", "clone", str(main_remote), str(main_path)])

    orphan_path = workspace_root / "repos" / "orphan-repo"
    orphan_path.mkdir(parents=True)
    _run(["git", "init"], orphan_path)
    _run(["git", "config", "user.email", "test@example.com"], orphan_path)
    _run(["git", "config", "user.name", "Test"], orphan_path)
    (orphan_path / "notes.md").write_text("local-only work, never pushed anywhere\n")
    _run(["git", "add", "-A"], orphan_path)
    _run(["git", "commit", "-m", "local only"], orphan_path)

    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.ALIVE,
            repo_slug="main-repo",
            repo_url=str(main_remote),
            created_at="2026-08-23T00:00:00+00:00",
            alive_since="2026-08-23T00:00:00+00:00",
            associated_repos=(
                AssociatedRepo(slug="orphan-repo", url="https://example.invalid/orphan.git"),
            ),
        )
    )

    with pytest.raises(DeadUnpushedCommitsError) as exc:
        service.dead("proj")

    assert "orphan-repo" in str(exc.value)
    # No partial dead: the otherwise-clean, remote-backed MAIN repo is untouched too —
    # proving the preflight covered the whole set before acting on any of it.
    assert main_path.exists()
    assert orphan_path.exists()
    assert (orphan_path / "notes.md").exists()
    assert store.get("proj") is not None
    assert store.get("proj").state == ContextState.ALIVE  # type: ignore[union-attr]


# ------------------------------------------------------------------ happy path


def test_dead_removes_every_clean_repo_in_the_set(tmp_path: Path, workspace_root: Path) -> None:
    """The full multi-repo happy path: main + 2 associated, all clean, dead() removes
    all three and transitions the context to DEAD."""
    main_remote = _bare_remote(tmp_path, "main-remote.git")
    assoc1_remote = _bare_remote(tmp_path, "assoc1-remote.git")
    assoc2_remote = _bare_remote(tmp_path, "assoc2-remote.git")
    _clone_with_initial_commit(main_remote, tmp_path / "seed-main")
    _clone_with_initial_commit(assoc1_remote, tmp_path / "seed-assoc1")
    _clone_with_initial_commit(assoc2_remote, tmp_path / "seed-assoc2")

    service, store = _make_service(workspace_root)
    main_path = workspace_root / "repos" / "main-repo"
    assoc1_path = workspace_root / "repos" / "assoc1-repo"
    assoc2_path = workspace_root / "repos" / "assoc2-repo"
    _run(["git", "clone", str(main_remote), str(main_path)])
    _run(["git", "clone", str(assoc1_remote), str(assoc1_path)])
    _run(["git", "clone", str(assoc2_remote), str(assoc2_path)])

    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.ALIVE,
            repo_slug="main-repo",
            repo_url=str(main_remote),
            created_at="2026-08-23T00:00:00+00:00",
            alive_since="2026-08-23T00:00:00+00:00",
            associated_repos=(
                AssociatedRepo(slug="assoc1-repo", url=str(assoc1_remote)),
                AssociatedRepo(slug="assoc2-repo", url=str(assoc2_remote)),
            ),
        )
    )

    ctx = service.dead("proj")

    assert ctx.state == ContextState.DEAD
    assert not main_path.exists()
    assert not assoc1_path.exists()
    assert not assoc2_path.exists()
    assert ctx.associated_repos == (
        AssociatedRepo(slug="assoc1-repo", url=str(assoc1_remote)),
        AssociatedRepo(slug="assoc2-repo", url=str(assoc2_remote)),
    )
