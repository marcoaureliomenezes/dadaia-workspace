"""Git client using subprocess."""

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
        # Skip if already cloned (idempotent)
        if target_dir.exists() and self.is_git_repo(target_dir):
            return
        # For local paths, use the absolute resolved path
        if not repo_ref.startswith(("http", "git@", "ssh://", "git://")):
            repo_ref = str(Path(repo_ref).resolve())
        self._run(["git", "clone", repo_ref, str(target_dir)])

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
