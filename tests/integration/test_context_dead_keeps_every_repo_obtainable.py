"""A dead context must stay re-obtainable: every repo it deletes keeps a clone URL.

Intent: CONTRACT — context-dead-destroys-associated-repo-without-url.

Real git + bare remotes in ``tmp_path`` (the ``test_associated_repos_alive_dead.py``
convention): ``dead()`` back-fills EVERY repo's URL from its origin before deleting it,
refuses to delete one it could never clone back, and ``alive()`` refuses a URL-less
missing repo with a runnable ``fix:`` line instead of a raw clone failure.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.exceptions import RepoUrlMissingError  # noqa: E402
from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    AssociatedRepo,
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from dadaia_workspace.features.specs.canon import scaffold as canon_scaffold  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
from tests.fakes import FakeContextStore  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _run(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, capture_output=True, check=True)


def _seeded_remote(tmp_path: Path, name: str) -> Path:
    bare = tmp_path / f"{name}.git"
    _run(["git", "init", "--bare", str(bare)])
    seed = tmp_path / f"seed-{name}"
    _run(["git", "clone", str(bare), str(seed)])
    _run(["git", "config", "user.email", "t@example.com"], cwd=seed)
    _run(["git", "config", "user.name", "T"], cwd=seed)
    (seed / "README.md").write_text("init\n")
    _run(["git", "add", "README.md"], cwd=seed)
    _run(["git", "commit", "-m", "init"], cwd=seed)
    _run(["git", "push", "-u", "origin", "HEAD"], cwd=seed)
    return bare


def _setup(tmp_path: Path, lib_url: str) -> tuple[SpecContextService, FakeContextStore, Path]:
    ws = tmp_path / "ws"
    (ws / "repos").mkdir(parents=True)
    main = _seeded_remote(tmp_path, "main")
    store = FakeContextStore()
    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.DEAD,
            repo_slug="main",
            repo_url=str(main),
            created_at="2026-09-24T00:00:00+00:00",
            associated_repos=(AssociatedRepo(slug="lib", url=lib_url),),
        )
    )
    service = SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=ws,
        scaffold_specs=canon_scaffold,
    )
    return service, store, ws


def test_alive_dead_alive_cycle_keeps_a_bare_registered_associated_repo(tmp_path: Path) -> None:
    lib = _seeded_remote(tmp_path, "lib")
    service, store, ws = _setup(tmp_path, "")
    _run(["git", "clone", str(lib), str(ws / "repos" / "lib")])

    service.alive("proj")
    dead = service.dead("proj", commit=True)

    assert dead.associated_repos == (AssociatedRepo(slug="lib", url=str(lib)),)
    service.alive("proj")
    assert (ws / "repos" / "lib" / "README.md").is_file()


def test_dead_refuses_to_delete_a_repo_it_could_never_clone_back(tmp_path: Path) -> None:
    service, store, ws = _setup(tmp_path, "")
    lib_path = ws / "repos" / "lib"
    _run(["git", "init", str(lib_path)])
    service.alive("proj")

    with pytest.raises(RepoUrlMissingError, match=r"fix: git -C repos/lib remote add origin"):
        service.dead("proj", commit=True)

    assert lib_path.is_dir() and (ws / "repos" / "main").is_dir()
    assert store.get("proj").state == ContextState.ALIVE  # type: ignore[union-attr]


def test_alive_refuses_a_legacy_url_less_missing_repo_with_a_fix_line(tmp_path: Path) -> None:
    service, store, ws = _setup(tmp_path, "")

    with pytest.raises(RepoUrlMissingError, match=r"fix: \.dadaia/\.venv/bin/dadaia context repo"):
        service.alive("proj")

    assert store.get("proj").state == ContextState.DEAD  # type: ignore[union-attr]
