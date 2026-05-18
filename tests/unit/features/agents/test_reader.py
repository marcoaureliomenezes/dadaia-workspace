"""Unit tests for dadaia_workspace.features.agents.reader.

Coverage:
- Resolution branch 1: $DADAIA_AGENTS_DIR env var
- Resolution branch 2: .dadaia/agentic/agents/
- Resolution branch 3: .claude/agents/
- Allowlist enforcement: unknown frontmatter keys are dropped
- Malformed-frontmatter resilience: file is skipped, remainder parsed
- _raw_to_dto edge cases: missing name, no description, bad maxTurns
- _strip_frontmatter edge cases: no delimiter, no closing delimiter
- get_prompt: happy path, invalid id (regex), invalid id (traversal),
  agent not found, no agents dir
"""

import os
from pathlib import Path

import pytest

from dadaia_workspace.features.agents import AgentDTO, read_canonical_agents
from dadaia_workspace.features.agents.reader import (
    AgentNotFoundError,
    InvalidAgentIdError,
    _strip_frontmatter,
    get_prompt,
)

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


# ---------------------------------------------------------------------------
# _raw_to_dto edge cases (lines 107-108, 112, 120-121)
# ---------------------------------------------------------------------------


def test_raw_to_dto_missing_name_returns_empty_agent_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Agent file with no 'name' field is skipped (returns None → not in list)."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    # File has description but no name
    (agentic_dir / "nameless.md").write_text(
        "---\ndescription: Agent without a name field.\n---\n# Nameless\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    names = {a.id for a in agents}
    assert "nameless" not in names


def test_raw_to_dto_empty_name_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Agent file with empty string name is skipped."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "empty-name.md").write_text(
        "---\nname: ''\ndescription: Empty name.\n---\n# Empty\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    assert all(a.id != "" for a in agents)


def test_raw_to_dto_missing_description_defaults_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When 'description' is absent, AgentDTO.description is empty string."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "no-desc.md").write_text(
        "---\nname: no-desc\n---\n# No description\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "no-desc"), None)
    assert agent is not None
    assert agent.description == ""


def test_raw_to_dto_bad_max_turns_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Non-integer maxTurns value is silently ignored; max_turns remains None."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "bad-turns.md").write_text(
        "---\nname: bad-turns\ndescription: Bad maxTurns.\nmaxTurns: 'not-a-number'\n---\n# Bad\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "bad-turns"), None)
    assert agent is not None
    assert agent.max_turns is None


def test_raw_to_dto_max_turns_snake_case(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """max_turns (snake_case) is accepted as a fallback when maxTurns absent."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "snake-turns.md").write_text(
        "---\nname: snake-turns\ndescription: Snake case turns.\nmax_turns: 42\n---\n# Snake\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "snake-turns"), None)
    assert agent is not None
    assert agent.max_turns == 42


def test_raw_to_dto_maxtturns_camelcase_priority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """maxTurns (camelCase) takes priority over max_turns when both are present."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "both-turns.md").write_text(
        "---\nname: both-turns\ndescription: Both maxTurns and max_turns.\nmaxTurns: 10\nmax_turns: 99\n---\n# Both\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "both-turns"), None)
    assert agent is not None
    assert agent.max_turns == 10  # camelCase takes priority


def test_raw_to_dto_non_dict_input_contract_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """input_contract that is not a dict is silently set to None."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "bad-contract.md").write_text(
        "---\nname: bad-contract\ndescription: Bad contract.\ninput_contract: just-a-string\n---\n# Bad\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "bad-contract"), None)
    assert agent is not None
    assert agent.input_contract is None


def test_raw_to_dto_unicode_emoji_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Agent with unicode/emoji in description is loaded without error."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "unicode-agent.md").write_text(
        "---\nname: unicode-agent\ndescription: '🤖 Agente com emoji e português'\n---\n# Unicode\n",
        encoding="utf-8",
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "unicode-agent"), None)
    assert agent is not None
    assert "🤖" in agent.description


# ---------------------------------------------------------------------------
# _strip_frontmatter edge cases (lines 182-191)
# ---------------------------------------------------------------------------


def test_strip_frontmatter_no_delimiter_returns_full_text() -> None:
    """Text with no '---' delimiter returns the full text stripped."""
    text = "# Just a body\n\nNo frontmatter here.\n"
    result = _strip_frontmatter(text)
    assert "No frontmatter here." in result


def test_strip_frontmatter_no_closing_delimiter_returns_text() -> None:
    """Text starting with '---' but no closing delimiter returns the full text."""
    text = "---\nname: broken\n# No closing delimiter\n"
    result = _strip_frontmatter(text)
    # Returns the stripped text (as-is, not None)
    assert isinstance(result, str)
    assert len(result) > 0


def test_strip_frontmatter_normal_returns_body_only() -> None:
    """Normal frontmatter: body after closing '---' is returned, stripped."""
    text = "---\nname: agent\n---\n\n# Body content\n"
    result = _strip_frontmatter(text)
    assert "# Body content" in result
    assert "name: agent" not in result


def test_strip_frontmatter_empty_body_returns_empty_string() -> None:
    """Frontmatter with no body after closing delimiter returns empty string."""
    text = "---\nname: agent\n---\n"
    result = _strip_frontmatter(text)
    assert result == ""


# ---------------------------------------------------------------------------
# get_prompt — happy path and error cases (lines 235-285)
# ---------------------------------------------------------------------------


def test_get_prompt_returns_body_and_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """get_prompt returns (body, path) for a valid agent in the fixtures dir."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "my-agent.md").write_text(
        "---\nname: my-agent\ndescription: Test agent.\n---\n\n# My Agent\n\nYou are my agent.\n"
    )
    body, path = get_prompt("my-agent", workspace_root=tmp_path)
    assert "# My Agent" in body
    assert path.name == "my-agent.md"


def test_get_prompt_invalid_id_regex_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Agent id failing regex validation raises InvalidAgentIdError."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    with pytest.raises(InvalidAgentIdError, match="does not match"):
        get_prompt("INVALID_ID!", workspace_root=tmp_path)


def test_get_prompt_uppercase_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Uppercase letters in agent_id fail the regex validation."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    with pytest.raises(InvalidAgentIdError):
        get_prompt("SoftwareEngineer", workspace_root=tmp_path)


def test_get_prompt_space_in_id_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Spaces in agent_id fail the regex validation."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    with pytest.raises(InvalidAgentIdError):
        get_prompt("software engineer", workspace_root=tmp_path)


def test_get_prompt_no_agents_dir_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When no agents directory can be resolved, AgentNotFoundError is raised."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    # No dirs under tmp_path
    with pytest.raises(AgentNotFoundError, match="No agents directory"):
        get_prompt("software-engineer", workspace_root=tmp_path)


def test_get_prompt_agent_not_found_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Valid id but no corresponding file raises AgentNotFoundError."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "other-agent.md").write_text(
        "---\nname: other-agent\ndescription: Other.\n---\n# Other\n"
    )
    with pytest.raises(AgentNotFoundError, match="No agent file found"):
        get_prompt("missing-agent", workspace_root=tmp_path)


def test_get_prompt_uses_env_var_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """get_prompt respects DADAIA_AGENTS_DIR env var for directory resolution."""
    custom_dir = tmp_path / "custom_agents"
    custom_dir.mkdir()
    (custom_dir / "se.md").write_text(
        "---\nname: se\ndescription: SE.\n---\n\n# SE prompt body.\n"
    )
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(custom_dir))
    body, path = get_prompt("se", workspace_root=tmp_path)
    assert "SE prompt body" in body


def test_get_prompt_strips_frontmatter_from_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """get_prompt body does not include the YAML frontmatter block."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "clean-agent.md").write_text(
        "---\nname: clean-agent\ndescription: Clean agent.\nmodel: gpt-4\n---\n\n# Clean Agent Body\n"
    )
    body, _ = get_prompt("clean-agent", workspace_root=tmp_path)
    assert "name: clean-agent" not in body
    assert "model: gpt-4" not in body
    assert "# Clean Agent Body" in body


def test_get_prompt_symlink_escape_raises_invalid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A symlink inside agents_dir that resolves outside the dir raises InvalidAgentIdError.

    This covers the defence-in-depth path traversal check (reader.py lines 258-268).
    """
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    # Target outside the agents dir
    outside = tmp_path / "outside.md"
    outside.write_text(
        "---\nname: escape-agent\ndescription: Outside agent.\n---\n# Escape\n"
    )
    # Symlink named "escape-agent.md" inside the dir, pointing outside
    link = agentic_dir / "escape-agent.md"
    link.symlink_to(outside)

    with pytest.raises(InvalidAgentIdError, match="[Pp]ath traversal"):
        get_prompt("escape-agent", workspace_root=tmp_path)


# ---------------------------------------------------------------------------
# AGT-32 — paths field (declarative, forward-compatible)
# ---------------------------------------------------------------------------


def test_paths_field_loaded_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When 'paths' frontmatter key is present its value is forwarded to AgentDTO.paths."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "pathed-agent.md").write_text(
        "---\nname: pathed-agent\ndescription: Agent with paths.\n"
        "paths:\n  write:\n    - repos/myrepo/src/\n  read:\n    - specs/\n"
        "---\n# Pathed\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "pathed-agent"), None)
    assert agent is not None
    assert agent.paths is not None
    assert "write" in agent.paths
    assert agent.paths["write"] == ["repos/myrepo/src/"]
    assert "read" in agent.paths
    assert agent.paths["read"] == ["specs/"]


def test_paths_field_defaults_to_none_when_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When 'paths' is absent from frontmatter, AgentDTO.paths defaults to None."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "no-paths.md").write_text(
        "---\nname: no-paths\ndescription: No paths field.\n---\n# NoPaths\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "no-paths"), None)
    assert agent is not None
    assert agent.paths is None


def test_paths_field_non_dict_defaults_to_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When 'paths' is not a dict (e.g. a plain string), AgentDTO.paths is None."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    (agentic_dir / "bad-paths.md").write_text(
        "---\nname: bad-paths\ndescription: Bad paths.\npaths: just-a-string\n---\n# BadPaths\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path)
    agent = next((a for a in agents if a.id == "bad-paths"), None)
    assert agent is not None
    assert agent.paths is None


def test_get_prompt_unreadable_file_raises_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A file that exists but cannot be read raises AgentNotFoundError (OSError path).

    This covers reader.py lines 279-280.
    """
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = tmp_path / ".dadaia" / "agentic" / "agents"
    agentic_dir.mkdir(parents=True)
    agent_file = agentic_dir / "locked-agent.md"
    agent_file.write_text(
        "---\nname: locked-agent\ndescription: Locked.\n---\n# Locked\n"
    )
    agent_file.chmod(0o000)
    try:
        with pytest.raises(AgentNotFoundError, match="Cannot read"):
            get_prompt("locked-agent", workspace_root=tmp_path)
    finally:
        agent_file.chmod(0o644)
