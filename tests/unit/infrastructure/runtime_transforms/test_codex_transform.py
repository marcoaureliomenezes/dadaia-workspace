"""Unit tests for dadaia_workspace.infrastructure.runtime_transforms.codex.

Covers (ADR-2 golden tests):
- project-manager / project-auditor bodies: Agent tool references are replaced with
  Codex custom-agent wording.
- Harness skill identifiers (e.g. ``ai-harness-claude-code``) are NOT model
  identifiers and survive intact; known Claude model identifiers ARE mapped;
  the Opus/Sonnet/Haiku tier-recommendation phrase is rewritten to Codex-native
  registry-tier terms (T-013-12 defense-in-depth).
- software-architect body (no Agent tool): output is identical to input (verbatim).
- All 12 canonical agents (9 core + 3 plugin stubs): output is non-empty after strip().
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.runtime_transforms.codex import transform_for_codex

_AGENTS_DIR = Path(__file__).parents[4] / "dadaia_workspace" / "public" / "agents"

_FRONTMATTER_DELIM = "---"


def _strip_frontmatter(text: str) -> str:
    """Remove the YAML frontmatter block (between ``---`` delimiters) from *text*.

    If no frontmatter is present the full text is returned unchanged.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
        return text
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONTMATTER_DELIM:
            return "".join(lines[i + 1 :])
    return text


def _load_body(agent_id: str) -> str:
    """Load the body (frontmatter-stripped) of *agent_id*."""
    path = _AGENTS_DIR / f"{agent_id}.md"
    raw = path.read_text(encoding="utf-8")
    return _strip_frontmatter(raw)


# All 12 canonical agent IDs (v0.1.8/v0.1.9 surface: 9 core + 3 plugin stubs).
_CANONICAL_AGENTS: tuple[str, ...] = (
    "ai-engineer",
    "code-reviewer",
    "design-specialist",
    "devops-engineer",
    "frontend-engineer",
    "product-engineer",
    "project-auditor",
    "project-manager",
    "qa-engineer",
    "security-reviewer",
    "software-architect",
    "software-engineer",
)


@pytest.mark.parametrize(
    "case",
    [
        "project-manager-agent-tool-replaced",
        "project-auditor-agent-tool-replaced",
        "preserves-claude-code-skill-identifier",
        "maps-known-claude-model-identifiers-only",
        "anthropic-tier-phrase-replaced",
    ],
)
def test_codex_transform_replacement_matrix(case: str) -> None:
    if case == "project-manager-agent-tool-replaced":
        body = _load_body("project-manager")
        result = transform_for_codex(body, "project-manager")
        assert "Agent tool" not in result, (
            "Expected 'Agent tool' to be replaced in project-manager output"
        )
        assert "`Agent`" not in result, (
            "Expected '`Agent`' tool-table entry to be replaced in project-manager output"
        )
        assert "subagent dispatch" not in result
        assert "explicit Codex subagent delegation" in result

    elif case == "project-auditor-agent-tool-replaced":
        body = _load_body("project-auditor")
        result = transform_for_codex(body, "project-auditor")
        assert "Agent tool" not in result, (
            "Expected 'Agent tool' to be replaced in project-auditor output"
        )
        assert "`Agent`" not in result, (
            "Expected '`Agent`' tool-table entry to be replaced in project-auditor output"
        )
        assert "subagent dispatch" not in result
        assert "explicit Codex subagent delegation" in result

    elif case == "preserves-claude-code-skill-identifier":
        body = "Use `ai-harness-claude-code` when auditing Claude Code projections."
        result = transform_for_codex(body, "ai-engineer")
        assert "`ai-harness-claude-code`" in result
        assert "ai-harness-gpt" not in result

    elif case == "maps-known-claude-model-identifiers-only":
        body = "Model row: claude-sonnet-4-6. Skill row: ai-harness-claude-code."
        result = transform_for_codex(body, "ai-engineer")
        assert "gpt-5.3-codex" in result
        assert "claude-sonnet-4-6" not in result
        assert "ai-harness-claude-code" in result

    else:  # anthropic-tier-phrase-replaced
        body = "recommend Opus / Sonnet / Haiku based on the workload-character table."
        result = transform_for_codex(body, "ai-engineer")
        assert "Opus / Sonnet / Haiku" not in result
        assert "deep / dispatch / fast registry tiers" in result


def test_generic_agent_preserved_verbatim() -> None:
    """software-architect has no Agent tool references — output must equal input
    (the only-coverage of the claude-string leak prevention into codex
    projections, pairing with D-CX-4)."""
    body = _load_body("software-architect")
    result = transform_for_codex(body, "software-architect")
    assert result == body, (
        "Expected software-architect body to be preserved verbatim "
        "(no Agent tool patterns present), but got diff"
    )


def test_output_nonempty_all_agents() -> None:
    """For every canonical agent, transform_for_codex output must not be empty."""
    for agent_id in _CANONICAL_AGENTS:
        body = _load_body(agent_id)
        result = transform_for_codex(body, agent_id)
        assert result.strip() != "", (
            f"transform_for_codex returned empty output for agent '{agent_id}'"
        )
