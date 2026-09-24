"""``context alive`` clones and hooks; it writes no specs and commits nothing.

Intent: CONTRACT — 0.4.8 AC3.7 (alive half), AC4.7, AC9.1; T-048-02.

Real ``GitSubprocessClient`` against bare remotes in ``tmp_path`` with the real hook
installer: a DEAD context going ALIVE leaves every repo of the set exactly as the remote
holds it (HEAD unchanged, porcelain clean, no ``specs/``) with the pre-push hook present.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from dadaia_workspace.features.workspace.bootstrap import install_git_hooks  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
from tests.fakes import FakeContextStore  # noqa: E402

pytestmark = [pytest.mark.integration]


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def _seeded_remote(tmp_path: Path, name: str) -> tuple[Path, str]:
    bare = tmp_path / f"{name}.git"
    subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
    seed = tmp_path / f"seed-{name}"
    subprocess.run(["git", "clone", "-q", str(bare), str(seed)], check=True)
    _git(seed, "config", "user.email", "test@example.com")
    _git(seed, "config", "user.name", "Test")
    (seed / "README.md").write_text("init\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-q", "-m", "init")
    _git(seed, "push", "-q", "-u", "origin", "HEAD")
    return bare, _git(seed, "rev-parse", "HEAD")


def test_alive_on_dead_context_writes_no_specs_commits_nothing_and_hooks_every_repo(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "ws"
    (workspace / "repos").mkdir(parents=True)
    main_url, main_head = _seeded_remote(tmp_path, "app")
    assoc_url, assoc_head = _seeded_remote(tmp_path, "lib")
    store = FakeContextStore()
    store.save(
        SpecContextProject(
            name="app",
            repo_slug="app",
            repo_url=str(main_url),
            state=ContextState.DEAD,
            created_at="2026-09-24T00:00:00Z",
            associated_repos=(AssociatedRepo(slug="lib", url=str(assoc_url)),),
        )
    )
    service = SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace,
        install_hooks=lambda repo: install_git_hooks(repo, force=True),
    )

    ctx = service.alive("app")

    assert ctx.state is ContextState.ALIVE
    for slug, head in (("app", main_head), ("lib", assoc_head)):
        repo = workspace / "repos" / slug
        assert _git(repo, "rev-parse", "HEAD") == head, f"{slug}: alive must commit nothing"
        assert _git(repo, "status", "--porcelain") == "", f"{slug}: alive must write nothing"
        assert not (repo / "specs").exists(), f"{slug}: alive must write no specs"
        assert (repo / ".git" / "hooks" / "pre-push").is_file(), f"{slug}: hook missing"
