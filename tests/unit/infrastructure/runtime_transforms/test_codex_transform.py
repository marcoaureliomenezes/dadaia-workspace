"""Unit tests for the Codex body transform and model map in ``codex_assets``.

Covers (ADR-2 golden tests):
- Harness skill identifiers (e.g. ``ai-harness-claude-code``) are NOT model
  identifiers and survive intact; known Claude model identifiers ARE mapped;
  the Opus/Sonnet/Haiku tier-recommendation phrase is rewritten to Codex-native
  registry-tier terms (T-013-12 defense-in-depth).
- dd-software-engineer body (no Agent tool): output is identical to input (verbatim).
- An unmapped Claude model id raises ``ValueError`` naming it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.infrastructure.runtime_transforms.codex_assets import (
    _split_frontmatter,
    codex_model,
    transform_for_codex,
)

_AGENTS_DIR = Path(__file__).parents[4] / "dadaia_workspace" / "public" / "agents"


def _load_body(agent_id: str) -> str:
    return _split_frontmatter((_AGENTS_DIR / f"{agent_id}.md").read_text(encoding="utf-8"))[1]


@pytest.mark.parametrize(
    "case",
    [
        "preserves-claude-code-skill-identifier",
        "maps-known-claude-model-identifiers-only",
        "anthropic-tier-phrase-replaced",
        "unknown-model-id-raises",
    ],
)
def test_codex_transform_replacement_matrix(case: str) -> None:
    if case == "preserves-claude-code-skill-identifier":
        body = "Use `ai-harness-claude-code` when auditing Claude Code projections."
        result = transform_for_codex(body)
        assert "`ai-harness-claude-code`" in result
        assert "ai-harness-gpt" not in result

    elif case == "maps-known-claude-model-identifiers-only":
        body = "Model row: claude-sonnet-4-6. Skill row: ai-harness-claude-code."
        result = transform_for_codex(body)
        assert "gpt-5.6-terra" in result
        assert "claude-sonnet-4-6" not in result
        assert "ai-harness-claude-code" in result

    elif case == "unknown-model-id-raises":
        with pytest.raises(ValueError, match="claude-unknown-9-9"):
            codex_model("claude-unknown-9-9")

    else:  # anthropic-tier-phrase-replaced
        body = "recommend Opus / Sonnet / Haiku based on the workload-character table."
        result = transform_for_codex(body)
        assert "Opus / Sonnet / Haiku" not in result
        assert "deep / dispatch / fast registry tiers" in result


def test_generic_agent_preserved_verbatim() -> None:
    """dd-code-reviewer has no Agent tool references — output must equal input
    (the only-coverage of the claude-string leak prevention into codex
    projections, pairing with D-CX-4)."""
    body = _load_body("dd-code-reviewer")
    result = transform_for_codex(body)
    assert result == body, (
        "Expected dd-code-reviewer body to be preserved verbatim "
        "(no Agent tool patterns present), but got diff"
    )
