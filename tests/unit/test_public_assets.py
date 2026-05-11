"""Unit tests for public asset staging and runtime projections."""

import json
from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager


def test_stage_creates_agentic_manifest(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.stage(workspace)

    manifest_path = workspace / ".dadaia" / "agentic" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "1"
    assert any(asset["path"] == "data/AGENTS.md" for asset in manifest["assets"])


def test_install_all_projects_runtime_assets(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()

    manager.install(workspace, target="all")

    assert (workspace / "AGENTS.md").exists()
    assert (workspace / ".agents" / "skills" / "dadaia-grill-me" / "SKILL.md").exists()
    assert (workspace / ".claude" / "agents" / "software-architect.md").exists()
    assert (workspace / ".codex" / "hooks.json").exists()
    assert (workspace / ".codex" / "config.toml").exists()
    assert (workspace / ".codex" / "rules" / "dadaia-workspace-dev-guardrail.md").exists()
    assert (workspace / ".opencode" / "commands" / "spec-context.md").exists()
    assert (workspace / "opencode.json").exists()


def test_install_preserves_existing_files_without_force(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(workspace, target="all")

    assert agents_md.read_text(encoding="utf-8") == "custom\n"


def test_install_overwrites_existing_files_with_force(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    agents_md = workspace / "AGENTS.md"
    agents_md.parent.mkdir(parents=True, exist_ok=True)
    agents_md.write_text("custom\n", encoding="utf-8")

    FileSystemPublicAssetManager().install(workspace, target="all", force=True)

    assert agents_md.read_text(encoding="utf-8").startswith("# dadaia Labs")


def test_doctor_reports_drift_and_unsupported(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    manager = FileSystemPublicAssetManager()
    manager.install(workspace, target="all")
    (workspace / "AGENTS.md").write_text("drift\n", encoding="utf-8")

    report = manager.doctor(workspace)

    assert "[drift] root:AGENTS.md" in report
    assert "[unsupported] codex:agents" in report
    assert "[unsupported] opencode:hooks" in report
