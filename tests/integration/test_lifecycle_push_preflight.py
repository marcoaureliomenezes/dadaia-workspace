"""Integration regression for blocked push lifecycle preflight."""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace import container
from dadaia_workspace.features.lifecycle.service import (
    LifecycleCommandStatus,
    LifecyclePreflightService,
)
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.runtime_files import FilesystemRuntimeFileAdapter


def _init_workspace(path: Path) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)
    return path


def test_blocked_push_preflight_emits_resumable_handoff_without_policy_change(
    tmp_path: Path,
) -> None:
    workspace = _init_workspace(tmp_path)
    codex_config = workspace / ".codex" / "config.toml"
    codex_rules = tuple(sorted((workspace / ".codex").rglob("*.rules")))
    before_config = codex_config.read_text(encoding="utf-8")
    before_rules = {
        path.relative_to(workspace).as_posix(): path.read_text(encoding="utf-8")
        for path in codex_rules
    }

    result = LifecyclePreflightService().blocked_push_preflight(
        context="dadaia-workspace",
        release_id="v0.1.15",
        commit_sha="abc123",
        runtime_files=FilesystemRuntimeFileAdapter(workspace),
        run_id="push-run",
    )

    assert result.command.status is LifecycleCommandStatus.BLOCKED
    assert result.command.blocked is not None
    assert result.command.blocked.reason == "push requires security-reviewer approval"
    assert result.command.blocked.operator_command == "git push"
    assert result.command.blocked.resume_token == "dadaia-workspace:v0.1.15:push:abc123"
    assert (
        result.handoff.path == ".dadaia/handoff/dadaia-workspace/push-run-blocked-push.handoff.json"
    )

    handoff_path = workspace / result.handoff.path
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    assert handoff["metrics"]["commit_sha"] == "abc123"
    assert handoff["metrics"]["operator_command"] == "git push"
    assert handoff["metrics"]["resume_token"] == "dadaia-workspace:v0.1.15:push:abc123"
    validation = container.build_reports_validation_service(workspace).validate_file(handoff_path)
    assert validation.valid is True

    assert codex_config.read_text(encoding="utf-8") == before_config
    after_rules = {
        path.relative_to(workspace).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted((workspace / ".codex").rglob("*.rules"))
    }
    assert after_rules == before_rules
