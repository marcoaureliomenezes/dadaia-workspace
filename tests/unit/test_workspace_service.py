"""Unit tests for WorkspaceService."""

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.workspace import Workspace
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


def test_init_creates_dirs_state_files_and_is_idempotent(
    service: WorkspaceService, workspace_root: Path
) -> None:
    service.init(workspace_root, skip_assets=True)

    assert (workspace_root / ".dadaia" / "states").is_dir()
    assert (workspace_root / ".dadaia" / "agentic").is_dir()
    assert (workspace_root / ".dadaia" / "reports").is_dir()
    assert (workspace_root / ".dadaia" / "scripts").is_dir()
    assert not (workspace_root / ".dadaia" / "src").exists()
    assert (workspace_root / ".dadaia" / "tmp" / "python").is_dir()
    assert (workspace_root / ".dadaia" / "tmp" / "json").is_dir()
    assert (workspace_root / ".agents" / "skills").is_dir()
    assert (workspace_root / ".claude").is_dir()
    assert (workspace_root / ".codex").is_dir()

    spec_contexts_path = workspace_root / ".dadaia" / "states" / "spec_contexts.json"
    assert spec_contexts_path.exists()
    assert json.loads(spec_contexts_path.read_text()) == {"schema_version": "2", "contexts": []}

    academy_path = workspace_root / ".dadaia" / "academy" / "academy.json"
    assert academy_path.exists()
    assert json.loads(academy_path.read_text()) == {"version": "1", "courses": []}

    server_registry_path = workspace_root / ".dadaia" / "states" / "server_registry.json"
    assert server_registry_path.exists()
    registry_data = json.loads(server_registry_path.read_text())
    assert registry_data["version"] == "1"
    assert registry_data["entries"] == []

    never_inited = workspace_root.parent / "never"
    assert not service.is_initialized(never_inited)
    assert service.is_initialized(workspace_root)

    # Idempotent: modify the state file; second init must not overwrite it.
    spec_contexts_path.write_text(json.dumps({"version": "1", "contexts": [{"name": "x"}]}))
    service.init(workspace_root, skip_assets=True)
    data = json.loads(spec_contexts_path.read_text())
    assert data["contexts"] == [{"name": "x"}]


def test_init_skip_assets_writes_no_settings_and_says_ungated(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """Bug init-skip-assets-writes-gateless-claude-settings: init carried a SECOND
    ``.claude/settings.json`` writer (``_configure_hook``) that emitted a gateless file
    (UserPromptSubmit only — no gate, no venv guard, no root whitelist), silently. The
    canonical writer is ``public install`` (runtime_config); init writes NO settings.
    Under ``--skip-assets`` the ungated state is loud instead of silently half-wired."""
    _, installed = service.init(workspace_root, skip_assets=True)
    assert not (workspace_root / ".claude" / "settings.json").exists()
    assert any("ungated" in line and "dadaia public install" in line for line in installed)


def test_init_with_assets_never_writes_settings_itself(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """On the normal path the full settings projection is ``public install``'s output —
    the service itself must not touch the file (one writer, one format)."""
    _, installed = service.init(workspace_root, skip_assets=False)
    assert not any("ungated" in line for line in installed)
    assert not (workspace_root / ".claude" / "settings.json").exists()
