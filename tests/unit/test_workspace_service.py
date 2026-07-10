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
    assert (workspace_root / ".dadaia" / "src").is_dir()
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


def _user_prompt_submit(settings_path: Path) -> list:  # type: ignore[type-arg]
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    return data["hooks"]["UserPromptSubmit"]


def test_configure_hook_writes_canonical_schema_and_supersedes_stale_sh(
    service: WorkspaceService, workspace_root: Path
) -> None:
    """_configure_hook must write the canonical nested Claude Code hook schema (a
    matcher entry with a nested `hooks` array), never the legacy flat entry — and
    given a stale ctx-inject.sh entry it must REPLACE it with the Python module
    command, not append a duplicate (bug pin: T-018-17, hooks.UserPromptSubmit.1.hooks
    Expected array)."""
    ws = Workspace.from_root(workspace_root)
    service._configure_hook(ws)

    entries = _user_prompt_submit(ws.claude_dir / "settings.json")
    assert len(entries) == 1
    entry = entries[0]
    assert entry["matcher"] == ""
    assert isinstance(entry["hooks"], list) and entry["hooks"]
    assert entry["hooks"][0]["type"] == "command"
    # T-018-17: command is now Python module invocation, not .sh path.
    assert "dadaia_workspace.hooks.ctx_inject" in entry["hooks"][0]["command"]
    assert "ctx-inject.sh" not in entry["hooks"][0]["command"]
    # Legacy flat schema must not leak to the top level.
    assert "command" not in entry

    # Now supersede: pre-populate with the stale .sh command (simulates a workspace
    # that was initialized before T-018-17).
    stale_ws_root = workspace_root.parent / "stale-ws"
    stale_ws = Workspace.from_root(stale_ws_root)
    stale_sh_command = str(stale_ws.dadaia_dir / "scripts" / "ctx-inject.sh")
    stale_ws.claude_dir.mkdir(parents=True, exist_ok=True)
    settings_path = stale_ws.claude_dir / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {
                            "matcher": "",
                            "hooks": [{"type": "command", "command": stale_sh_command}],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    service._configure_hook(stale_ws)

    superseded_entries = _user_prompt_submit(settings_path)
    # SUPERSEDE: exactly one entry — the .sh was replaced, not duplicated.
    assert len(superseded_entries) == 1, "must not append a duplicate; stale .sh must be superseded"
    superseded_entry = superseded_entries[0]
    assert isinstance(superseded_entry.get("hooks"), list)
    cmd = superseded_entry["hooks"][0]["command"]
    assert "dadaia_workspace.hooks.ctx_inject" in cmd
    assert "ctx-inject.sh" not in cmd
