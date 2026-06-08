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


def _user_prompt_submit(settings_path: Path) -> list:  # type: ignore[type-arg]
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    return data["hooks"]["UserPromptSubmit"]


def test_configure_hook_writes_canonical_nested_schema(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """_configure_hook must write the canonical nested Claude Code hook schema
    (a matcher entry with a nested `hooks` array), never the legacy flat entry."""
    from dadaia_workspace.core.models.workspace import Workspace

    ws = Workspace.from_root(workspace_root)
    service._configure_hook(ws)

    entries = _user_prompt_submit(ws.claude_dir / "settings.json")
    assert len(entries) == 1
    entry = entries[0]
    assert entry["matcher"] == ""
    assert isinstance(entry["hooks"], list) and entry["hooks"]
    assert entry["hooks"][0]["type"] == "command"
    assert entry["hooks"][0]["command"].endswith("ctx-inject.sh")
    # Legacy flat schema must not leak to the top level.
    assert "command" not in entry


def test_configure_hook_no_duplicate_against_existing_nested_entry(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """Given the nested entry public_assets.py already wrote, _configure_hook must
    detect it via the nested command and NOT append a duplicate (the bug that broke
    Claude Code settings validation: hooks.UserPromptSubmit.1.hooks Expected array)."""
    from dadaia_workspace.core.models.workspace import Workspace

    ws = Workspace.from_root(workspace_root)
    hook_command = str(ws.dadaia_dir / "scripts" / "ctx-inject.sh")
    ws.claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = ws.claude_dir / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "matcher": "",
                            "hooks": [{"type": "command", "command": hook_command}],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    service._configure_hook(ws)

    entries = _user_prompt_submit(settings_path)
    assert len(entries) == 1, "must not append a duplicate UserPromptSubmit entry"
    # Every entry is schema-valid: carries a nested hooks array.
    for entry in entries:
        assert isinstance(entry.get("hooks"), list)


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
