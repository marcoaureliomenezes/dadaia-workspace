"""The Codex body transform and model map (ADR-2): Claude model ids and the tier phrase
are rewritten, harness skill identifiers are not, an unmapped id raises.

Intent: CONTRACT — ADR-2 golden tests, T-013-12
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
    ("body", "present", "absent"),
    [
        pytest.param(
            "Use `ai-harness-claude-code` when auditing.",
            "`ai-harness-claude-code`",
            "ai-harness-gpt",
            id="preserves-claude-code-skill-identifier",
        ),
        pytest.param(
            "Model row: claude-sonnet-4-6. Skill row: ai-harness-claude-code.",
            "gpt-5.6-terra",
            "claude-sonnet-4-6",
            id="maps-known-claude-model-identifiers-only",
        ),
        pytest.param(
            "recommend Opus / Sonnet / Haiku based on the table.",
            "deep / dispatch / fast registry tiers",
            "Opus / Sonnet / Haiku",
            id="anthropic-tier-phrase-replaced",
        ),
    ],
)
def test_codex_transform_replacement_matrix(body: str, present: str, absent: str) -> None:
    result = transform_for_codex(body)
    assert present in result and absent not in result
    assert "ai-harness-claude-code" in result or "ai-harness" not in body


def test_an_unmapped_claude_model_id_raises() -> None:
    with pytest.raises(ValueError, match="claude-unknown-9-9"):
        codex_model("claude-unknown-9-9")


def test_generic_agent_preserved_verbatim() -> None:
    """A body with no Claude-specific pattern passes through verbatim (pairs with D-CX-4)."""
    body = _load_body("dd-code-reviewer")
    assert transform_for_codex(body) == body
