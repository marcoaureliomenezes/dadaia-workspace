"""Integration tests for public asset install projection flows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import PublicAssetError
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow(reason="public asset install writes projected workspace files"),
]


def _build_minimal_agentic_dir(tmp_path: Path) -> tuple[Path, Path]:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    agentic_dir.mkdir(parents=True)
    manifest = {
        "schema_version": "1",
        "package_version": "0.0.0-test",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "assets": [],
    }
    (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return agentic_dir, workspace_root


def _make_manager(public_dir: Path) -> FileSystemPublicAssetManager:
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001
    return manager


def _make_minimal_agentic(workspace_root: Path) -> Path:
    agentic_dir = workspace_root / ".dadaia" / "agentic"
    (agentic_dir / "rules").mkdir(parents=True)
    (agentic_dir / "agents").mkdir(parents=True)
    (agentic_dir / "skills").mkdir(parents=True)
    (agentic_dir / "workflows").mkdir(parents=True)
    (agentic_dir / "commands").mkdir(parents=True)
    (agentic_dir / "rules" / "my-rule.md").write_text("# rule", encoding="utf-8")
    (agentic_dir / "agents" / "my-agent.md").write_text(
        "---\nname: my-agent\nmodel: claude-sonnet-4-6\n---\n# body\n",
        encoding="utf-8",
    )
    manifest = {"schema_version": "1", "package_version": "0.0.1"}
    (agentic_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return agentic_dir


def test_legacy_path_uses_templates_agents_md(tmp_path: Path) -> None:
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    templates_dir = agentic_dir / "templates"
    templates_dir.mkdir()
    (templates_dir / "AGENTS.md").write_text("# TEMPLATES AGENTS\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(workspace_root, target="claude", force=True)

    assert (workspace_root / "AGENTS.md").exists()


def test_legacy_path_repos_only_skips_agents_md(tmp_path: Path) -> None:
    agentic_dir, workspace_root = _build_minimal_agentic_dir(tmp_path)
    templates_dir = agentic_dir / "templates"
    templates_dir.mkdir()
    (templates_dir / "AGENTS.md").write_text("# TEMPLATES AGENTS\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(
        workspace_root, target="claude", force=True, scope="repos-only"
    )

    assert not (workspace_root / "AGENTS.md").exists()


def test_invalid_target_raises_public_asset_error(tmp_path: Path) -> None:
    _, workspace_root = _build_minimal_agentic_dir(tmp_path)

    with pytest.raises(PublicAssetError, match="Unsupported"):
        FileSystemPublicAssetManager().install(workspace_root, target="invalid-target")


def test_install_only_rules_skips_agents(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    _make_minimal_agentic(workspace_root)
    manager = _make_manager(public_dir)

    installed = manager.install(workspace_root, target="claude", force=True, only="rules")

    installed_paths = " ".join(installed)
    assert "rules" in installed_paths or len(installed) == 0
    agents_dir = workspace_root / ".claude" / "agents"
    assert not agents_dir.exists() or list(agents_dir.iterdir()) == []


def test_install_only_agents_skips_rules(tmp_path: Path) -> None:
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    _make_minimal_agentic(workspace_root)
    manager = _make_manager(public_dir)

    manager.install(workspace_root, target="claude", force=True, only="agents")

    rules_dir = workspace_root / ".claude" / "rules"
    assert not rules_dir.exists() or list(rules_dir.iterdir()) == []
