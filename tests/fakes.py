"""In-memory fakes for the container-built collaborators — unit tests without I/O."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus
from dadaia_workspace.core.models.spec_context import SpecContextProject


class FakeContextStore:
    def __init__(self) -> None:
        self._store: dict[str, SpecContextProject] = {}

    def save(self, ctx: SpecContextProject) -> None:
        self._store[ctx.name] = ctx

    def update(self, ctx: SpecContextProject) -> None:
        self._store[ctx.name] = ctx

    def get(self, name: str) -> SpecContextProject | None:
        return self._store.get(name)

    def list_all(self) -> list[SpecContextProject]:
        return list(self._store.values())

    def delete(self, name: str) -> None:
        self._store.pop(name, None)


class FakeGitClient:
    def __init__(self) -> None:
        self.cloned: list[tuple[str, Path]] = []
        self.committed: list[Path] = []
        self.committed_paths: list[tuple[Path, tuple[str, ...]]] = []
        self.pushed: list[Path] = []
        self.checked_out: list[tuple[Path, str]] = []
        self._dirty: set[Path] = set()
        self._has_remote: set[Path] = set()
        self._branches: dict[Path, str] = {}
        self._untracked: dict[Path, list[str]] = {}
        self._remote_urls: dict[Path, str] = {}
        self._has_commits: set[Path] = set()

    def clone(self, url: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        self.cloned.append((url, dest))

    def is_dirty(self, path: Path) -> bool:
        return path in self._dirty

    def has_commits(self, path: Path) -> bool:
        return path in self._has_commits

    def commit_all(self, path: Path, msg: str) -> None:
        self.committed.append(path)
        self._has_commits.add(path)
        self._dirty.discard(path)
        self._untracked.pop(path, None)

    def commit_paths(self, path: Path, msg: str, paths: Sequence[str]) -> None:
        """Explicit-path staging counterpart of ``commit_all`` (never a blanket sweep).

        Records the exact *paths* the caller staged in ``committed_paths`` so tests can
        assert the scaffold commit never widened beyond what it authored. A no-op when
        *paths* is empty, mirroring :class:`GitSubprocessClient`.
        """
        if not paths:
            return
        self.committed.append(path)
        self.committed_paths.append((path, tuple(paths)))
        self._has_commits.add(path)
        self._dirty.discard(path)
        self._untracked.pop(path, None)

    def has_remote(self, path: Path) -> bool:
        return path in self._has_remote

    def push(self, path: Path) -> None:
        self.pushed.append(path)

    def current_branch(self, path: Path) -> str:
        return self._branches.get(path, "main")

    def checkout(self, path: Path, branch: str) -> None:
        self.checked_out.append((path, branch))
        self._branches[path] = branch

    def is_git_root(self, path: Path) -> bool:
        return path.exists()

    def list_untracked(self, path: Path) -> list[str]:
        return list(self._untracked.get(path, []))

    def remote_url(self, path: Path) -> str:
        return self._remote_urls.get(path, "")


class FakePublicAssetManager:
    def __init__(self) -> None:
        self.staged: list[Path] = []
        self.installed: list[tuple[Path, str | None, bool]] = []
        self.doctored: list[Path] = []

    def stage(self, workspace_root: Path) -> list[str]:
        self.staged.append(workspace_root)
        (workspace_root / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
        return [str(workspace_root / ".dadaia" / "agentic")]

    def install(
        self,
        workspace_root: Path,
        harness: str | None = None,
        force: bool = False,
        scope: str = "all",
        only: str | None = None,
    ) -> list[str]:
        self.installed.append((workspace_root, harness, force))
        return [str(workspace_root / ".agents" / "skills" / "fake-skill" / "SKILL.md")]

    def list_all(self) -> dict[str, list[str]]:
        return {"agents": ["fake-agent"], "skills": ["fake-skill"]}

    def doctor(self, workspace_root: Path) -> list[DoctorLine]:
        self.doctored.append(workspace_root)
        return [DoctorLine(DoctorStatus.OK, "fake")]


class FakePythonEnvironmentManager:
    """In-memory PythonEnvironmentManager — builds venv paths using PLATFORM flags.

    Uses ``PLATFORM.venv_scripts_dir`` and ``PLATFORM.venv_exe_suffix`` so that
    tests validating venv path construction work correctly on all platforms.
    """

    def __init__(self) -> None:
        self.ensured: list[str] = []

    def ensure_workspace_venv(self, workspace_root: str) -> str:
        self.ensured.append(workspace_root)
        return f"{workspace_root}/.dadaia/.venv"

    def version_change(self, workspace_root: str) -> tuple[str | None, str | None, str]:
        return None, None, "install"

    def python_executable(self, workspace_root: str) -> str:
        from dadaia_workspace.core.platform import PLATFORM

        return (
            f"{workspace_root}/.dadaia/.venv"
            f"/{PLATFORM.venv_scripts_dir}/python{PLATFORM.venv_exe_suffix}"
        )

    def pip_executable(self, workspace_root: str) -> str:
        from dadaia_workspace.core.platform import PLATFORM

        return (
            f"{workspace_root}/.dadaia/.venv"
            f"/{PLATFORM.venv_scripts_dir}/pip{PLATFORM.venv_exe_suffix}"
        )


def register_dead(
    service: Any,
    name: str,
    repo_slug: str,
    repo_url: str,
    *,
    associated_repos: tuple[Any, ...] = (),
) -> Any:
    """Register a DEAD context record through the service's one validation seam —
    the fixture shape ``dadaia import`` produces (``create`` now materializes)."""
    from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject

    return service.register(
        SpecContextProject(
            name=name,
            state=ContextState.DEAD,
            repo_slug=repo_slug,
            repo_url=repo_url,
            created_at="2026-01-01T00:00:00+00:00",
            alive_since=None,
            dead_since=None,
            associated_repos=associated_repos,
        )
    )


def seed_dead_context(
    workspace_root: Path, name: str, repo_slug: str, repo_url: str, **kw: Any
) -> Any:
    """``register_dead`` against the workspace's real on-disk registry — the fixture
    for CLI tests about verbs other than ``create`` (which now clones)."""
    from dadaia_workspace import container

    return register_dead(
        container.build_spec_context_service(workspace_root), name, repo_slug, repo_url, **kw
    )
