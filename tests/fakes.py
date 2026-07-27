"""In-memory fakes for all protocols — enable unit tests without I/O."""

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dadaia_workspace.core.models.server_registry import PortEntry
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
        self._untracked: dict[Path, list[str]] = {}
        self._remote_urls: dict[Path, str] = {}
        self._upstream_branches: dict[Path, str | None] = {}
        self._unpushed_commit_counts: dict[Path, int] = {}
        self._has_commits: set[Path] = set()
        self._diff_names: dict[Path, tuple[str, ...]] = {}

    def clone(self, url: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        self.cloned.append((url, dest))

    def is_dirty(self, path: Path) -> bool:
        return path in self._dirty

    def has_commits(self, path: Path) -> bool:
        return path in self._has_commits

    def diff_name_only(self, path: Path) -> tuple[str, ...]:
        return self._diff_names.get(path, ())

    def commit_all(self, path: Path, msg: str) -> None:
        self.committed.append(path)
        self._has_commits.add(path)
        self._dirty.discard(path)
        self._diff_names.pop(path, None)
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

    def upstream_branch(self, path: Path) -> str | None:
        """Configurable via ``self._upstream_branches[path] = "origin/main"``.

        Defaults to ``None`` (no upstream configured) — mirrors
        :class:`SubprocessGitClient`'s behavior on a checkout with no tracking branch.
        """
        return self._upstream_branches.get(path)

    def unpushed_commit_count(self, path: Path) -> int:
        """Configurable via ``self._unpushed_commit_counts[path] = 3``.

        Defaults to ``0`` (nothing pending) — mirrors
        :class:`SubprocessGitClient`'s behavior when there is no upstream to compare.
        """
        return self._unpushed_commit_counts.get(path, 0)


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

    def install(
        self,
        workspace_root: Path,
        target: str = "all",
        force: bool = False,
        scope: str = "all",
        only: str | None = None,
    ) -> list[str]:
        self.installed.append((workspace_root, target, force))
        return [str(workspace_root / ".agents" / "skills" / "fake-skill" / "SKILL.md")]

    def list_all(self) -> dict[str, list[str]]:
        return {"agents": ["fake-agent"], "skills": ["fake-skill"]}

    def doctor(self, workspace_root: Path) -> list[str]:
        self.doctored.append(workspace_root)
        return ["[ok] fake"]


class FakeExcelReader:
    def __init__(self, rows: list[dict[str, str]] | None = None) -> None:
        self._rows = rows or []

    def read_rows(self, file_path: Path) -> list[dict[str, str]]:
        return self._rows


def shared_connection_factory(conn: sqlite3.Connection) -> Callable[[], Any]:
    """Return a per-call connection factory that yields a non-closing view of *conn*.

    ``TelemetryAggregator`` (per-call mode) closes each connection it opens; an in-memory
    sqlite DB used by the aggregator tests cannot be reopened, so the factory hands back a
    proxy whose ``close()`` is a no-op — keeping the seeded connection alive across the
    queries of a single test (the seam the removed shared-``dao`` mode used to provide).
    """

    class _NonClosing:
        # Transparent proxy: forward every attribute get AND set to the real connection
        # (queries mutate e.g. ``conn.row_factory``), but neutralize ``close()`` so the
        # seeded connection survives the aggregator's per-call ``finally: conn.close()``.
        def __getattr__(self, name: str) -> Any:
            return getattr(conn, name)

        def __setattr__(self, name: str, value: Any) -> None:
            setattr(conn, name, value)

        def close(self) -> None:
            return None

    proxy = _NonClosing()
    return lambda: proxy


class FakeFilePermissionSetter:
    """In-memory FilePermissionSetter — records calls, never performs I/O.

    Optionally raises ``PlatformSecurityError`` on the next call when
    ``_raise_on_next`` is set to ``True`` (for testing Tier-1 error paths).
    """

    def __init__(self, raise_on_next: bool = False) -> None:
        self.restricted_files: list[tuple[Any, int]] = []
        self.restricted_dirs: list[tuple[Any, int]] = []
        self._raise_on_next = raise_on_next

    def _maybe_raise(self) -> None:
        if self._raise_on_next:
            from dadaia_workspace.core.exceptions import PlatformSecurityError

            raise PlatformSecurityError(
                "FakeFilePermissionSetter: simulated failure",
                feature_name="fake-permission-setter",
                platform="test",
            )

    def restrict_to_owner(self, path: object, mode: int = 0o600) -> None:
        self._maybe_raise()
        self.restricted_files.append((path, mode))

    def restrict_dir_to_owner(self, path: object, mode: int = 0o700) -> None:
        self._maybe_raise()
        self.restricted_dirs.append((path, mode))


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


class FakeServerRegistryStore:
    """In-memory ServerRegistryStore — keyed by port number."""

    def __init__(self) -> None:
        self._store: dict[int, PortEntry] = {}

    def save(self, entry: PortEntry) -> None:
        self._store[entry.port] = entry

    def update(self, entry: PortEntry) -> None:
        self._store[entry.port] = entry

    def get(self, port: int) -> PortEntry | None:
        return self._store.get(port)

    def list_all(self) -> list[PortEntry]:
        return sorted(self._store.values(), key=lambda e: e.port)

    def delete(self, port: int) -> None:
        self._store.pop(port, None)

    def count(self) -> int:
        return len(self._store)


class FakeProcessProbe:
    """Controllable probe — add PIDs to _alive_pids to simulate live processes."""

    def __init__(self) -> None:
        self._alive_pids: set[int] = set()

    def is_pid_alive(self, pid: int) -> bool:
        return pid in self._alive_pids


class FakeHandoffValidator:
    """Configurable fake implementing ``ValidatorPort``.

    Accepts a list of canned ``HandoffValidationError`` instances that will be
    returned on every call to ``validate()``.  Records all calls for inspection
    in ``calls``.

    Args:
        canned_errors: List of ``HandoffValidationError`` instances to return.
            Pass an empty list to simulate a valid document.
    """

    def __init__(self, canned_errors: list | None = None) -> None:
        from dadaia_workspace.core.exceptions import HandoffValidationError as _HVE  # noqa: F401

        self._canned: list = list(canned_errors or [])
        self.calls: list[dict] = []

    def validate(self, doc: dict) -> list:
        self.calls.append({"doc": doc})
        return list(self._canned)
