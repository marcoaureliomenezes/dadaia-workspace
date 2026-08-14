"""Bug context-alive-sweeps-unrelated-worktree-changes (MEDIUM).

Intent: CONTRACT — bug context-alive-sweeps-unrelated-worktree-changes.

``dadaia context alive <ctx>`` on a context repo with a dirty working tree produced the
scaffold commit ``chore(scaffold): dadaia context alive specs baseline`` via
``GitClient.commit_all`` — a blanket ``git add -u`` + untracked sweep — which silently
folded in EVERY pre-existing unrelated modified tracked file (e.g. a docker-compose.yml
and a supervisord.conf the operator was mid-edit on) into a tool-authored commit, with no
operator consent. The scaffold commit must stage exactly the specs/ baseline (+
AGENTS.md / tests/AGENTS.md) it authors; pre-existing unrelated worktree modifications
must stay untouched and uncommitted (workspace rule: a commit stages exactly what its
change touched, never -A over a shared tree).

Runs against the REAL ``GitSubprocessClient`` and a real git repo in ``tmp_path`` — the
executed path, not a fake.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fcntl")

from dadaia_workspace.core.models.spec_context import (  # noqa: E402
    ContextState,
    SpecContextProject,
)
from dadaia_workspace.features.spec_context.service import SpecContextService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient  # noqa: E402
from tests.fakes import FakeContextStore  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.slow]


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, capture_output=True, check=True)


def test_alive_scaffold_commit_never_sweeps_preexisting_dirty_tracked_files(
    tmp_path: Path,
) -> None:
    """Repro: dirty two pre-existing TRACKED files unrelated to specs/ in a context
    repo, then run the real ``alive()`` code path. The scaffold commit must include
    ONLY the specs/ baseline it authored; the two unrelated files must remain
    dirty/uncommitted afterwards (``git status`` non-empty for both)."""
    workspace_root = tmp_path / "ws"
    (workspace_root / "repos").mkdir(parents=True)
    repo = workspace_root / "repos" / "ctx-repo"
    repo.mkdir()

    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "test@test.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)

    (repo / "docker-compose.yml").write_text("services:\n  app:\n    image: old\n")
    (repo / "supervisord.conf").write_text("[supervisord]\nnodaemon=old\n")
    _run(["git", "add", "-A"], repo)
    _run(["git", "commit", "-m", "init"], repo)

    # Operator WIP, dirtied BEFORE alive() runs — unrelated to the specs scaffold.
    (repo / "docker-compose.yml").write_text("services:\n  app:\n    image: new\n")
    (repo / "supervisord.conf").write_text("[supervisord]\nnodaemon=new\n")

    store = FakeContextStore()
    store.save(
        SpecContextProject(
            name="proj",
            state=ContextState.DEAD,
            repo_slug="ctx-repo",
            repo_url="https://example.invalid/ctx-repo.git",
            created_at="2026-08-14T00:00:00+00:00",
            alive_since=None,
            dead_since=None,
            current_branch=None,
        )
    )
    service = SpecContextService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=workspace_root,
    )

    service.alive("proj")

    # The scaffold commit stages ONLY the specs/ baseline (+ AGENTS.md) it authored.
    stat = subprocess.run(
        ["git", "show", "--stat", "--format=", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    committed_paths = [line.split("|")[0].strip() for line in stat.splitlines() if "|" in line]
    assert committed_paths, "scaffold commit must have touched files"
    assert all(p == "AGENTS.md" or p.startswith("specs/") for p in committed_paths), (
        f"scaffold commit swept non-scaffold paths: {committed_paths}"
    )
    assert "docker-compose.yml" not in committed_paths
    assert "supervisord.conf" not in committed_paths

    # The pre-existing unrelated files stay dirty and uncommitted — operator WIP is
    # never silently swept into a tool-authored commit.
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert "docker-compose.yml" in status
    assert "supervisord.conf" in status
