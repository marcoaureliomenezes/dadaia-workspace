"""Unit tests for dadaia_workspace.features.agents.reader.

Coverage:
- Resolution branch 1: $DADAIA_AGENTS_DIR env var
- Resolution branch 2: .dadaia/agentic/agents/
- Resolution branch 3: .claude/agents/
- Allowlist enforcement: unknown frontmatter keys are dropped
- Malformed-frontmatter resilience: file is skipped, remainder parsed
"""

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.agents import AgentDTO, read_canonical_agents

_FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Resolution branch 1 — explicit $DADAIA_AGENTS_DIR env var
# ---------------------------------------------------------------------------


def test_env_var_branch_loads_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """When DADAIA_AGENTS_DIR points at the fixtures dir, agents are loaded."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=Path("/does/not/matter"))
    names = {a.id for a in agents}
    # malformed.md is skipped; software-engineer, frontend-engineer,
    # with-unknown-keys (backend-engineer name) must be present
    assert "software-engineer" in names
    assert "frontend-engineer" in names
    assert "backend-engineer" in names


def test_env_var_branch_skips_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed YAML frontmatter causes the file to be skipped, not raised."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=Path("/does/not/matter"))
    # The malformed.md file has name: malformed but bad YAML so it is skipped.
    # We should not see "malformed" in the resulting IDs.
    names = {a.id for a in agents}
    assert "malformed" not in names


def test_env_var_branch_supersedes_fallback_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When DADAIA_AGENTS_DIR is set, fallback dirs are ignored entirely."""
    # Place a sentinel agent under .dadaia/agentic/agents/ in a temp workspace
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "sentinel-agent.md").write_text(
        "---\nname: sentinel-agent\ndescription: should not appear\n---\n# Sentinel\n"
    )
    # But DADAIA_AGENTS_DIR points at fixtures — sentinel must NOT appear
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=tmp_path)
    names = {a.id for a in agents}
    assert "sentinel-agent" not in names


# ---------------------------------------------------------------------------
# Resolution branch 2 — .dadaia/agentic/agents/
# ---------------------------------------------------------------------------


def test_agentic_branch_loads_agents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When DADAIA_AGENTS_DIR is absent, .dadaia/agentic/agents/ is used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "alpha.md").write_text(
        "---\nname: alpha\ndescription: Alpha agent.\n---\n# Alpha\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    assert any(a.id == "alpha" for a in agents)


def test_agentic_branch_preferred_over_claude(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/agents/ exists and is non-empty, .claude/agents/ is not used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "alpha.md").write_text(
        "---\nname: alpha\ndescription: Alpha agent.\n---\n# Alpha\n"
    )
    # Place a competing agent in .claude/agents/
    claude_dir = tmp_path / ".claude" / "agents"
    claude_dir.mkdir(parents=True)
    (claude_dir / "beta.md").write_text(
        "---\nname: beta\ndescription: Beta agent.\n---\n# Beta\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    names = {a.id for a in agents}
    assert "alpha" in names
    assert "beta" not in names


# ---------------------------------------------------------------------------
# Resolution branch 3 — .claude/agents/
# ---------------------------------------------------------------------------


def test_claude_branch_used_when_agentic_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/agents/ does not exist, .claude/agents/ is used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    claude_dir = tmp_path / ".claude" / "agents"
    claude_dir.mkdir(parents=True)
    (claude_dir / "gamma.md").write_text(
        "---\nname: gamma\ndescription: Gamma agent.\n---\n# Gamma\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    assert any(a.id == "gamma" for a in agents)


def test_claude_branch_used_when_agentic_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/agents/ exists but is empty, .claude/agents/ is used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    # directory exists but has no .md files
    claude_dir = tmp_path / ".claude" / "agents"
    claude_dir.mkdir(parents=True)
    (claude_dir / "delta.md").write_text(
        "---\nname: delta\ndescription: Delta agent.\n---\n# Delta\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    assert any(a.id == "delta" for a in agents)


def test_returns_empty_list_when_no_dir_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Returns an empty list when no agent directory can be resolved."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    # neither .dadaia/agentic/agents/ nor .claude/agents/ exist
    agents = read_canonical_agents(workspace_root=tmp_path)
    assert agents == []


# ---------------------------------------------------------------------------
# Allowlist enforcement
# ---------------------------------------------------------------------------


def test_unknown_keys_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fields not in the allowlist are silently dropped; known fields are preserved."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=Path("/does/not/matter"))
    backend = next((a for a in agents if a.id == "backend-engineer"), None)
    assert backend is not None
    # unknown_field and another_unknown must NOT appear as attributes
    assert not hasattr(backend, "unknown_field")
    assert not hasattr(backend, "another_unknown")
    # known fields must be preserved
    assert backend.model == "claude-opus-4"
    assert backend.max_turns == 30


def test_known_fields_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """All AgentDTO fields from SPEC §5.1 are populated on a well-formed agent."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=Path("/does/not/matter"))
    se = next((a for a in agents if a.id == "software-engineer"), None)
    assert se is not None
    assert se.id == "software-engineer"
    assert se.name == "software-engineer"
    assert "Python" in se.description or "software engineer" in se.description.lower()
    assert isinstance(se.skills, list)
    assert isinstance(se.tools, list)
    assert se.model == "claude-sonnet-4-6"
    assert se.opencode_model is None  # not set in fixture
    assert se.max_turns == 60
    # input_contract may be a dict or None — must be present as attribute
    assert hasattr(se, "input_contract")


def test_optional_fields_default_to_none_or_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Optional AgentDTO fields default to None or empty list when absent."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    # Minimal agent: only name + description
    (agentic_dir / "minimal.md").write_text(
        "---\nname: minimal\ndescription: Minimal agent.\n---\n# Minimal\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    minimal = next((a for a in agents if a.id == "minimal"), None)
    assert minimal is not None
    assert minimal.skills == []
    assert minimal.tools == []
    assert minimal.model is None
    assert minimal.opencode_model is None
    assert minimal.max_turns is None
    assert minimal.input_contract is None


# ---------------------------------------------------------------------------
# Malformed-frontmatter resilience
# ---------------------------------------------------------------------------


def test_malformed_frontmatter_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """A file with malformed YAML is skipped; other files in the dir are still parsed."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=Path("/does/not/matter"))
    names = {a.id for a in agents}
    # malformed.md must be skipped
    assert "malformed" not in names
    # but the other fixtures must still load
    assert "software-engineer" in names


def test_missing_frontmatter_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A .md file with no frontmatter delimiters is skipped gracefully."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "no-frontmatter.md").write_text(
        "# No Frontmatter\n\nThis file has no YAML frontmatter.\n"
    )
    (agentic_dir / "valid.md").write_text(
        "---\nname: valid\ndescription: Valid agent.\n---\n# Valid\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    names = {a.id for a in agents}
    assert "no-frontmatter" not in names
    assert "valid" in names


def test_empty_frontmatter_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A .md file with empty/null frontmatter (just delimiters) is skipped."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "empty-fm.md").write_text("---\n---\n# Empty\n")
    (agentic_dir / "valid.md").write_text(
        "---\nname: valid\ndescription: Valid agent.\n---\n# Valid\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    names = {a.id for a in agents}
    assert "empty-fm" not in names
    assert "valid" in names


# ---------------------------------------------------------------------------
# AgentDTO type assertions
# ---------------------------------------------------------------------------


def test_agent_dto_is_dataclass_or_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    """AgentDTO is importable and instances have the expected field set."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=Path("/does/not/matter"))
    assert len(agents) > 0
    dto = agents[0]
    assert isinstance(dto, AgentDTO)
    required_fields = {"id", "name", "description", "skills", "tools",
                       "model", "opencode_model", "max_turns", "input_contract"}
    for field in required_fields:
        assert hasattr(dto, field), f"AgentDTO missing field: {field}"


def test_opencode_model_loaded_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """opencode_model field is populated when present in frontmatter."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=Path("/does/not/matter"))
    fe = next((a for a in agents if a.id == "frontend-engineer"), None)
    assert fe is not None
    assert fe.opencode_model == "claude-sonnet-4-6"
