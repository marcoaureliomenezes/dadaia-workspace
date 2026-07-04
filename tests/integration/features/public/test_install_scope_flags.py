"""Integration tests for scope flags on FileSystemPublicAssetManager.install().

Coverage:
- ``scope="all"`` (default): workspace-root pair AND consumer repos are installed.
- ``scope="workspace-only"``: workspace-root pair written; consumer repos skipped.
- ``scope="repos-only"``: consumer repos written; workspace-root pair skipped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = [pytest.mark.integration, pytest.mark.slow]

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

_CONSUMER_VERSION = "0.0.0"


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
    """Register a consumer repo under ``workspace_root/repos/`` via the registry (v0.1.58 FR4)."""
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


# -----------------------------------------------------------------------
# Integration tests — FileSystemPublicAssetManager.install() scope parameter
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
