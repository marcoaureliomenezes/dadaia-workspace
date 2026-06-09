"""Unit tests for T-016-P06 — WorkflowLauncher extract to infrastructure layer.

Tests cover:
  1. WorkflowLauncher protocol — FakeWorkflowLauncher satisfies the protocol.
  2. PanelService.run_workflow uses the injected launcher (no subprocess in features).
  3. PanelService.run_workflow raises RuntimeError for unknown workflows.
  4. PanelService.run_workflow raises RuntimeError when workflow is already running.
  5. PanelService.run_workflow evicts stale PID when launcher reports dead.
  6. State survives restart via JsonWorkflowStateStore (restart-survival).
  7. JsonWorkflowStateStore.load returns empty dict when file absent.
  8. JsonWorkflowStateStore atomically saves and loads state.
  9. SubprocessWorkflowLauncher.is_alive returns False for non-existent PID.
  10. SubprocessWorkflowLauncher.is_alive returns True for own PID.
  11. No subprocess or os.kill imports remain in features/panel/service.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.infrastructure.json_workflow_state_store import JsonWorkflowStateStore
from dadaia_workspace.infrastructure.workflow_launcher_adapter import SubprocessWorkflowLauncher

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeWorkflowLauncher:
    """Fake WorkflowLauncher that records calls and controls liveness."""

    def __init__(self) -> None:
        self.launched: list[tuple[str, str, str]] = []  # (name, cwd, exe)
        self._next_pid = 1000
        self._alive_pids: set[int] = set()

    def launch(
        self,
        workflow_name: str,
        workspace_root: str,
        *,
        python_executable: str,
    ) -> int:
        pid = self._next_pid
        self._next_pid += 1
        self.launched.append((workflow_name, workspace_root, python_executable))
        self._alive_pids.add(pid)
        return pid

    def is_alive(self, pid: int) -> bool:
        return pid in self._alive_pids

    def kill(self, pid: int) -> None:
        """Test helper: mark a PID as dead."""
        self._alive_pids.discard(pid)


def _assert_workflow_launcher_protocol(launcher: Any) -> None:
    """Assert that *launcher* satisfies the WorkflowLauncher protocol at runtime."""
    assert callable(getattr(launcher, "launch", None)), "launch() must be callable"
    assert callable(getattr(launcher, "is_alive", None)), "is_alive() must be callable"


class FakeServerRegistryService:
    def list_entries(self, project: str | None = None, include_stale: bool = True) -> list[Any]:
        return []


class FakeSpecContextService:
    def list_all(self) -> list[Any]:
        return []


class FakeWorkflowsService:
    def __init__(self, known: list[str]) -> None:
        self._known = known

    def list_summaries(self) -> list[Any]:
        from dataclasses import dataclass

        @dataclass
        class _Summary:
            name: str

        return [_Summary(name=n) for n in self._known]


def _build_service(
    known_workflows: list[str] | None = None,
    launcher: FakeWorkflowLauncher | None = None,
    state_store: JsonWorkflowStateStore | None = None,
) -> tuple[PanelService, FakeWorkflowLauncher]:
    if launcher is None:
        launcher = FakeWorkflowLauncher()
    svc = PanelService(
        registry=FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        workflow_launcher=launcher,
        workflow_state_store=state_store,
    )
    if known_workflows is not None:
        svc._workflows_service_override = FakeWorkflowsService(known_workflows)  # type: ignore[attr-defined]
    return svc, launcher


# ---------------------------------------------------------------------------
# 1. FakeWorkflowLauncher satisfies the WorkflowLauncher protocol
# ---------------------------------------------------------------------------


def test_fake_launcher_satisfies_protocol() -> None:
    """FakeWorkflowLauncher must satisfy the WorkflowLauncher protocol."""
    launcher = FakeWorkflowLauncher()
    _assert_workflow_launcher_protocol(launcher)


# ---------------------------------------------------------------------------
# 2. PanelService.run_workflow uses the injected launcher
# ---------------------------------------------------------------------------


def test_run_workflow_delegates_to_launcher() -> None:
    """run_workflow must call the injected launcher.launch(), not subprocess."""
    svc, launcher = _build_service(known_workflows=["deploy"])
    result = svc.run_workflow("deploy")
    assert len(launcher.launched) == 1
    name, cwd, exe = launcher.launched[0]
    assert name == "deploy"
    # run_workflow passes str(workspace_root); on Windows that's the native
    # "\workspace", the correct cwd for the subprocess on that host.
    assert cwd == str(Path("/workspace"))
    assert result["workflow"] == "deploy"
    assert isinstance(result["pid"], int)


# ---------------------------------------------------------------------------
# 3. RuntimeError for unknown workflow
# ---------------------------------------------------------------------------


def test_run_workflow_raises_for_unknown() -> None:
    """run_workflow must raise RuntimeError when workflow name is not known."""
    svc, _ = _build_service(known_workflows=["deploy"])
    with pytest.raises(RuntimeError, match="not found"):
        svc.run_workflow("nonexistent")


# ---------------------------------------------------------------------------
# 4. RuntimeError when already running (PID alive)
# ---------------------------------------------------------------------------


def test_run_workflow_raises_already_running() -> None:
    """run_workflow must raise RuntimeError when the workflow PID is still alive."""
    svc, launcher = _build_service(known_workflows=["deploy"])
    svc.run_workflow("deploy")  # first launch
    # PID is still alive in the fake launcher — second launch must raise.
    with pytest.raises(RuntimeError, match="already running"):
        svc.run_workflow("deploy")


# ---------------------------------------------------------------------------
# 5. Evicts stale PID when launcher reports dead
# ---------------------------------------------------------------------------


def test_run_workflow_evicts_stale_pid() -> None:
    """run_workflow must evict a dead PID and re-launch."""
    svc, launcher = _build_service(known_workflows=["deploy"])
    result1 = svc.run_workflow("deploy")
    # Mark the PID as dead in the fake launcher.
    launcher.kill(result1["pid"])  # type: ignore[arg-type]
    # Second run should succeed (stale entry evicted).
    result2 = svc.run_workflow("deploy")
    assert result2["pid"] != result1["pid"]
    assert len(launcher.launched) == 2


# ---------------------------------------------------------------------------
# 6. State survives restart via JsonWorkflowStateStore
# ---------------------------------------------------------------------------


def test_state_survives_restart(tmp_path: Path) -> None:
    """State persisted by one PanelService instance must be visible to the next."""
    store = JsonWorkflowStateStore(tmp_path)
    launcher1 = FakeWorkflowLauncher()
    svc1, _ = _build_service(known_workflows=["deploy"], launcher=launcher1, state_store=store)
    result = svc1.run_workflow("deploy")
    pid = result["pid"]  # type: ignore[assignment]

    # Simulate restart: build a new PanelService with the same store.
    launcher2 = FakeWorkflowLauncher()
    # Pre-populate launcher2's alive set so is_alive(pid) returns True.
    launcher2._alive_pids.add(pid)
    svc2, _ = _build_service(known_workflows=["deploy"], launcher=launcher2, state_store=store)
    # The persisted state shows "deploy" as running — must raise "already running".
    with pytest.raises(RuntimeError, match="already running"):
        svc2.run_workflow("deploy")


# ---------------------------------------------------------------------------
# 7. JsonWorkflowStateStore.load returns empty dict when file absent
# ---------------------------------------------------------------------------


def test_state_store_load_empty_when_absent(tmp_path: Path) -> None:
    """load() must return {} when no state file exists."""
    store = JsonWorkflowStateStore(tmp_path)
    assert store.load() == {}


# ---------------------------------------------------------------------------
# 8. JsonWorkflowStateStore atomically saves and loads state
# ---------------------------------------------------------------------------


def test_state_store_save_and_load(tmp_path: Path) -> None:
    """save() + load() must round-trip the PID map correctly."""
    store = JsonWorkflowStateStore(tmp_path)
    store.save({"deploy": 1234, "build": 5678})
    loaded = store.load()
    assert loaded == {"deploy": 1234, "build": 5678}


def test_state_store_set_pid_and_remove(tmp_path: Path) -> None:
    """set_pid() adds an entry; remove() deletes it."""
    store = JsonWorkflowStateStore(tmp_path)
    store.set_pid("deploy", 999)
    assert store.load() == {"deploy": 999}
    store.remove("deploy")
    assert store.load() == {}


def test_state_store_remove_nonexistent_is_noop(tmp_path: Path) -> None:
    """remove() must be a no-op when the workflow name is not in state."""
    store = JsonWorkflowStateStore(tmp_path)
    store.remove("nonexistent")  # must not raise
    assert store.load() == {}


def test_state_store_corrupt_file_returns_empty(tmp_path: Path) -> None:
    """load() must return {} when the state file contains invalid JSON."""
    state_file = tmp_path / "running_workflows.json"
    state_file.write_text("not json", encoding="utf-8")
    store = JsonWorkflowStateStore(tmp_path)
    assert store.load() == {}


def test_state_store_file_is_valid_json(tmp_path: Path) -> None:
    """The state file written by save() must be valid JSON."""
    store = JsonWorkflowStateStore(tmp_path)
    store.save({"wf": 42})
    state_path = tmp_path / "running_workflows.json"
    parsed = json.loads(state_path.read_text())
    assert parsed == {"wf": 42}


# ---------------------------------------------------------------------------
# 9. SubprocessWorkflowLauncher.is_alive returns False for non-existent PID
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="os.kill semantics differ on Windows")
def test_subprocess_launcher_is_alive_false_for_dead_pid() -> None:
    """is_alive() must return False for a PID that definitely doesn't exist."""
    launcher = SubprocessWorkflowLauncher()
    # PID 0 is the kernel on Linux; os.kill(0, 0) signals the process group.
    # Use a very high PID that is almost certainly not running.
    assert launcher.is_alive(2**22 - 1) is False


# ---------------------------------------------------------------------------
# 10. SubprocessWorkflowLauncher.is_alive returns True for own PID
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform == "win32", reason="os.kill semantics differ on Windows")
def test_subprocess_launcher_is_alive_true_for_self() -> None:
    """is_alive() must return True for the current process's PID."""
    import os

    launcher = SubprocessWorkflowLauncher()
    assert launcher.is_alive(os.getpid()) is True


# ---------------------------------------------------------------------------
# 11. No subprocess or os.kill imports remain in features/panel/service.py
# ---------------------------------------------------------------------------


def test_service_module_has_no_subprocess_import() -> None:
    """features/panel/service.py must not import subprocess directly."""
    import ast
    from pathlib import Path as _Path

    src = (
        _Path(__file__).parents[4] / "dadaia_workspace" / "features" / "panel" / "service.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "subprocess", (
                    "features/panel/service.py must not import 'subprocess' directly. "
                    "Move subprocess use to infrastructure/workflow_launcher_adapter.py."
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "subprocess", (
                "features/panel/service.py must not import from 'subprocess'. "
                "Move subprocess use to infrastructure/workflow_launcher_adapter.py."
            )


def test_service_module_has_no_os_kill() -> None:
    """features/panel/service.py must not call os.kill directly."""
    import ast
    from pathlib import Path as _Path

    src = (
        _Path(__file__).parents[4] / "dadaia_workspace" / "features" / "panel" / "service.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # Check for os.kill(...)
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "kill"
                and isinstance(func.value, ast.Name)
                and func.value.id == "os"
            ):
                pytest.fail(
                    "features/panel/service.py must not call os.kill() directly. "
                    "Move this to infrastructure/workflow_launcher_adapter.py."
                )
