"""GitSubprocessClient — git operations via stdlib subprocess."""

import logging
import subprocess
from pathlib import Path

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError

logger = logging.getLogger(__name__)


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _has_embedded_git(directory: Path) -> bool:
    """Return True if *directory* is itself a git repository (contains .git)."""
    return (directory / ".git").exists()


def _stage_files_safe(path: Path) -> None:
    """Stage all changes while excluding embedded git repos.

    Problem: ``git add -A`` recurses into directories that contain their own
    ``.git`` directory (embedded repos, e.g. ``.claude/worktrees/agent-*``).
    This produces git warnings ("adding embedded git repository") and pollutes
    the outer repo's index.

    Fix strategy:
    1. Use ``git add -u`` to stage modifications/deletions to already-tracked files.
    2. Find untracked directories via ``git ls-files --others --directory``.
    3. For each untracked directory, skip it if it contains its own ``.git``.
    4. Add the remaining untracked entries individually.

    This is equivalent to ``git add -A`` but respects embedded repos.
    """
    # Stage tracked-file changes (modifications + deletions)
    _run(["git", "add", "-u"], cwd=path)

    # Discover untracked items (files and dirs)
    result = _run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=path,
    )
    untracked: list[str] = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    safe: list[str] = []
    skipped: list[str] = []
    for item in untracked:
        # Paths ending with "/" are untracked directories
        full = path / item.rstrip("/")
        if full.is_dir() and _has_embedded_git(full):
            skipped.append(item)
        else:
            safe.append(item)

    if skipped:
        logger.debug(
            "commit_all: skipping %d embedded git repo(s) in %s: %s",
            len(skipped),
            path,
            skipped,
        )

    if safe:
        # git add accepts multiple paths; chunk to avoid ARG_MAX issues on
        # very large trees (practical repos are fine with a single call)
        _run(["git", "add", "--"] + safe, cwd=path)


class GitSubprocessClient:
    def clone(self, url: str, dest: Path) -> None:
        # Block the two transports that turn a URL into code/option execution:
        # ``ext::`` runs an arbitrary helper (RCE) and a leading "-" can be parsed
        # by git as an option (argument injection). Legitimate https/ssh/git@ and
        # local-path / file:// clones are still allowed.
        if url.startswith("ext::") or url.startswith("-"):
            raise GitCloneError(f"refusing to clone from unsafe URL: {url!r}")
        result = _run(["git", "clone", url, str(dest)])
        if result.returncode != 0:
            raise GitCloneError(f"git clone failed for {url!r}: {result.stderr.strip()}")

    def is_dirty(self, path: Path) -> bool:
        result = _run(["git", "status", "--porcelain"], cwd=path)
        return bool(result.stdout.strip())

    def commit_all(self, path: Path, msg: str) -> None:
        # Bug 1 fix: use safe staging that excludes embedded git repos
        _stage_files_safe(path)

        result = _run(["git", "commit", "-m", msg], cwd=path)

        # Bug 2 fix: treat empty stdout+stderr with non-zero exit as silent
        # no-op (submodule edge case); include both streams in error message.
        if result.returncode != 0:
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            if "nothing to commit" in stdout:
                return  # normal no-op
            if not stdout and not stderr:
                return  # silent no-op (submodule edge case)
            raise GitSyncError(
                f"git commit failed in {path}. stdout: {stdout!r} stderr: {stderr!r}"
            )

    def has_remote(self, path: Path) -> bool:
        result = _run(["git", "remote"], cwd=path)
        return bool(result.stdout.strip())

    def push(self, path: Path) -> None:
        # Bug 4 fix: detect whether an upstream tracking branch is configured.
        # If not, use ``git push -u origin <branch>`` to set it on first push.
        tracking = _run(["git", "rev-parse", "--abbrev-ref", "@{u}"], cwd=path)
        if tracking.returncode != 0:
            # No upstream tracking branch — set it during push
            branch = self.current_branch(path)
            result = _run(["git", "push", "-u", "origin", branch], cwd=path)
        else:
            result = _run(["git", "push"], cwd=path)

        if result.returncode != 0:
            raise GitSyncError(f"git push failed in {path}: {result.stderr.strip()}")

    def current_branch(self, path: Path) -> str:
        result = _run(["git", "branch", "--show-current"], cwd=path)
        return result.stdout.strip()

    def checkout(self, path: Path, branch: str) -> None:
        result = _run(["git", "checkout", branch], cwd=path)
        if result.returncode != 0:
            raise GitSyncError(f"git checkout {branch!r} failed in {path}: {result.stderr.strip()}")

    def is_git_root(self, path: Path) -> bool:
        result = _run(["git", "rev-parse", "--show-toplevel"], cwd=path)
        if result.returncode != 0:
            return False
        return Path(result.stdout.strip()).resolve() == path.resolve()

    def list_untracked(self, path: Path) -> list[str]:
        """Return repo-relative paths of untracked, non-gitignored files.

        Uses ``git ls-files --others --exclude-standard`` so that ``.gitignore``
        is honoured (gitignored files are NOT returned). The result drives the
        ``dead()`` review gate: an untracked file here is content that would be
        newly committed and pushed, so it must be reviewed/scanned first.
        """
        result = _run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=path,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
