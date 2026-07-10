"""Unit tests for dadaia_workspace.features.agents.reader.

Coverage (post v0.1.75 rearchitecture — decision-table consolidation):
- Directory resolution precedence (env > agentic > claude > none) — 1 param table.
- Malformed/missing/empty-frontmatter skip behavior — 1 param table.
- ``_raw_to_dto`` edge handling incl. unknown-keys allowlist and dispatch_band
  resolution — 1 param table.
- ``get_prompt`` error cases (invalid id, no agents dir, agent not found) — 1 param table.
- ``get_prompt`` happy path: body extraction + frontmatter-strip (kept verbatim).
- ``get_prompt`` symlink-escape defence-in-depth (security, kept verbatim).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.agents import AgentDTO, read_canonical_agents
from dadaia_workspace.features.agents.reader import (
    AgentNotFoundError,
    InvalidAgentIdError,
    MissingDispatchBandError,
    _raw_to_dto,
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


# ---------------------------------------------------------------------------
# Directory resolution precedence: env > agentic > claude > none
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("case", "setup", "use_env_fixtures", "expect_present", "expect_absent"),
    [
        pytest.param(
            "env-supersedes-fallback",
            lambda tmp_path: _write_agent(
                _agentic_dir(tmp_path),
                "sentinel-agent.md",
                "name: sentinel-agent\ntier: 3\ndescription: should not appear\n",
            ),
            True,
            "software-engineer",
            "sentinel-agent",
            id="env-supersedes-fallback",
        ),
        pytest.param(
            "agentic-branch",
            lambda tmp_path: _write_agent(
                _agentic_dir(tmp_path),
                "alpha.md",
                "name: alpha\ntier: 3\ndescription: Alpha agent.\n",
            ),
            False,
            "alpha",
            None,
            id="agentic-branch-loads",
        ),
        pytest.param(
            "agentic-preferred-over-claude",
            lambda tmp_path: (
                _write_agent(
                    _agentic_dir(tmp_path), "alpha.md", "name: alpha\ntier: 3\ndescription: A.\n"
                ),
                _write_agent(
                    _claude_dir(tmp_path), "beta.md", "name: beta\ntier: 3\ndescription: B.\n"
                ),
            ),
            False,
            "alpha",
            "beta",
            id="agentic-preferred-over-claude",
        ),
        pytest.param(
            "claude-used-when-agentic-missing",
            lambda tmp_path: _write_agent(
                _claude_dir(tmp_path), "gamma.md", "name: gamma\ntier: 3\ndescription: G.\n"
            ),
            False,
            "gamma",
            None,
            id="claude-used-when-agentic-missing",
        ),
        pytest.param(
            "claude-used-when-agentic-empty",
            lambda tmp_path: (
                _agentic_dir(tmp_path),
                _write_agent(
                    _claude_dir(tmp_path), "delta.md", "name: delta\ntier: 3\ndescription: D.\n"
                ),
            ),
            False,
            "delta",
            None,
            id="claude-used-when-agentic-empty",
        ),
        pytest.param(
            "no-dirs-returns-empty",
            lambda tmp_path: None,
            False,
            None,
            None,
            id="no-dirs-found-returns-empty",
        ),
    ],
)
def test_dir_resolution_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
    setup: Any,
    use_env_fixtures: bool,
    expect_present: str | None,
    expect_absent: str | None,
) -> None:
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    setup(tmp_path)
    if use_env_fixtures:
        monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_FIXTURES))
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    if case == "no-dirs-returns-empty":
        assert agents == []
    if expect_present is not None:
        assert expect_present in names
    if expect_absent is not None:
        assert expect_absent not in names


# ---------------------------------------------------------------------------
# Malformed / missing / empty frontmatter — skip-file resilience
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("build_bad_file", "bad_id"),
    [
        pytest.param(
            lambda d: _write_agent(
                d,
                "malformed.md",
                "name: malformed\n  bad: [unterminated\n",
            ),
            "malformed",
            id="malformed-yaml",
        ),
        pytest.param(
            lambda d: (d / "no-frontmatter.md").write_text(
                "# No Frontmatter\n\nThis file has no YAML frontmatter.\n"
            ),
            "no-frontmatter",
            id="missing-frontmatter-delimiters",
        ),
        pytest.param(
            lambda d: (d / "empty-fm.md").write_text("---\n---\n# Empty\n"),
            "empty-fm",
            id="empty-frontmatter",
        ),
    ],
)
def test_skip_bad_frontmatter_file_others_still_load(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, build_bad_file: Any, bad_id: str
) -> None:
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    agentic_dir = _agentic_dir(tmp_path)
    build_bad_file(agentic_dir)
    _write_agent(
        agentic_dir, "valid.md", "name: valid\ntier: 3\ndescription: Valid agent.\n", "# Valid\n"
    )
    agents = read_canonical_agents(workspace_root=tmp_path, store_factory=MarkdownAgentStore)
    names = {a.id for a in agents}
    assert bad_id not in names
    assert "valid" in names


# ---------------------------------------------------------------------------
# _raw_to_dto edge handling incl. unknown-keys allowlist + dispatch_band
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "assert_fn"),
    [
        pytest.param(
            {"tier": 3, "description": "no name"},
            lambda dto: dto is None,
            id="missing-name-skipped",
        ),
        pytest.param(
            {"name": "", "description": "empty name"},
            lambda dto: dto is None or dto.id == "",
            id="empty-name-not-a-real-agent",
        ),
        pytest.param(
            {"name": "no-desc", "dispatch_band": 3},
            lambda dto: dto is not None and dto.description == "",
            id="missing-description-defaults-empty",
        ),
        pytest.param(
            {"name": "bad-turns", "dispatch_band": 3, "maxTurns": "not-a-number"},
            lambda dto: dto is not None and dto.max_turns is None,
            id="bad-max-turns-ignored",
        ),
        pytest.param(
            {"name": "snake-turns", "dispatch_band": 3, "max_turns": 42},
            lambda dto: dto is not None and dto.max_turns == 42,
            id="max-turns-snake-case-fallback",
        ),
        pytest.param(
            {"name": "both-turns", "dispatch_band": 3, "maxTurns": 10, "max_turns": 99},
            lambda dto: dto is not None and dto.max_turns == 10,
            id="max-turns-camelcase-priority",
        ),
        pytest.param(
            {"name": "bad-contract", "dispatch_band": 3, "input_contract": "just-a-string"},
            lambda dto: dto is not None and dto.input_contract is None,
            id="non-dict-input-contract-ignored",
        ),
        pytest.param(
            {
                "name": "backend-engineer",
                "dispatch_band": 3,
                "description": "Backend.",
                "model": "claude-opus-4",
                "max_turns": 30,
                "unknown_field": "drop-me",
                "another_unknown": 123,
            },
            lambda dto: (
                dto is not None
                and not hasattr(dto, "unknown_field")
                and not hasattr(dto, "another_unknown")
                and dto.model == "claude-opus-4"
                and dto.max_turns == 30
            ),
            id="unknown-keys-dropped-known-preserved",
        ),
        pytest.param(
            {"name": "unicode-agent", "dispatch_band": 3, "description": "🤖 Agente português"},
            lambda dto: dto is not None and "🤖" in dto.description,
            id="unicode-emoji-description",
        ),
        pytest.param(
            {"name": "pathed-agent", "dispatch_band": 3, "paths": {"write": ["repos/x/"]}},
            lambda dto: dto is not None and dto.paths == {"write": ["repos/x/"]},
            id="paths-field-loaded-when-present",
        ),
        pytest.param(
            {"name": "no-paths", "dispatch_band": 3},
            lambda dto: dto is not None and dto.paths is None,
            id="paths-field-defaults-none",
        ),
        pytest.param(
            {"name": "bad-paths", "dispatch_band": 3, "paths": "just-a-string"},
            lambda dto: dto is not None and dto.paths is None,
            id="paths-non-dict-defaults-none",
        ),
        pytest.param(
            {"name": "legacy-agent", "description": "Legacy tier.", "tier": 2},
            lambda dto: dto is not None and dto.dispatch_band == 2,
            id="legacy-tier-only-resolves-band",
        ),
        pytest.param(
            {"name": "both-agent", "description": "Both.", "dispatch_band": 1, "tier": 3},
            lambda dto: dto is not None and dto.dispatch_band == 1,
            id="dispatch-band-beats-legacy-tier",
        ),
        pytest.param(
            {"name": "no-band-agent", "description": "No band."},
            lambda dto: dto is not None and dto.dispatch_band == 3,
            id="missing-band-defaults-to-3",
        ),
        pytest.param(
            {"name": "bad-band-str", "description": "Bad band.", "dispatch_band": "foo"},
            "raises:non-integer 'dispatch_band'",
            id="non-integer-band-raises",
        ),
        pytest.param(
            {"name": "bad-band-range", "description": "Bad band.", "dispatch_band": 7},
            "raises:invalid 'dispatch_band' value",
            id="out-of-range-band-raises",
        ),
        pytest.param(
            {"name": "design-specialist", "description": "[PLUGIN] stub.", "plugin": True},
            lambda dto: dto is not None and dto.plugin is True,
            id="plugin-stub-frontmatter-maps-to-dto",
        ),
        pytest.param(
            {
                "name": "software-engineer",
                "description": "Implementer.",
                "dispatch_band": 3,
                "gate_role": "implementer",
            },
            lambda dto: dto is not None and dto.plugin is False and dto.gate_role == "implementer",
            id="non-plugin-defaults-plugin-false-maps-gate-role",
        ),
    ],
)
def test_raw_to_dto_edge_cases(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, raw: dict[str, Any], assert_fn: Any
) -> None:
    if isinstance(assert_fn, str) and assert_fn.startswith("raises:"):
        match = assert_fn[len("raises:") :]
        with pytest.raises(MissingDispatchBandError, match=match):
            _raw_to_dto(raw)
        if raw.get("name") == "bad-band-range":
            # Companion composition-point proof: via read_canonical_agents (not the
            # direct _raw_to_dto call), an out-of-range dispatch_band skips the agent
            # silently rather than propagating the raise.
            monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
            _write_agent(
                _agentic_dir(tmp_path),
                "bad-band-agent.md",
                "name: bad-band-agent\ndescription: Invalid band.\ndispatch_band: 99\n",
                "# BadBand\n",
            )
            agents = read_canonical_agents(
                workspace_root=tmp_path, store_factory=MarkdownAgentStore
            )
            names = {a.id for a in agents}
            assert "bad-band-agent" not in names
        return
    dto = _raw_to_dto(raw)
    assert assert_fn(dto)


# ---------------------------------------------------------------------------
# get_prompt: happy path (body extraction + frontmatter-strip) — kept verbatim
# ---------------------------------------------------------------------------


def test_get_prompt_happy_path_returns_body_without_frontmatter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """get_prompt returns (body, path); the YAML frontmatter block is stripped out."""
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    _write_agent(
        _agentic_dir(tmp_path),
        "my-agent.md",
        "name: my-agent\ndescription: Test agent.\nmodel: gpt-4\n",
        "\n# My Agent\n\nYou are my agent.\n",
    )
    body, path = get_prompt("my-agent", workspace_root=tmp_path)
    assert "# My Agent" in body
    assert path.name == "my-agent.md"
    assert "name: my-agent" not in body
    assert "model: gpt-4" not in body

    # The v0.1.8 public roster uses a single unified software-engineer (not
    # language-split) and every loaded DTO is a real AgentDTO instance
    # (executed-path proof for read_lesson).
    monkeypatch.setenv("DADAIA_AGENTS_DIR", str(_PUBLIC_AGENTS_DIR))
    public_agents = read_canonical_agents(
        workspace_root=Path("/does/not/matter"), store_factory=MarkdownAgentStore
    )
    assert all(isinstance(a, AgentDTO) for a in public_agents)
    ids = {a.id for a in public_agents}
    assert "software-engineer" in ids
    assert "software-engineer-python" not in ids
    assert "software-engineer-node" not in ids


# ---------------------------------------------------------------------------
# get_prompt: error cases (invalid id, no dir, not found) — 1 param table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("agent_id", "setup", "exc", "match"),
    [
        pytest.param(
            "INVALID_ID!", None, InvalidAgentIdError, None, id="invalid-id-uppercase-bang"
        ),
        pytest.param(
            "SoftwareEngineer", None, InvalidAgentIdError, None, id="invalid-id-camelcase"
        ),
        pytest.param("software engineer", None, InvalidAgentIdError, None, id="invalid-id-space"),
        pytest.param(
            "software-engineer",
            None,
            AgentNotFoundError,
            "No agents directory",
            id="no-agents-dir",
        ),
        pytest.param(
            "missing-agent",
            "other-agent",
            AgentNotFoundError,
            "No agent file found",
            id="agent-not-found",
        ),
    ],
)
def test_get_prompt_error_cases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    agent_id: str,
    setup: str | None,
    exc: type[Exception],
    match: str | None,
) -> None:
    monkeypatch.delenv("DADAIA_AGENTS_DIR", raising=False)
    if setup is not None:
        _write_agent(
            _agentic_dir(tmp_path),
            f"{setup}.md",
            f"name: {setup}\ndescription: Other.\n",
            "# Other\n",
        )
    with pytest.raises(exc, match=match):
        get_prompt(agent_id, workspace_root=tmp_path)


# ---------------------------------------------------------------------------
# get_prompt: symlink escape (security, kept verbatim)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Real-consumer regression: the public roster stays coherent (unified
# software-engineer, no split agents, AgentDTO importable end-to-end).
# Folded into test_get_prompt_happy_path_returns_body_without_frontmatter above.
# ---------------------------------------------------------------------------

_PUBLIC_AGENTS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "dadaia_workspace" / "public" / "agents"
)
