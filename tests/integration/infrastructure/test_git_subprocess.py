"""Real-git integration tests for GitSubprocessClient.

Bugs covered:
  Bug 1 — commit_all: git add -A engulfs embedded git repos.
  Bug 4 — git push fails without upstream tracking / mismatched upstream branch name.

The MagicMock-patched `subprocess.run` unit-in-disguise fns (empty-stdout/stderr noop,
error-message detail, refspec argv, skip-when-nothing) are dropped here — they are
already covered by ``tests/unit/infrastructure/test_git_subprocess_unit.py`` via the
cleaner ``git_subprocess._run`` seam (``test_error_and_noop_mapping`` and
``test_push_argv_contract_upstream_vs_explicit_refspec``), which asserts the exact same
behaviors without a subprocess. Real-git fixtures collapse to the two that need an
actual repo/bare-remote: embedded-repo exclusion and first-push/mismatched-upstream.
"""

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

pytestmark = [pytest.mark.integration, pytest.mark.slow]

# ---------------------------------------------------------------------------
# Helper — bootstrap a real git repo in a tmp dir
# ---------------------------------------------------------------------------


def _init_git_repo(path: Path, initial_commit: bool = True) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        capture_output=True,
    )
    if initial_commit:
        (path / "README.md").write_text("init")
        subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True)


# ---------------------------------------------------------------------------
# Bug 1 — embedded git repos are excluded from git add
# ---------------------------------------------------------------------------


def test_commit_all_skips_embedded_git_repo(tmp_path: Path) -> None:
    """commit_all must not include directories that are themselves git repos.

    Strategy: create an outer repo with a nested inner repo (simulating
    .claude/worktrees/agent-*). After commit_all, the inner repo's files must
    NOT appear in the outer repo's index.
    """
    outer = tmp_path / "outer"
    _init_git_repo(outer)

    # Create an embedded git repo inside the outer repo
    inner = outer / ".claude" / "worktrees" / "agent-task-1"
    inner.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=inner, capture_output=True, check=True)
    (inner / "secret.txt").write_text("inner content")

    # Also add a normal file to the outer repo so there is something to commit
    (outer / "legit.txt").write_text("outer content")

    client = GitSubprocessClient()
    # Must not raise (no git embedding warnings treated as errors)
    client.commit_all(outer, "add legit.txt")

    # Verify the legit file was committed
    log_result = subprocess.run(
        ["git", "log", "--oneline", "-1"], cwd=outer, capture_output=True, text=True
    )
    assert "add legit.txt" in log_result.stdout

    # Verify the embedded repo's file is NOT tracked in the outer index
    ls_result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(inner / "secret.txt")],
        cwd=outer,
        capture_output=True,
        text=True,
    )
    assert ls_result.returncode != 0, (
        "secret.txt inside embedded git repo must not be tracked in outer repo"
    )


# ---------------------------------------------------------------------------
# Bug 4 — push sets upstream tracking when missing; explicit refspec on mismatch
# ---------------------------------------------------------------------------


def test_push_first_push_sets_upstream_and_mismatched_branch_uses_explicit_refspec(
    tmp_path: Path,
) -> None:
    """First push (no upstream) uses `git push -u origin <branch>`; a later push from a
    differently-named local branch tracking a mismatched remote branch name succeeds via
    the explicit refspec (v0.1.50 FR3 — plain `git push` fails under push.default=simple
    whenever the upstream branch name differs from the local branch name).
    """
    bare = tmp_path / "bare.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare", str(bare)], capture_output=True, check=True)

    local = tmp_path / "local"
    _init_git_repo(local)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)],
        cwd=local,
        capture_output=True,
        check=True,
    )

    # At this point no upstream tracking branch is set.
    tracking_check = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert tracking_check.returncode != 0, "pre-condition: no upstream should be set"

    client = GitSubprocessClient()
    client.push(local)  # must NOT raise; establishes upstream via -u

    tracking_after = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert tracking_after.returncode == 0, "upstream tracking must be set after push -u"

    # Force-establish a remote `main` branch (the local default branch name is whatever
    # `git init` picked, e.g. `master`) so the mismatch scenario below is genuine.
    subprocess.run(
        ["git", "push", "origin", "HEAD:refs/heads/main"],
        cwd=local,
        capture_output=True,
        check=True,
    )

    # A differently-named local branch tracking origin/main + a new commit + simple mode.
    subprocess.run(["git", "checkout", "-b", "work"], cwd=local, capture_output=True, check=True)
    subprocess.run(
        ["git", "branch", "--set-upstream-to=origin/main", "work"],
        cwd=local,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "push.default", "simple"], cwd=local, capture_output=True, check=True
    )
    (local / "next.txt").write_text("next")
    subprocess.run(["git", "add", "-A"], cwd=local, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "next"], cwd=local, capture_output=True, check=True)

    client.push(local)  # old plain-push behavior raises GitSyncError here

    remote_tip = subprocess.run(
        ["git", "rev-parse", "main"], cwd=bare, capture_output=True, text=True
    ).stdout.strip()
    local_tip = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=local, capture_output=True, text=True
    ).stdout.strip()
    assert remote_tip == local_tip
