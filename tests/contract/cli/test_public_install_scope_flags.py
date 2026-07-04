"""Contract tests for public install scope flags."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.contract

_CONSUMER_VERSION = "0.0.0"
_runner = CliRunner()


def _register_context(workspace_root: Path, slug: str, state: str = "alive") -> None:
    """Register a consumer repo in ``spec_contexts.json`` (v0.1.58 FR4 registry detection)."""
    states_dir = workspace_root / ".dadaia" / "states"
    states_dir.mkdir(parents=True, exist_ok=True)
    registry = states_dir / "spec_contexts.json"
    data = (
        json.loads(registry.read_text(encoding="utf-8"))
        if registry.exists()
        else {"schema_version": "2", "contexts": []}
    )
    data["contexts"].append(
        {
            "name": slug,
            "state": state,
            "repo_slug": slug,
            "repo_url": f"https://example.test/{slug}.git",
            "created_at": "2026-07-04T00:00:00Z",
            "alive_since": "2026-07-04T00:00:00Z" if state == "alive" else None,
            "dead_since": None if state == "alive" else "2026-07-04T00:00:00Z",
            "current_branch": "main",
        }
    )
    registry.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _add_marker_consumer(workspace_root: Path, slug: str) -> Path:
    """Register a consumer repo under ``repos/`` via the registry (v0.1.58 FR4, Ruling G)."""
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1", "package_version": _CONSUMER_VERSION}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    _register_context(workspace_root, slug)
    return consumer


def _make_manager() -> FileSystemPublicAssetManager:
    return FileSystemPublicAssetManager()


def _init_workspace(path: Path) -> None:
    WorkspaceService(
        public_assets=_make_manager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(path)


def test_cli_install_both_flags_mutually_exclusive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--repos-only", "--workspace-only"])

    assert result.exit_code == 1
    assert "mutually exclusive" in result.output.lower() or "Error" in result.output


def test_cli_install_repos_only_flag_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--repos-only"])

    assert result.exit_code == 0, result.output


def test_cli_install_workspace_only_flag_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--workspace-only"])

    assert result.exit_code == 0, result.output


def test_cli_install_no_flags_writes_workspace_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "AGENTS.md").exists()


def test_cli_install_workspace_only_writes_root_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_workspace(tmp_path)
    consumer = _add_marker_consumer(tmp_path, "some-consumer")
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--workspace-only", "--force"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert not (consumer / "AGENTS.md").exists()


def test_cli_install_repos_only_writes_consumer_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _init_workspace(tmp_path)
    root_agents = tmp_path / "AGENTS.md"
    root_agents.unlink(missing_ok=True)
    consumer = _add_marker_consumer(tmp_path, "some-consumer")
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--repos-only", "--force"])

    assert result.exit_code == 0, result.output
    assert not root_agents.exists()
    assert (consumer / "AGENTS.md").exists()
