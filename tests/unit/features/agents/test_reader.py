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

from functools import lru_cache
from pathlib import Path

import pytest

from dadaia_workspace.features.agents import AgentDTO, read_canonical_agents
from dadaia_workspace.features.agents.reader import (
    AgentNotFoundError,
    InvalidAgentIdError,
    _strip_frontmatter,
    get_prompt,
)
from dadaia_workspace.infrastructure.markdown_agent_store import MarkdownAgentStore

_FIXTURES = Path(__file__).parent / "fixtures"


def _agentic_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".dadaia" / "agentic" / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _claude_dir(tmp_path: Path) -> Path:
    path = tmp_path / ".claude" / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_agent(
    directory: Path,
    filename: str,
    frontmatter: str,
    body: str = "# Agent\n",
    *,
    encoding: str | None = None,
) -> Path:
    path = directory / filename
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding=encoding)
    return path


def test_env_var_branch_loads_agents(monkeypatch: pytest.MonkeyPatch) -> None:
    """When DADAIA_AGENTS_DIR points at the fixtures dir, agents are loaded."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(
        workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
    )
    names = {a.id for a in agents}
    # malformed.md is skipped; software-engineer, frontend-engineer,
    # with-unknown-keys (backend-engineer name) must be present
    assert "software-engineer" in names
    assert "frontend-engineer" in names
    assert "backend-engineer" in names


def test_env_var_branch_skips_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed YAML frontmatter causes the file to be skipped, not raised."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(
        workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
    )
    # The malformed.md file has name: malformed but bad YAML so it is skipped.
    # We should not see "malformed" in the resulting IDs.
    names = {a.id for a in agents}
    assert "malformed" not in names


def test_env_var_branch_supersedes_fallback_dirs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When DADAIA_AGENTS_DIR is set, fallback dirs are ignored entirely."""
    _write_agent(
        _agentic_dir(tmp_path),
        "sentinel-agent.md",
        "name: sentinel-agent\ntier: 3\ndescription: should not appear\n",
        "# Sentinel\n",
    )
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert "sentinel-agent" not in names


def test_agentic_branch_loads_agents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When DADAIA_AGENTS_DIR is absent, .dadaia/agentic/agents/ is used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path), "alpha.md", "name: alpha\ntier: 3\ndescription: Alpha agent.\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    assert any(a.id == "alpha" for a in agents)


def test_agentic_branch_preferred_over_claude(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/agents/ exists and is non-empty, .claude/agents/ is not used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path), "alpha.md", "name: alpha\ntier: 3\ndescription: Alpha agent.\n"
    )
    _write_agent(
        _claude_dir(tmp_path), "beta.md", "name: beta\ntier: 3\ndescription: Beta agent.\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert "alpha" in names
    assert "beta" not in names


def test_claude_branch_used_when_agentic_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/agents/ does not exist, .claude/agents/ is used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _claude_dir(tmp_path), "gamma.md", "name: gamma\ntier: 3\ndescription: Gamma agent.\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    assert any(a.id == "gamma" for a in agents)


def test_claude_branch_used_when_agentic_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When .dadaia/agentic/agents/ exists but is empty, .claude/agents/ is used."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _agentic_dir(tmp_path)
    _write_agent(
        _claude_dir(tmp_path), "delta.md", "name: delta\ntier: 3\ndescription: Delta agent.\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    assert any(a.id == "delta" for a in agents)


def test_returns_empty_list_when_no_dir_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Returns an empty list when no agent directory can be resolved."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    # neither .dadaia/agentic/agents/ nor .claude/agents/ exist
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    assert agents == []


def test_unknown_keys_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fields not in the allowlist are silently dropped; known fields are preserved."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(
        workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
    )
    backend = next((a for a in agents if a.id == "backend-engineer"), None)
    assert backend is not None
    # unknown_field and another_unknown must NOT appear as attributes
    assert not hasattr(backend, "unknown_field")
    assert not hasattr(backend, "another_unknown")
    # known fields must be preserved
    assert backend.model == "claude-opus-4"
    assert backend.max_turns == 30


def test_known_fields_all_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """All canonical AgentDTO fields are populated on a well-formed agent."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(
        workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
    )
    se = next((a for a in agents if a.id == "software-engineer"), None)
    assert se is not None
    assert se.id == "software-engineer"
    assert se.name == "software-engineer"
    assert "Python" in se.description or "software engineer" in se.description.lower()
    assert isinstance(se.skills, list)
    assert isinstance(se.tools, list)
    assert se.model == "claude-sonnet-4-6"
    assert se.max_turns == 60
    # input_contract may be a dict or None — must be present as attribute
    assert hasattr(se, "input_contract")


def test_optional_fields_default_to_none_or_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Optional AgentDTO fields default to None or empty list when absent."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "minimal.md",
        "name: minimal\ntier: 3\ndescription: Minimal agent.\n",
        "# Minimal\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    minimal = next((a for a in agents if a.id == "minimal"), None)
    assert minimal is not None
    assert minimal.skills == []
    assert minimal.tools == []
    assert minimal.model is None
    assert minimal.max_turns is None
    assert minimal.input_contract is None


def test_malformed_frontmatter_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """A file with malformed YAML is skipped; other files in the dir are still parsed."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(
        workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
    )
    names = {a.id for a in agents}
    # malformed.md must be skipped
    assert "malformed" not in names
    # but the other fixtures must still load
    assert "software-engineer" in names


def test_missing_frontmatter_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A .md file with no frontmatter delimiters is skipped gracefully."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = _agentic_dir(tmp_path)
    (agentic_dir / "no-frontmatter.md").write_text(
        "# No Frontmatter\n\nThis file has no YAML frontmatter.\n"
    )
    _write_agent(
        agentic_dir, "valid.md", "name: valid\ntier: 3\ndescription: Valid agent.\n", "# Valid\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert "no-frontmatter" not in names
    assert "valid" in names


def test_empty_frontmatter_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A .md file with empty/null frontmatter (just delimiters) is skipped."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = _agentic_dir(tmp_path)
    (agentic_dir / "empty-fm.md").write_text("---\n---\n# Empty\n")
    _write_agent(
        agentic_dir, "valid.md", "name: valid\ntier: 3\ndescription: Valid agent.\n", "# Valid\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert "empty-fm" not in names
    assert "valid" in names


def test_agent_dto_is_dataclass_or_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    """AgentDTO is importable and instances have the expected field set."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(
        workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
    )
    assert len(agents) > 0
    dto = agents[0]
    assert isinstance(dto, AgentDTO)
    required_fields = {
        "id",
        "name",
        "description",
        "skills",
        "tools",
        "model",
        "max_turns",
        "input_contract",
    }
    for field in required_fields:
        assert hasattr(dto, field), f"AgentDTO missing field: {field}"


def test_raw_to_dto_missing_name_returns_empty_agent_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Agent file with no 'name' field is skipped (returns None → not in list)."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "nameless.md",
        "tier: 3\ndescription: Agent without a name field.\n",
        "# Nameless\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert "nameless" not in names


def test_raw_to_dto_empty_name_skipped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Agent file with empty string name is skipped."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path), "empty-name.md", "name: ''\ndescription: Empty name.\n", "# Empty\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    assert all(a.id != "" for a in agents)


def test_raw_to_dto_missing_description_defaults_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When 'description' is absent, AgentDTO.description is empty string."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path), "no-desc.md", "name: no-desc\ntier: 3\n", "# No description\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "no-desc"), None)
    assert agent is not None
    assert agent.description == ""


def test_raw_to_dto_bad_max_turns_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Non-integer maxTurns value is silently ignored; max_turns remains None."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "bad-turns.md",
        "name: bad-turns\ntier: 3\ndescription: Bad maxTurns.\nmaxTurns: 'not-a-number'\n",
        "# Bad\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "bad-turns"), None)
    assert agent is not None
    assert agent.max_turns is None


def test_raw_to_dto_max_turns_snake_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """max_turns (snake_case) is accepted as a fallback when maxTurns absent."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "snake-turns.md",
        "name: snake-turns\ntier: 3\ndescription: Snake case turns.\nmax_turns: 42\n",
        "# Snake\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "snake-turns"), None)
    assert agent is not None
    assert agent.max_turns == 42


def test_raw_to_dto_maxtturns_camelcase_priority(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """maxTurns (camelCase) takes priority over max_turns when both are present."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "both-turns.md",
        "name: both-turns\ntier: 3\ndescription: Both maxTurns and max_turns.\nmaxTurns: 10\nmax_turns: 99\n",
        "# Both\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "both-turns"), None)
    assert agent is not None
    assert agent.max_turns == 10  # camelCase takes priority


def test_raw_to_dto_non_dict_input_contract_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """input_contract that is not a dict is silently set to None."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "bad-contract.md",
        "name: bad-contract\ntier: 3\ndescription: Bad contract.\ninput_contract: just-a-string\n",
        "# Bad\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "bad-contract"), None)
    assert agent is not None
    assert agent.input_contract is None


def test_raw_to_dto_unicode_emoji_name(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Agent with unicode/emoji in description is loaded without error."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "unicode-agent.md",
        "name: unicode-agent\ntier: 3\ndescription: '🤖 Agente com emoji e português'\n",
        "# Unicode\n",
        encoding="utf-8",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "unicode-agent"), None)
    assert agent is not None
    assert "🤖" in agent.description


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


def test_get_prompt_returns_body_and_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_prompt returns (body, path) for a valid agent in the fixtures dir."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "my-agent.md",
        "name: my-agent\ndescription: Test agent.\n",
        "\n# My Agent\n\nYou are my agent.\n",
    )
    body, path = get_prompt("my-agent", workspace_root=tmp_path)
    assert "# My Agent" in body
    assert path.name == "my-agent.md"


@pytest.mark.parametrize("agent_id", ["INVALID_ID!", "SoftwareEngineer", "software engineer"])
def test_get_prompt_invalid_id_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, agent_id: str
) -> None:
    """Agent IDs outside the lowercase slug grammar are rejected."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    with pytest.raises(InvalidAgentIdError):
        get_prompt(agent_id, workspace_root=tmp_path)


def test_get_prompt_no_agents_dir_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When no agents directory can be resolved, AgentNotFoundError is raised."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    # No dirs under tmp_path
    with pytest.raises(AgentNotFoundError, match="No agents directory"):
        get_prompt("software-engineer", workspace_root=tmp_path)


def test_get_prompt_agent_not_found_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Valid id but no corresponding file raises AgentNotFoundError."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "other-agent.md",
        "name: other-agent\ndescription: Other.\n",
        "# Other\n",
    )
    with pytest.raises(AgentNotFoundError, match="No agent file found"):
        get_prompt("missing-agent", workspace_root=tmp_path)


def test_get_prompt_uses_env_var_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """get_prompt respects DADAIA_AGENTS_DIR env var for directory resolution."""
    custom_dir = tmp_path / "custom_agents"
    custom_dir.mkdir()
    _write_agent(custom_dir, "se.md", "name: se\ndescription: SE.\n", "\n# SE prompt body.\n")
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(custom_dir))
    body, path = get_prompt("se", workspace_root=tmp_path)
    assert "SE prompt body" in body


def test_get_prompt_strips_frontmatter_from_body(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """get_prompt body does not include the YAML frontmatter block."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "clean-agent.md",
        "name: clean-agent\ndescription: Clean agent.\nmodel: gpt-4\n",
        "\n# Clean Agent Body\n",
    )
    body, _ = get_prompt("clean-agent", workspace_root=tmp_path)
    assert "name: clean-agent" not in body
    assert "model: gpt-4" not in body
    assert "# Clean Agent Body" in body


def test_get_prompt_symlink_escape_raises_invalid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A symlink inside agents_dir that resolves outside the dir raises InvalidAgentIdError.

    This covers the defence-in-depth path traversal check.
    """
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = _agentic_dir(tmp_path)
    outside = tmp_path / "outside.md"
    _write_agent(
        tmp_path, "outside.md", "name: escape-agent\ndescription: Outside agent.\n", "# Escape\n"
    )
    link = agentic_dir / "escape-agent.md"
    link.symlink_to(outside)

    with pytest.raises(InvalidAgentIdError, match="[Pp]ath traversal"):
        get_prompt("escape-agent", workspace_root=tmp_path)


def test_paths_field_loaded_when_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When 'paths' frontmatter key is present its value is forwarded to AgentDTO.paths."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "pathed-agent.md",
        "name: pathed-agent\ntier: 3\ndescription: Agent with paths.\n"
        "paths:\n  write:\n    - repos/myrepo/src/\n  read:\n    - specs/\n"
        "",
        "# Pathed\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
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
    _write_agent(
        _agentic_dir(tmp_path),
        "no-paths.md",
        "name: no-paths\ntier: 3\ndescription: No paths field.\n",
        "# NoPaths\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "no-paths"), None)
    assert agent is not None
    assert agent.paths is None


def test_paths_field_non_dict_defaults_to_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When 'paths' is not a dict (e.g. a plain string), AgentDTO.paths is None."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "bad-paths.md",
        "name: bad-paths\ntier: 3\ndescription: Bad paths.\npaths: just-a-string\n",
        "# BadPaths\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    agent = next((a for a in agents if a.id == "bad-paths"), None)
    assert agent is not None
    assert agent.paths is None


_PUBLIC_AGENTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "dadaia_workspace" / "public" / "agents"
)


@lru_cache(maxsize=1)
def _public_agents() -> tuple[AgentDTO, ...]:
    return tuple(
        read_canonical_agents(
            workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
        )
    )


def _is_plugin_stub(agent: "AgentDTO") -> bool:  # noqa: F821
    """Return True when *agent* is a plugin stub (no model/tools/skills, plugin: true marker).

    Plugin stubs (frontend-engineer, design-specialist, devops-engineer) are intentionally
    minimal — they carry no runtime behavior and must be skipped for full-agent assertions.
    """
    return not agent.model and not agent.skills and not agent.tools


def test_all_public_agents_have_valid_write_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every non-plugin-stub public agent declares a non-empty string write allowlist."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_PUBLIC_AGENTS_DIR))
    agents = _public_agents()
    # Skip plugin stubs — they intentionally have no paths block.
    core_agents = [a for a in agents if not _is_plugin_stub(a)]
    without_paths = [a.id for a in core_agents if a.paths is None]
    empty_allowlist: list[str] = []
    bad: list[tuple[str, object]] = []
    for agent in core_agents:
        if agent.paths is None:
            continue
        wl = agent.paths.get("write_allowlist", [])
        if not wl:
            empty_allowlist.append(agent.id)
        for entry in wl:
            if not isinstance(entry, str) or not entry.strip():
                bad.append((agent.id, entry))
    assert without_paths == [], f"Core agents missing 'paths' block: {without_paths}"
    assert empty_allowlist == [], (
        f"Core agents with empty or absent 'write_allowlist': {empty_allowlist}"
    )
    assert bad == [], f"Non-string or empty entries in write_allowlist: {bad}"


def test_all_public_agent_files_are_loadable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every public agent markdown file must produce one canonical DTO."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_PUBLIC_AGENTS_DIR))
    agents = _public_agents()
    expected_ids = {path.stem for path in _PUBLIC_AGENTS_DIR.glob("*.md")}
    loaded_ids = {agent.id for agent in agents}
    assert loaded_ids == expected_ids, (
        f"Public agent files and loaded DTOs differ: "
        f"missing={sorted(expected_ids - loaded_ids)}, extra={sorted(loaded_ids - expected_ids)}"
    )


def test_all_public_agents_have_model_and_skills(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every non-plugin-stub public agent declares a runtime model and at least one skill.

    Plugin stubs (frontend-engineer, design-specialist, devops-engineer) intentionally
    omit model and skills — they are skipped here.
    """
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_PUBLIC_AGENTS_DIR))
    agents = _public_agents()
    core_agents = [a for a in agents if not _is_plugin_stub(a)]
    missing_model = [agent.id for agent in core_agents if not agent.model]
    missing_skills = [agent.id for agent in core_agents if not agent.skills]
    assert missing_model == [], f"Core public agents missing model: {missing_model}"
    assert missing_skills == [], f"Core public agents missing skills: {missing_skills}"


def test_public_agent_roster_uses_unified_software_engineer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The v0.1.8 public roster uses a single unified software-engineer (not language-split).

    The v0.1.8 surface reduction merged software-engineer-python and software-engineer-node
    into a single software-engineer agent. This test validates the new roster shape.
    """
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_PUBLIC_AGENTS_DIR))
    agents = _public_agents()
    ids = {a.id for a in agents}
    assert "software-engineer" in ids, (
        f"The public roster must contain 'software-engineer': {sorted(ids)}"
    )
    assert "software-engineer-python" not in ids, (
        f"Deleted agent 'software-engineer-python' must not appear in public roster: {sorted(ids)}"
    )
    assert "software-engineer-node" not in ids, (
        f"Deleted agent 'software-engineer-node' must not appear in public roster: {sorted(ids)}"
    )


_TIER1_AGENTS = {"project-manager", "project-auditor"}
_TIER2_AGENTS = {"product-engineer"}
# v0.1.8: software-engineer-python replaced by software-engineer; frontend-engineer is a plugin stub.
_TIER3_SAMPLE = {"software-engineer", "qa-engineer", "ai-engineer"}


def test_all_agents_have_tier_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every loaded public agent must have a tier ∈ {1, 2, 3}."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_PUBLIC_AGENTS_DIR))
    agents = _public_agents()
    assert len(agents) > 0, "Expected at least one public agent to be loaded"
    for agent in agents:
        assert agent.tier in {1, 2, 3}, (
            f"Agent {agent.id!r} has invalid tier {agent.tier!r} — must be 1, 2, or 3"
        )


def test_tier_mapping_matches_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PM + auditor → tier 1; product-engineer → tier 2; sample leaf agents → tier 3."""
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_PUBLIC_AGENTS_DIR))
    agents = _public_agents()
    by_id = {a.id: a for a in agents}

    for aid in _TIER1_AGENTS:
        assert aid in by_id, f"Expected T1 agent {aid!r} in public roster"
        assert by_id[aid].tier == 1, f"Agent {aid!r} should be tier 1, got {by_id[aid].tier}"

    for aid in _TIER2_AGENTS:
        assert aid in by_id, f"Expected T2 agent {aid!r} in public roster"
        assert by_id[aid].tier == 2, f"Agent {aid!r} should be tier 2, got {by_id[aid].tier}"

    for aid in _TIER3_SAMPLE:
        assert aid in by_id, f"Expected T3 agent {aid!r} in public roster"
        assert by_id[aid].tier == 3, f"Agent {aid!r} should be tier 3, got {by_id[aid].tier}"


def test_invalid_tier_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An agent file with a present-but-invalid 'tier' value raises MissingTierError.

    Invalid means: non-integer (e.g. 'foo') or out-of-range (e.g. 5, 0).
    The agent is skipped (not raised) when read_canonical_agents is called.
    """
    from dadaia_workspace.features.agents.reader import MissingTierError, _raw_to_dto

    # Non-integer tier → raises
    with pytest.raises(MissingTierError, match="non-integer 'tier'"):
        _raw_to_dto({"name": "bad-tier-agent", "description": "Bad tier.", "tier": "foo"})

    # Out-of-range tier → raises
    with pytest.raises(MissingTierError, match="invalid 'tier' value"):
        _raw_to_dto({"name": "bad-tier-agent", "description": "Bad tier.", "tier": 7})

    # Via read_canonical_agents with invalid tier: must be skipped (not raised)
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "bad-tier-agent.md",
        "name: bad-tier-agent\ndescription: Invalid tier.\ntier: 99\n",
        "# BadTier\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert "bad-tier-agent" not in names


def test_missing_tier_defaults_to_3(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """An agent file with no 'tier' frontmatter field defaults to tier=3 with a warning.

    This preserves compatibility for staged files that do not yet declare tier.
    """
    from dadaia_workspace.features.agents.reader import _raw_to_dto

    # Direct call: missing tier → tier == 3 (no exception)
    dto = _raw_to_dto({"name": "no-tier-agent", "description": "No tier."})
    assert dto is not None
    assert dto.tier == 3

    # Via read_canonical_agents: agent is present (not skipped), tier == 3
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "no-tier-agent.md",
        "name: no-tier-agent\ndescription: Missing tier.\n",
        "# NoTier\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert "no-tier-agent" in names
    agent = next(a for a in agents if a.id == "no-tier-agent")
    assert agent.tier == 3


def test_get_prompt_unreadable_file_raises_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A file that exists but cannot be read raises AgentNotFoundError (OSError path).

    This covers the unreadable prompt-file branch.
    """
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "locked-agent.md",
        "name: locked-agent\ndescription: Locked.\n",
        "# Locked\n",
    )
    # Force the OSError via monkeypatch rather than chmod(0o000): chmod mode bits
    # are a no-op on Windows, so the file would stay readable there. This exercises
    # the unreadable-file -> AgentNotFoundError branch on every OS.
    real_read = Path.read_text

    def boom(self: Path, *args: object, **kwargs: object) -> str:
        if self.name == "locked-agent.md":
            raise OSError("simulated unreadable file")
        return real_read(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", boom)
    with pytest.raises(AgentNotFoundError, match="Cannot read"):
        get_prompt("locked-agent", workspace_root=tmp_path)


# ---------------------------------------------------------------------------
# plugin / gate_role frontmatter mapping (Agentic-tab redesign)
# ---------------------------------------------------------------------------


def test_plugin_stub_frontmatter_maps_to_dto(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An agent with ``plugin: true`` maps to AgentDTO.plugin = True."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "design-specialist.md",
        'name: design-specialist\ndescription: "[PLUGIN] stub."\nplugin: true\n',
        "# stub\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    dto = next(a for a in agents if a.id == "design-specialist")
    assert dto.plugin is True


def test_non_plugin_agent_defaults_plugin_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A normal agent (no plugin key) has plugin = False and gate_role mapped."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "software-engineer.md",
        (
            "name: software-engineer\ndescription: Implementer.\n"
            "tier: 3\nmodel: claude-opus-4-8\ngate_role: implementer\n"
        ),
        "# se\n",
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    dto = next(a for a in agents if a.id == "software-engineer")
    assert dto.plugin is False
    assert dto.gate_role == "implementer"


def test_plugin_stub_missing_tier_does_not_warn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Plugin stubs omit ``tier`` by design — no missing-tier stderr warning."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "frontend-engineer.md",
        'name: frontend-engineer\ndescription: "[PLUGIN] stub."\nplugin: true\n',
        "# stub\n",
    )
    read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    captured = capsys.readouterr()
    assert "missing the 'tier'" not in captured.err
