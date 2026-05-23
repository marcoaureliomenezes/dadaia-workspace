"""Unit tests for GitSubprocessClient bug fixes (T-BCR-04).

Bugs covered:
  Bug 1 — commit_all: git add -A engulfs embedded git repos.
  Bug 2 — GitSyncError with empty stderr on submodule no-op.
  Bug 4 — git push fails without upstream tracking.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dadaia_workspace.core.exceptions import GitSyncError
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient

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
# Bug 2 — silent no-op when returncode != 0 but stdout and stderr are empty
# ---------------------------------------------------------------------------


def test_commit_all_treats_empty_stdout_stderr_as_noop() -> None:
    """If git commit exits non-zero with both stdout and stderr empty,
    commit_all must NOT raise GitSyncError (submodule edge case).
    """
    fake_result = MagicMock()
    fake_result.returncode = 1
    fake_result.stdout = ""
    fake_result.stderr = ""

    with patch(
        "dadaia_workspace.infrastructure.git_subprocess.subprocess.run",
        return_value=fake_result,
    ):
        client = GitSubprocessClient()
        # Must not raise
        client.commit_all(Path("/fake/repo"), "test commit")


def test_commit_all_raises_with_meaningful_message_on_real_failure() -> None:
    """If git commit exits non-zero with actual output, GitSyncError must include
    both stdout and stderr in its message.

    _stage_files_safe makes 2 calls before git commit:
      1. git add -u
      2. git ls-files --others --exclude-standard  (returns empty → no extra adds)
    Then git commit is the 3rd call.
    """
    ok_result = MagicMock()
    ok_result.returncode = 0
    ok_result.stdout = ""
    ok_result.stderr = ""

    ls_result = MagicMock()
    ls_result.returncode = 0
    ls_result.stdout = ""  # no untracked files
    ls_result.stderr = ""

    commit_result = MagicMock()
    commit_result.returncode = 1
    commit_result.stdout = "error: some stdout detail"
    commit_result.stderr = "fatal: some stderr detail"

    with patch(
        "dadaia_workspace.infrastructure.git_subprocess.subprocess.run",
        side_effect=[ok_result, ls_result, commit_result],
    ):
        client = GitSubprocessClient()
        with pytest.raises(GitSyncError) as exc_info:
            client.commit_all(Path("/fake/repo"), "test commit")

    msg = str(exc_info.value)
    assert "some stdout detail" in msg
    assert "some stderr detail" in msg


# ---------------------------------------------------------------------------
# Bug 4 — push sets upstream tracking when missing
# ---------------------------------------------------------------------------


def test_push_uses_set_upstream_when_no_tracking_configured(tmp_path: Path) -> None:
    """On first push (no upstream), push() must call git push -u origin <branch>.

    We simulate the no-upstream case by making `git rev-parse --abbrev-ref @{u}`
    return non-zero (no tracking), then verifying the push call uses -u.
    """
    # We use a real repo + a bare remote so git push can actually succeed
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

    # At this point no upstream tracking branch is set
    tracking_check = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert tracking_check.returncode != 0, "pre-condition: no upstream should be set"

    client = GitSubprocessClient()
    client.push(local)  # must NOT raise

    # After push, the upstream should now be set
    tracking_after = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        cwd=local,
        capture_output=True,
        text=True,
    )
    assert tracking_after.returncode == 0, "upstream tracking must be set after push -u"


def test_push_uses_plain_push_when_tracking_already_set(tmp_path: Path) -> None:
    """If upstream is already configured, push() should use plain `git push`
    (not git push -u), verified by checking the git subprocess call sequence.
    """
    # Simulate tracking already configured by mocking subprocess.run
    tracking_result = MagicMock()
    tracking_result.returncode = 0
    tracking_result.stdout = "origin/main"
    tracking_result.stderr = ""

    push_result = MagicMock()
    push_result.returncode = 0
    push_result.stdout = ""
    push_result.stderr = ""

    calls_made: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> MagicMock:
        calls_made.append(args)
        if "--abbrev-ref" in args:
            return tracking_result
        return push_result

    with patch(
        "dadaia_workspace.infrastructure.git_subprocess.subprocess.run",
        side_effect=fake_run,
    ):
        client = GitSubprocessClient()
        client.push(Path("/fake/repo"))

    push_calls = [c for c in calls_made if "push" in c and "--abbrev-ref" not in c]
    assert len(push_calls) == 1
    assert "-u" not in push_calls[0], "plain push should not include -u when tracking is set"
    assert "push" in push_calls[0]
