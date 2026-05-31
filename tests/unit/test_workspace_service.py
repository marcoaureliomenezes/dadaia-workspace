"""Unit tests for WorkspaceService."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace.service import WorkspaceService
from tests.fakes import FakePublicAssetManager, FakePythonEnvironmentManager


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    return tmp_path / "ws"


@pytest.fixture()
def service() -> WorkspaceService:
    return WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    )


def test_init_creates_dadaia_dirs(service: WorkspaceService, workspace_root: Path) -> None:
    service.init(workspace_root, skip_assets=True)
    assert (workspace_root / ".dadaia" / "states").is_dir()
    assert (workspace_root / ".dadaia" / "agentic").is_dir()
    assert (workspace_root / ".dadaia" / "reports").is_dir()
    assert (workspace_root / ".dadaia" / "scripts").is_dir()
    assert (workspace_root / ".dadaia" / "src").is_dir()
    assert (workspace_root / ".dadaia" / "tmp" / "python").is_dir()
    assert (workspace_root / ".dadaia" / "tmp" / "json").is_dir()
    assert (workspace_root / ".agents" / "skills").is_dir()
    assert (workspace_root / ".claude").is_dir()
    assert (workspace_root / ".codex").is_dir()
    assert (workspace_root / ".opencode").is_dir()


def test_init_creates_report_subdirs(service: WorkspaceService, workspace_root: Path) -> None:
    service.init(workspace_root, skip_assets=True)
    # Agents create <context>/<agent-name>/ subdirs at runtime — only the root dir is pre-created.
    assert (workspace_root / ".dadaia" / "reports").is_dir()


def test_init_creates_spec_contexts_json(service: WorkspaceService, workspace_root: Path) -> None:
    service.init(workspace_root, skip_assets=True)
    path = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data == {"schema_version": "2", "contexts": []}


def test_init_creates_academy_json(service: WorkspaceService, workspace_root: Path) -> None:
    service.init(workspace_root, skip_assets=True)
    path = workspace_root / ".dadaia" / "academy" / "academy.json"
    assert path.exists()
    data = json.loads(path.read_text())
    assert data == {"version": "1", "courses": []}


def test_init_is_idempotent(service: WorkspaceService, workspace_root: Path) -> None:
    service.init(workspace_root, skip_assets=True)
    # Modify the state file; second init must not overwrite it
    state_path = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    state_path.write_text(json.dumps({"version": "1", "contexts": [{"name": "x"}]}))
    service.init(workspace_root, skip_assets=True)
    data = json.loads(state_path.read_text())
    assert data["contexts"] == [{"name": "x"}]


def test_is_initialized_false_before_init(service: WorkspaceService, workspace_root: Path) -> None:
    assert not service.is_initialized(workspace_root)


def test_is_initialized_true_after_init(service: WorkspaceService, workspace_root: Path) -> None:
    service.init(workspace_root, skip_assets=True)
    assert service.is_initialized(workspace_root)


def test_init_creates_server_registry_json(tmp_path: Path) -> None:
    WorkspaceService(
        public_assets=FakePublicAssetManager(),
        python_env=FakePythonEnvironmentManager(),
    ).init(tmp_path)
    registry = tmp_path / ".dadaia" / "states" / "server_registry.json"
    assert registry.exists()
    import json

    data = json.loads(registry.read_text())
    assert data["version"] == "1"
    assert data["entries"] == []
