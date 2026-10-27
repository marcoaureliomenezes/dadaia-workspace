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
from tests.helpers.oslib import read_text

_AGENTS = Path(__file__).resolve().parents[2] / "dadaia_workspace" / "public" / "agents"
_PERSONAS = sorted(_AGENTS.glob("*.md"))
#: An instruction that needs the Write tool (literal phrasings, case-insensitive).
_NEEDS_WRITE = re.compile(
    r"write the (?:review )?report|emit the handoff|emit via `dd-handoff-emitter`"
    r"|`Write` to|write to `repos/|writes reports",
    re.IGNORECASE,
)
#: An instruction to route an alert, decision or proposal to the operator, whom no persona's
#: tools reach (its one channel is its returned text to the main thread).
_NEEDS_OPERATOR = re.compile(
    r"\b(?:alert|inform|notif|tell|escalat|put|surfac|ask|report|return|send|hand|flag|warn|rais)"
    r"[a-z]*\b[^.;\n]{0,60}\boperator\b|\bto the operator\b",
    re.IGNORECASE,
)
_RESOLVED = ResolvedAgentModel(model="sonnet", effort="high", source="default")


@pytest.mark.parametrize("persona", _PERSONAS, ids=lambda p: p.stem)
def test_a_persona_body_never_requires_a_missing_tool(persona: Path) -> None:
    """The rendered Claude agent and
    Codex TOML of a persona without Write never instruct a write."""
    claude = render_claude_agent(read_text(persona), _RESOLVED)
    if "disallowedTools: [Edit, Write, NotebookEdit]" not in claude:
        return
    codex = codex_agent_toml_bytes(persona, persona.stem, _RESOLVED).decode("utf-8")
    for rendered in (claude, codex):
        assert _NEEDS_WRITE.findall(rendered) == []


@pytest.mark.parametrize("persona", _PERSONAS, ids=lambda p: p.stem)
def test_a_persona_body_never_routes_to_the_operator_it_cannot_reach(persona: Path) -> None:
    """The rendered Claude agent and Codex TOML of every persona route no act to the operator."""
    claude = render_claude_agent(read_text(persona), _RESOLVED)
    codex = codex_agent_toml_bytes(persona, persona.stem, _RESOLVED).decode("utf-8")
    for rendered in (claude, codex):
        assert _NEEDS_OPERATOR.findall(rendered) == []


@pytest.mark.parametrize(
    ("sentence", "routes"),
    [
        ("Stop and alert the operator and the main thread on a CRITICAL finding.", True),
        ("Report a deferral to the operator as an intake proposal.", True),
        ("Surface a stale branch to the operator first.", True),
        ("Stop and report a CRITICAL finding to the operator.", True),
        ("Return the blocker to the operator.", True),
        ("Alerts the operator on a red.", True),
        ("It notifies the operator of the gap.", True),
        ("Hand it to the operator.", True),
        ("Stop before implementation and inform the operator.", True),
        ("Ask the operator which one to keep.", True),
        ("Stop and alert when X; the operator decides.", False),
    ],
)
def test_the_operator_route_pattern_matches_the_addressee_not_a_phrase(
    sentence: str, routes: bool
) -> None:
    assert bool(_NEEDS_OPERATOR.search(sentence)) is routes
