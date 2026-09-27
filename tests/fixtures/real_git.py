"""Real git in tmp_path — the one fixture every git question is asked against (AC9.4)."""

import subprocess
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    """One git command in *cwd*; its stripped stdout, raising on a non-zero exit."""
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout.strip()


def identify(repo: Path) -> None:
    git(repo, "config", "user.email", "t@example.invalid")
    git(repo, "config", "user.name", "T")


def seeded_remote(
    parent: Path, name: str, *, files: dict[str, str] | None = None, branch: str = "main"
) -> Path:
    """A bare ``<parent>/<name>.git`` whose *branch* carries one commit of *files*."""
    bare, seed = parent / f"{name}.git", parent / f"seed-{name}"
    git(parent, "init", "-q", "--bare", "-b", branch, str(bare))
    git(parent, "init", "-q", "-b", branch, str(seed))
    identify(seed)
    for rel, text in (files or {"README.md": "init\n"}).items():
        (seed / rel).parent.mkdir(parents=True, exist_ok=True)
        (seed / rel).write_text(text, encoding="utf-8")
    git(seed, "add", "-A")
    git(seed, "commit", "-q", "-m", "init")
    git(seed, "push", "-q", str(bare), f"HEAD:{branch}")
    return bare


def clone(remote: Path, dest: Path) -> Path:
    """A working clone of *remote* at *dest*, with a committer identity."""
    git(remote.parent, "clone", "-q", str(remote), str(dest))
    identify(dest)
    return dest


ZERO = "0" * 40


class PushRepo:
    """A work clone with a bare ``origin``: its commits are what a real push carries."""

    def __init__(self, parent: Path, branch: str = "feature/0.0.1") -> None:
        self.remote = parent / "origin.git"
        self.path = parent / "repo"
        git(parent, "init", "-q", "--bare", "-b", branch, str(self.remote))
        git(parent, "init", "-q", "-b", branch, str(self.path))
        identify(self.path)
        git(self.path, "remote", "add", "origin", str(self.remote))

    def commit(self, files: dict[str, str | bytes], message: str = "change") -> str:
        """Commit *files* on HEAD; the new commit's sha."""
        for rel, data in files.items():
            target = self.path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data) if isinstance(data, bytes) else target.write_text(data)
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "--allow-empty", "-m", message)
        return git(self.path, "rev-parse", "HEAD")

    def publish(self, branch: str | None = None) -> str:
        """Push HEAD to origin's *branch* (HEAD's own by default) — published history."""
        git(self.path, "push", "-q", "origin", f"HEAD:refs/heads/{branch}" if branch else "HEAD")
        return git(self.path, "rev-parse", "HEAD")
