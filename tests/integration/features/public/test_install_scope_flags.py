"""Integration tests for scope flags on FileSystemPublicAssetManager.install().

Merged per plan-integration.md (7 -> 2):
  1. scope='all'/default: workspace-root pair AND consumer repos installed.
  2. workspace-only (multi-consumer skip) + repos-only (root untouched/not created,
     empty-consumers list).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = [pytest.mark.integration, pytest.mark.slow]

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


def test_scope_all_and_default_install_workspace_root_and_consumer_repos(
    tmp_path: Path,
) -> None:
    """scope='all' (default, and the implicit no-scope case) installs both root + consumers."""
    manager = FileSystemPublicAssetManager()
    consumer = _add_marker_consumer(tmp_path, "test-repo")

    manager.install(tmp_path, scope="all", force=True)
    assert (tmp_path / "AGENTS.md").exists(), "workspace-root AGENTS.md must be written"
    assert (tmp_path / "CLAUDE.md").exists(), "workspace-root CLAUDE.md must be written"
    assert (consumer / "AGENTS.md").exists(), "consumer AGENTS.md must be written (scope=all)"
    assert (consumer / "CLAUDE.md").exists(), "consumer CLAUDE.md must be written (scope=all)"

    # Calling install() without scope= behaves identically to scope='all'.
    manager2 = FileSystemPublicAssetManager()
    consumer2_root = tmp_path / "default-case"
    consumer2_root.mkdir()
    consumer2 = _add_marker_consumer(consumer2_root, "test-repo")
    manager2.install(consumer2_root, force=True)
    assert (consumer2_root / "AGENTS.md").exists()
    assert (consumer2 / "AGENTS.md").exists()


def test_scope_workspace_only_and_repos_only(tmp_path: Path) -> None:
    """workspace-only skips all consumers (even multiple); repos-only never touches/creates
    the workspace-root pair and returns an empty installed list with no consumers present."""
    manager = FileSystemPublicAssetManager()
    consumer_a = _add_marker_consumer(tmp_path, "repo-a")
    consumer_b = _add_marker_consumer(tmp_path, "repo-b")

    manager.install(tmp_path, scope="workspace-only", force=True)
    assert (tmp_path / "AGENTS.md").exists(), "workspace root must be written"
    assert (tmp_path / "CLAUDE.md").exists(), (
        "workspace-root CLAUDE.md must be written with scope=workspace-only"
    )
    assert not (consumer_a / "AGENTS.md").exists(), "repo-a must not be written"
    assert not (consumer_b / "AGENTS.md").exists(), "repo-b must not be written"

    # repos-only: pre-existing root AGENTS.md is not overwritten.
    repos_only_root = tmp_path / "repos-only-case"
    repos_only_root.mkdir()
    consumer = _add_marker_consumer(repos_only_root, "test-repo")
    root_agents = repos_only_root / "AGENTS.md"
    original_root_content = "# ORIGINAL root AGENTS.md — must not be overwritten\n"
    root_agents.write_text(original_root_content, encoding="utf-8")

    manager_repos_only = FileSystemPublicAssetManager()
    manager_repos_only.install(repos_only_root, scope="repos-only", force=True)
    assert root_agents.read_text(encoding="utf-8") == original_root_content, (
        "workspace-root AGENTS.md must NOT be overwritten with scope=repos-only"
    )
    assert (consumer / "AGENTS.md").exists(), (
        "consumer AGENTS.md must be written with scope=repos-only"
    )
    assert (consumer / "CLAUDE.md").exists(), (
        "consumer CLAUDE.md must be written with scope=repos-only"
    )

    # repos-only: no root AGENTS.md is created if absent.
    repos_only_no_root = tmp_path / "repos-only-no-root"
    repos_only_no_root.mkdir()
    _add_marker_consumer(repos_only_no_root, "test-repo")
    no_root_agents = repos_only_no_root / "AGENTS.md"
    assert not no_root_agents.exists()
    FileSystemPublicAssetManager().install(repos_only_no_root, scope="repos-only", force=True)
    assert not no_root_agents.exists(), (
        "workspace-root AGENTS.md must NOT be created with scope=repos-only"
    )

    # repos-only with zero consumer repos: installed list excludes root-pair entries.
    empty_root = tmp_path / "repos-only-empty"
    empty_root.mkdir()
    installed = FileSystemPublicAssetManager().install(empty_root, scope="repos-only", force=True)
    root_agents_path = str(empty_root / "AGENTS.md")
    root_claude_path = str(empty_root / "CLAUDE.md")
    paths_installed = [e.split(None, 1)[-1] for e in installed]
    assert root_agents_path not in paths_installed
    assert root_claude_path not in paths_installed
