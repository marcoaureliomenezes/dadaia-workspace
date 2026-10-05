"""The persona frontmatter rules: a read-only persona's body never instructs a write, and
ADDITIVE keeps its one meaning — the gate's path class — never a persona word.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.core.model_registry import ResolvedAgentModel
from dadaia_workspace.infrastructure.agent_transcodes import codex_agent_toml_bytes
from dadaia_workspace.infrastructure.install_helpers import render_claude_agent

pytestmark = pytest.mark.contract

_AGENTS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "agents"
_PERSONAS = sorted(_AGENTS.glob("*.md"))
#: An instruction that needs the Write tool (literal phrasings, case-insensitive).
_NEEDS_WRITE = re.compile(
    r"write the (?:review )?report|emit the handoff|emit via `dd-handoff-emitter`"
    r"|`Write` to|write to `repos/|writes reports",
    re.IGNORECASE,
)
_RESOLVED = ResolvedAgentModel(model="claude-sonnet-5", effort="high", source="default")


@pytest.mark.parametrize("persona", _PERSONAS, ids=lambda p: p.stem)
def test_a_persona_body_never_requires_a_missing_tool(persona: Path) -> None:
    """sa-reviewer-persona-body-contradicts-its-tools#B1: the rendered Claude agent and
    Codex TOML of a persona without Write never instruct a write."""
    claude = render_claude_agent(persona.read_text(encoding="utf-8"), _RESOLVED)
    if "disallowedTools: [Edit, Write, NotebookEdit]" not in claude:
        return
    codex = codex_agent_toml_bytes(persona, persona.stem, _RESOLVED).decode("utf-8")
    for rendered in (claude, codex):
        assert _NEEDS_WRITE.findall(rendered) == []
