"""GitSubprocessClient — git operations via stdlib subprocess."""

import subprocess
from pathlib import Path

from dadaia_workspace.core.exceptions import GitCloneError, GitSyncError


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


class GitSubprocessClient:
    def clone(self, url: str, dest: Path) -> None:
        result = _run(["git", "clone", url, str(dest)])
        if result.returncode != 0:
            raise GitCloneError(f"git clone failed for {url!r}: {result.stderr.strip()}")

    def is_dirty(self, path: Path) -> bool:
        result = _run(["git", "status", "--porcelain"], cwd=path)
        return bool(result.stdout.strip())

    def commit_all(self, path: Path, msg: str) -> None:
        _run(["git", "add", "-A"], cwd=path)
        result = _run(["git", "commit", "-m", msg], cwd=path)
        if result.returncode != 0 and "nothing to commit" not in result.stdout:
            raise GitSyncError(f"git commit failed in {path}: {result.stderr.strip()}")

    def has_remote(self, path: Path) -> bool:
        result = _run(["git", "remote"], cwd=path)
        return bool(result.stdout.strip())

    def push(self, path: Path) -> None:
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
