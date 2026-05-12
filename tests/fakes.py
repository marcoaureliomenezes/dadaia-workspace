"""In-memory fakes for all protocols — enable unit tests without I/O."""

from pathlib import Path

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


class FakePrimaryContextStore:
    def __init__(self) -> None:
        self._data: dict[str, str] | None = None

    def write(self, name: str, repo_slug: str, specs_dir: Path) -> None:
        self._data = {"name": name, "repo_slug": repo_slug, "specs_dir": str(specs_dir)}

    def read(self) -> dict[str, str] | None:
        return self._data

    def clear(self) -> None:
        self._data = None


class FakeGitClient:
    def __init__(self) -> None:
        self.cloned: list[tuple[str, Path]] = []
        self.committed: list[Path] = []
        self.pushed: list[Path] = []
        self.checked_out: list[tuple[Path, str]] = []
        self._dirty: set[Path] = set()
        self._has_remote: set[Path] = set()
        self._branches: dict[Path, str] = {}

    def clone(self, url: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        self.cloned.append((url, dest))

    def is_dirty(self, path: Path) -> bool:
        return path in self._dirty

    def commit_all(self, path: Path, msg: str) -> None:
        self.committed.append(path)

    def has_remote(self, path: Path) -> bool:
        return path in self._has_remote

    def push(self, path: Path) -> None:
        self.pushed.append(path)

    def current_branch(self, path: Path) -> str:
        return self._branches.get(path, "main")

    def checkout(self, path: Path, branch: str) -> None:
        self.checked_out.append((path, branch))
        self._branches[path] = branch


class FakeCourseStore:
    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def save(self, course: object) -> None:
        self._store[course.slug] = course  # type: ignore[call-overload]

    def update(self, course: object) -> None:
        self._store[course.slug] = course  # type: ignore[call-overload]

    def get(self, slug: str) -> object | None:
        return self._store.get(slug)

    def list_all(self) -> list[object]:
        return list(self._store.values())

    def delete(self, slug: str) -> None:
        self._store.pop(slug, None)


class FakePublicAssetManager:
    def __init__(self) -> None:
        self.staged: list[Path] = []
        self.installed: list[tuple[Path, str, bool]] = []
        self.doctored: list[Path] = []

    def stage(self, workspace_root: Path) -> list[str]:
        self.staged.append(workspace_root)
        (workspace_root / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
        return [str(workspace_root / ".dadaia" / "agentic")]

    def install(self, workspace_root: Path, target: str = "all", force: bool = False) -> list[str]:
        self.installed.append((workspace_root, target, force))
        return [str(workspace_root / ".agents" / "skills" / "fake-skill" / "SKILL.md")]

    def doctor(self, workspace_root: Path) -> list[str]:
        self.doctored.append(workspace_root)
        return ["[ok] fake"]


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
