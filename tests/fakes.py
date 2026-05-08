"""In-memory fakes for all protocols — enable unit tests without I/O."""

from pathlib import Path

from dadaia_workspace.core.models.spec_context import SpecContextProject
from dadaia_workspace.core.models.workspace import Workspace


class FakeWorkspaceRepository:
    def __init__(self) -> None:
        self._store: dict[str, Workspace] = {}

    def save(self, workspace: Workspace) -> None:
        self._store[str(workspace.root)] = workspace

    def load(self, root: Path) -> Workspace | None:
        return self._store.get(str(root))


class FakeSpecContextRepository:
    def __init__(self) -> None:
        self._store: dict[str, SpecContextProject] = {}

    def save(self, ctx: SpecContextProject) -> None:
        self._store[ctx.name] = ctx

    def update(self, ctx: SpecContextProject) -> None:
        self._store[ctx.name] = ctx

    def get_by_name(self, name: str) -> SpecContextProject | None:
        return self._store.get(name)

    def get_active(self) -> SpecContextProject | None:
        from dadaia_workspace.core.models.spec_context import ContextState
        for ctx in self._store.values():
            if ctx.state == ContextState.ATIVO:
                return ctx
        return None

    def list_all(self) -> list[SpecContextProject]:
        return list(self._store.values())

    def delete(self, name: str) -> None:
        self._store.pop(name, None)


class FakeGitClient:
    def __init__(self, *, fail_push: bool = False, has_remote: bool = True) -> None:
        self.cloned: list[tuple[str, Path]] = []
        self.committed: list[Path] = []
        self.pushed: list[Path] = []
        self._fail_push = fail_push
        self._has_remote = has_remote

    def clone(self, repo_ref: str, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / ".git").mkdir(exist_ok=True)
        self.cloned.append((repo_ref, target_dir))

    def is_git_repo(self, path: Path) -> bool:
        return (path / ".git").exists()

    def has_changes(self, path: Path) -> bool:
        return False

    def has_remote(self, path: Path) -> bool:
        return self._has_remote

    def commit_all(self, path: Path, message: str) -> None:
        self.committed.append(path)

    def push(self, path: Path) -> None:
        if self._fail_push:
            from dadaia_workspace.core.exceptions import GitOperationError
            raise GitOperationError("push failed (fake)")
        self.pushed.append(path)


class FakePublicAssetManager:
    def __init__(self) -> None:
        self.installed: list[tuple[Path, bool]] = []

    def install(self, target_claude_dir: Path, force: bool = False) -> list[str]:
        self.installed.append((target_claude_dir, force))
        return [str(target_claude_dir / "rules" / "fake-rule.md")]


class FakeExcelReader:
    def __init__(self, rows: list[dict[str, str]] | None = None) -> None:
        self._rows = rows or []

    def read_rows(self, file_path: Path) -> list[dict[str, str]]:
        return self._rows


class FakePythonEnvironmentManager:
    def __init__(self) -> None:
        self.ensured: list[str] = []

    def ensure_workspace_venv(self, workspace_root: str) -> str:
        self.ensured.append(workspace_root)
        return f"{workspace_root}/.dadaia/.venv"

    def python_executable(self, workspace_root: str) -> str:
        return f"{workspace_root}/.dadaia/.venv/bin/python"

    def pip_executable(self, workspace_root: str) -> str:
        return f"{workspace_root}/.dadaia/.venv/bin/pip"
