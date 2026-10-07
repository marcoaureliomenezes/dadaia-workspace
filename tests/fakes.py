"""In-memory fakes for the container-built collaborators — unit tests without I/O."""

from pathlib import Path
from typing import Any

from dadaia_workspace import container
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorStatus


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


def gate_fixes() -> Any:
    """The fix inputs a pure push-gate test feeds the decision (the CLI builds the real ones)."""
    from dadaia_workspace.features.chokepoints.branch_policy import GateFixes

    return GateFixes(repo="/repo")


def no_worktree_rows(_root: Path) -> tuple[list[dict[str, Any]], str, str]:
    """The owner's rows with no open worktree: no process is spawned to read them."""
    return [], "", ""


class NoWorktreeContainer:
    """``dadaia_workspace.container`` whose spec-context service reads no worktree rows."""

    def build_spec_context_service(self, workspace_root: Path) -> Any:
        return container.build_spec_context_service(workspace_root, rows=no_worktree_rows)

    def build_git_client(self) -> Any:
        return container.build_git_client()
