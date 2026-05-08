"""Git client using subprocess."""

import shutil
import subprocess
from pathlib import Path

from dadaia_workspace.core.exceptions import GitOperationError


class GitSubprocessClient:
    def _run(self, args: list[str], cwd: Path | None = None, check: bool = True) -> str:
        try:
            result = subprocess.run(
                args,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitOperationError(
                f"git command failed: {' '.join(args)}\n{e.stderr}"
            ) from e

    def clone(self, repo_ref: str, target_dir: Path) -> None:
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        is_remote = repo_ref.startswith(("http", "git@", "ssh://", "git://"))
        if is_remote:
            # Skip if already cloned (idempotent)
            if target_dir.exists() and self.is_git_repo(target_dir):
                return
            self._run(["git", "clone", repo_ref, str(target_dir)])
        else:
            # Local path: copy the full directory tree (including uncommitted content).
            # git clone would only copy tracked files and requires a .git directory.
            src = Path(repo_ref).resolve()
            if not src.exists():
                raise GitOperationError(f"Local repo path does not exist: {src}")
            if target_dir.exists():
                return  # already materialized (idempotent)
            shutil.copytree(src, target_dir, symlinks=False)

    def is_git_repo(self, path: Path) -> bool:
        return (path / ".git").exists()

    def has_changes(self, path: Path) -> bool:
        output = self._run(["git", "status", "--porcelain"], cwd=path)
        return bool(output)

    def has_remote(self, path: Path) -> bool:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(path),
            capture_output=True,
            text=True,
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    def commit_all(self, path: Path, message: str) -> None:
        self._run(["git", "add", "-A"], cwd=path)
        self._run(["git", "commit", "-m", message], cwd=path)

    def push(self, path: Path) -> None:
        self._run(["git", "push", "origin"], cwd=path)
