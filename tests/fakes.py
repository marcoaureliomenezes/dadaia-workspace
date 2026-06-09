"""In-memory fakes for all protocols — enable unit tests without I/O."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from dadaia_workspace.core.exceptions import (
    OrchestrationUnsupportedError,
    RunNotFoundError,
    WorkflowNotFoundError,
)
from dadaia_workspace.core.models.run_state import (
    DispatcherCapabilities,
    DispatcherMode,
    RunEvent,
    RunManifest,
    StageInvocation,
    StageResult,
    StageStatus,
)
from dadaia_workspace.core.models.server_registry import PortEntry
from dadaia_workspace.core.models.spec_context import SpecContextProject
from dadaia_workspace.core.models.workflow import WorkflowDefinition


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

    def is_git_root(self, path: Path) -> bool:
        return path.exists()


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


class FakeWorkflowStore:
    def __init__(self, workflows: Iterable[WorkflowDefinition] | None = None) -> None:
        self._by_name: dict[str, WorkflowDefinition] = {w.name: w for w in (workflows or ())}

    def add(self, workflow: WorkflowDefinition) -> None:
        self._by_name[workflow.name] = workflow

    def list(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(self._by_name.values())

    def get(self, name: str) -> WorkflowDefinition:
        if name not in self._by_name:
            raise WorkflowNotFoundError(f"workflow '{name}' not found")
        return self._by_name[name]

    def validate(self, name: str) -> tuple[str, ...]:
        if name not in self._by_name:
            return (f"workflow '{name}' not found",)
        return ()


class FakeRunStateStore:
    def __init__(self) -> None:
        self.manifests: dict[str, RunManifest] = {}
        self.events: dict[str, list[RunEvent]] = {}

    def create_run(self, manifest: RunManifest) -> None:
        self.manifests[manifest.run_id] = manifest
        self.events.setdefault(manifest.run_id, [])

    def load_run(self, run_id: str) -> RunManifest:
        if run_id not in self.manifests:
            raise RunNotFoundError(f"run '{run_id}' not found")
        return self.manifests[run_id]

    def update_manifest(self, manifest: RunManifest) -> None:
        self.manifests[manifest.run_id] = manifest

    def append_event(self, event: RunEvent) -> None:
        self.events.setdefault(event.run_id, []).append(event)

    def list_runs(self) -> tuple[RunManifest, ...]:
        return tuple(self.manifests.values())

    def iter_events(self, run_id: str) -> Iterable[RunEvent]:
        return list(self.events.get(run_id, []))


class FakeAgentDispatcher:
    """Configurable fake — defaults to native (Claude-like). Use _set_mode for variants."""

    def __init__(self, mode: DispatcherMode = DispatcherMode.NATIVE) -> None:
        self._mode = mode
        self.dispatched: list[StageInvocation] = []
        self.parallel_dispatched: list[tuple[StageInvocation, ...]] = []

    def capabilities(self) -> DispatcherCapabilities:
        runtime_name = {
            DispatcherMode.NATIVE: "claude",
            DispatcherMode.BEST_EFFORT_SEQUENTIAL: "opencode",
            DispatcherMode.UNSUPPORTED: "codex",
            DispatcherMode.CLI_ONLY: "cli",
        }[self._mode]
        return DispatcherCapabilities(
            runtime_name=runtime_name,
            supports_parallel=self._mode == DispatcherMode.NATIVE,
            supports_gates_inline=False,
            mode=self._mode,
        )

    def dispatch(self, invocation: StageInvocation) -> StageResult:
        self.dispatched.append(invocation)
        return StageResult(
            run_id=invocation.run_id,
            stage_id=invocation.stage_id,
            status=StageStatus.AWAITING_GATE,
            output_path=invocation.expected_output_path,
        )

    def dispatch_parallel(
        self, invocations: tuple[StageInvocation, ...]
    ) -> tuple[StageResult, ...]:
        if self._mode == DispatcherMode.UNSUPPORTED and any(
            inv.parallel_group for inv in invocations
        ):
            raise OrchestrationUnsupportedError("fake codex dispatcher rejects parallel_group")
        self.parallel_dispatched.append(invocations)
        return tuple(self.dispatch(inv) for inv in invocations)


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
