"""Tests for scope flags on FileSystemPublicAssetManager.install() — T-32 (P6).

Coverage:
- ``scope="all"`` (default): workspace-root pair AND consumer repos are installed.
- ``scope="workspace-only"``: workspace-root pair written; consumer repos skipped.
- ``scope="repos-only"``: consumer repos written; workspace-root pair skipped.
- CLI ``--repos-only`` and ``--workspace-only`` flags are mutually exclusive.
- CLI ``--repos-only`` alone: exit 0, consumer repos written.
- CLI ``--workspace-only`` alone: exit 0, workspace-root pair written.
- No flags: same behavior as ``scope="all"``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

_CONSUMER_VERSION = "0.0.0"
_runner = CliRunner()


def _add_marker_consumer(workspace_root: Path, slug: str) -> Path:
    """Create a marker-bearing consumer repo under ``workspace_root/repos/``."""
    consumer = workspace_root / "repos" / slug
    (consumer / ".dadaia" / "agentic").mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": "1", "package_version": _CONSUMER_VERSION}
    (consumer / ".dadaia" / "agentic" / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return consumer


def _make_manager() -> FileSystemPublicAssetManager:
    return FileSystemPublicAssetManager()


# -----------------------------------------------------------------------
# Unit tests — FileSystemPublicAssetManager.install() scope parameter
# -----------------------------------------------------------------------


def test_scope_all_installs_workspace_root_and_consumer_repos(tmp_path: Path) -> None:
    """scope='all' (default): workspace-root pair AND consumer repos get installed.

    This is the backward-compatible default — same as calling install() without scope.
    """
    manager = _make_manager()
    consumer = _add_marker_consumer(tmp_path, "test-repo")

    manager.install(tmp_path, scope="all", force=True)

    # Workspace root pair must exist
    assert (tmp_path / "AGENTS.md").exists(), "workspace-root AGENTS.md must be written"
    assert (tmp_path / "CLAUDE.md").exists(), "workspace-root CLAUDE.md must be written"
    # Consumer repo pair must also exist
    assert (consumer / "AGENTS.md").exists(), "consumer AGENTS.md must be written (scope=all)"
    assert (consumer / "CLAUDE.md").exists(), "consumer CLAUDE.md must be written (scope=all)"


def test_scope_default_is_all(tmp_path: Path) -> None:
    """Calling install() without scope= should behave identically to scope='all'."""
    manager = _make_manager()
    consumer = _add_marker_consumer(tmp_path, "test-repo")

    manager.install(tmp_path, force=True)

    assert (tmp_path / "AGENTS.md").exists()
    assert (consumer / "AGENTS.md").exists()


def test_scope_workspace_only_writes_root_skips_consumers(tmp_path: Path) -> None:
    """scope='workspace-only': workspace-root pair written; consumer repos NOT written."""
    manager = _make_manager()
    consumer = _add_marker_consumer(tmp_path, "test-repo")

    manager.install(tmp_path, scope="workspace-only", force=True)

    # Workspace root must be written
    assert (tmp_path / "AGENTS.md").exists(), (
        "workspace-root AGENTS.md must be written with scope=workspace-only"
    )
    assert (tmp_path / "CLAUDE.md").exists(), (
        "workspace-root CLAUDE.md must be written with scope=workspace-only"
    )
    # Consumer repo must NOT be written
    assert not (consumer / "AGENTS.md").exists(), (
        "consumer AGENTS.md must NOT be written with scope=workspace-only"
    )
    assert not (consumer / "CLAUDE.md").exists(), (
        "consumer CLAUDE.md must NOT be written with scope=workspace-only"
    )


def test_scope_repos_only_writes_consumers_skips_root(tmp_path: Path) -> None:
    """scope='repos-only': consumer repos written; workspace-root pair NOT written."""
    manager = _make_manager()
    consumer = _add_marker_consumer(tmp_path, "test-repo")

    # Pre-create workspace root AGENTS.md to confirm it is NOT overwritten
    root_agents = tmp_path / "AGENTS.md"
    root_agents.parent.mkdir(parents=True, exist_ok=True)
    original_root_content = "# ORIGINAL root AGENTS.md — must not be overwritten\n"
    root_agents.write_text(original_root_content, encoding="utf-8")

    manager.install(tmp_path, scope="repos-only", force=True)

    # Workspace root must NOT have been overwritten
    assert root_agents.read_text(encoding="utf-8") == original_root_content, (
        "workspace-root AGENTS.md must NOT be overwritten with scope=repos-only"
    )
    # Consumer repo must be written
    assert (consumer / "AGENTS.md").exists(), (
        "consumer AGENTS.md must be written with scope=repos-only"
    )
    assert (consumer / "CLAUDE.md").exists(), (
        "consumer CLAUDE.md must be written with scope=repos-only"
    )


def test_scope_repos_only_no_root_agents_written(tmp_path: Path) -> None:
    """scope='repos-only': workspace-root AGENTS.md is not created if absent."""
    manager = _make_manager()
    _add_marker_consumer(tmp_path, "test-repo")

    # Ensure no AGENTS.md at root before install
    root_agents = tmp_path / "AGENTS.md"
    assert not root_agents.exists(), "pre-condition: no AGENTS.md at workspace root"

    manager.install(tmp_path, scope="repos-only", force=True)

    # The workspace-root file should still not exist
    assert not root_agents.exists(), (
        "workspace-root AGENTS.md must NOT be created with scope=repos-only"
    )


def test_scope_workspace_only_multiple_consumers_none_written(tmp_path: Path) -> None:
    """scope='workspace-only': all consumers skipped even when multiple exist."""
    manager = _make_manager()
    consumer_a = _add_marker_consumer(tmp_path, "repo-a")
    consumer_b = _add_marker_consumer(tmp_path, "repo-b")

    manager.install(tmp_path, scope="workspace-only", force=True)

    assert (tmp_path / "AGENTS.md").exists(), "workspace root must be written"
    assert not (consumer_a / "AGENTS.md").exists(), "repo-a must not be written"
    assert not (consumer_b / "AGENTS.md").exists(), "repo-b must not be written"


def test_scope_repos_only_no_consumers_returns_empty_list(tmp_path: Path) -> None:
    """scope='repos-only' with no consumer repos: installed list should be empty for guardrail."""
    manager = _make_manager()
    # No consumer repos — repos/ directory does not even exist

    installed = manager.install(tmp_path, scope="repos-only", force=True)

    # Workspace-root pair entries must not appear in the installed list
    root_agents = str(tmp_path / "AGENTS.md")
    root_claude = str(tmp_path / "CLAUDE.md")
    paths_installed = [e.split(None, 1)[-1] for e in installed]
    assert root_agents not in paths_installed, (
        "workspace-root AGENTS.md path must NOT appear in installed list for scope=repos-only"
    )
    assert root_claude not in paths_installed, (
        "workspace-root CLAUDE.md path must NOT appear in installed list for scope=repos-only"
    )


# -----------------------------------------------------------------------
# CLI tests — --repos-only, --workspace-only, mutual exclusivity
# -----------------------------------------------------------------------


def test_cli_install_both_flags_mutually_exclusive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Passing both --repos-only and --workspace-only exits with code 1."""
    monkeypatch.chdir(tmp_path)
    # Need a minimal workspace so resolver doesn't fail before we hit the check
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=_make_manager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--repos-only", "--workspace-only"])

    assert result.exit_code == 1, (
        f"Expected exit code 1 when both flags are combined; got {result.exit_code}.\n"
        f"Output: {result.output}"
    )
    assert "mutually exclusive" in result.output.lower() or "Error" in result.output, (
        "Error message about mutual exclusivity must appear in output."
    )


def test_cli_install_repos_only_flag_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--repos-only flag: command exits with code 0."""
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=_make_manager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--repos-only"])

    assert result.exit_code == 0, (
        f"Expected exit code 0 for --repos-only; got {result.exit_code}.\nOutput: {result.output}"
    )


def test_cli_install_workspace_only_flag_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--workspace-only flag: command exits with code 0."""
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=_make_manager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--workspace-only"])

    assert result.exit_code == 0, (
        f"Expected exit code 0 for --workspace-only; got {result.exit_code}.\n"
        f"Output: {result.output}"
    )


def test_cli_install_no_flags_same_as_scope_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No scope flags: install behaves the same as scope='all' (backward compat)."""
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=_make_manager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install"])

    assert result.exit_code == 0, (
        f"Expected exit code 0 with no scope flags; got {result.exit_code}.\n"
        f"Output: {result.output}"
    )
    # Workspace-root AGENTS.md must be written (standard install behavior)
    assert (tmp_path / "AGENTS.md").exists(), (
        "workspace-root AGENTS.md must be written by default install"
    )


def test_cli_install_workspace_only_writes_root_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--workspace-only: root pair written; consumer repo is skipped."""
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=_make_manager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)

    # Add a consumer repo
    consumer = _add_marker_consumer(tmp_path, "some-consumer")
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--workspace-only", "--force"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "AGENTS.md").exists(), "workspace-root AGENTS.md must be written"
    assert not (consumer / "AGENTS.md").exists(), (
        "consumer AGENTS.md must NOT be written with --workspace-only"
    )


def test_cli_install_repos_only_writes_consumer_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--repos-only: consumer repo written; workspace-root pair not created."""
    from dadaia_workspace.features.workspace.service import WorkspaceService
    from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

    WorkspaceService(
        public_assets=_make_manager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)

    # Remove AGENTS.md from workspace root if it was written by init
    root_agents = tmp_path / "AGENTS.md"
    root_agents.unlink(missing_ok=True)

    consumer = _add_marker_consumer(tmp_path, "some-consumer")
    monkeypatch.chdir(tmp_path)

    result = _runner.invoke(app, ["public", "install", "--repos-only", "--force"])

    assert result.exit_code == 0, result.output
    # Workspace root AGENTS.md must still not exist (repos-only skips it)
    assert not root_agents.exists(), (
        "workspace-root AGENTS.md must NOT be created with --repos-only"
    )
    # Consumer pair must exist
    assert (consumer / "AGENTS.md").exists(), "consumer AGENTS.md must be written with --repos-only"
