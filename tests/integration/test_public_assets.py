"""Integration tests for FileSystemPublicAssetManager — full pipeline stage + install."""

import tomllib
from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

_AGENT_A_CONTENT = """\
---
name: agent-a
description: First fixture agent for integration testing.
model: claude-sonnet-4-5
---
# Agent A

Does fixture things.
"""

_AGENT_B_CONTENT = """\
---
name: agent-b
description: Second fixture agent for integration testing.
model: claude-haiku-3-5
tools:
  - Read
  - Edit
---
# Agent B

Does more fixture things.
"""


def test_install_codex_writes_agents_blocks_for_fixture_agents(tmp_path: Path) -> None:
    """T-PB-1 integration — stage + install(target=codex) writes [agents.*] blocks
    to .codex/config.toml for each fixture agent declared in the public agents dir.

    Verifies:
    (a) .codex/config.toml is created
    (b) it parses cleanly as valid TOML (tomllib.loads does not raise)
    (c) [agents."agent-a"] block is present
    (d) [agents."agent-b"] block is present
    (e) no .tmp file is left behind (ADR-ENG-6 atomic write smoke)
    """
    # Arrange: create a minimal public/agents/ directory in tmp_path
    public_agents_dir = tmp_path / "agents"
    public_agents_dir.mkdir(parents=True)
    (public_agents_dir / "agent-a.md").write_text(_AGENT_A_CONTENT, encoding="utf-8")
    (public_agents_dir / "agent-b.md").write_text(_AGENT_B_CONTENT, encoding="utf-8")

    # Create a minimal public/ structure the manager expects
    public_dir = tmp_path / "public"
    public_dir.mkdir()
    (public_dir / "agents").symlink_to(public_agents_dir)

    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Point the manager's _public_dir at our fixture public directory
    manager = FileSystemPublicAssetManager()
    manager._public_dir = public_dir  # noqa: SLF001

    # Act: stage then install codex
    manager.stage(workspace_root)
    manager.install(workspace_root, target="codex", force=True)

    # Assert (a): config.toml exists
    config_path = workspace_root / ".codex" / "config.toml"
    assert config_path.exists(), f"Expected .codex/config.toml to exist at {config_path}"

    # Assert (b): valid TOML — tomllib.loads must not raise
    content = config_path.read_text(encoding="utf-8")
    parsed = tomllib.loads(content)

    # Assert (c) and (d): both fixture agent blocks present
    agents = parsed.get("agents", {})
    assert "agent-a" in agents, (
        f"Expected [agents.\"agent-a\"] in config.toml; found agents: {list(agents.keys())}"
    )
    assert "agent-b" in agents, (
        f"Expected [agents.\"agent-b\"] in config.toml; found agents: {list(agents.keys())}"
    )

    # Assert (e): no leftover .tmp file (atomic write smoke)
    tmp_files = list(config_path.parent.glob("*.tmp"))
    assert not tmp_files, f"Stale .tmp files found after install: {tmp_files}"
