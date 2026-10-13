"""Unit tests for ``core.model_registry`` — the one module answering which model an
agent gets: templates name a tier by alias, ``TIER_CODEX`` maps alias to Codex id, the
effort clamp, and ``resolve_agent_model`` (applied template > ``balanced`` default).
Agents and cells come from ``TEMPLATES`` and ``CORE_AGENTS``, never roster literals.
"""

from __future__ import annotations

import dataclasses
from typing import get_args

import pytest

import dadaia_workspace.core.model_registry as mr
from dadaia_workspace.core.model_registry import (
    CORE_AGENTS,
    TEMPLATES,
    AgentModelPolicyOverlay,
    codex_effort_for_claude_effort,
    resolve_agent_model,
)

ALIASES = {"opus", "sonnet", "haiku", "fable"}
CELLS = [(t, a) for t, cells in TEMPLATES.items() for a in cells]


@pytest.mark.parametrize(("template", "agent"), CELLS)
def test_every_template_cell_names_a_tier_alias(template: str, agent: str) -> None:
    """No cell names an exact Claude model id."""
    assert TEMPLATES[template][agent].model in ALIASES


def test_tier_codex_has_exactly_the_four_spec_entries() -> None:
    assert mr.TIER_CODEX == {
        "opus": "gpt-5.6-sol",
        "fable": "gpt-5.6-sol",
        "sonnet": "gpt-5.6-terra",
        "haiku": "gpt-5.3-codex-spark",
    }


@pytest.mark.parametrize("template", list(TEMPLATES))
def test_code_reviewer_never_resolves_to_fable(template: str) -> None:
    """Kept by the template table alone."""
    overlay = AgentModelPolicyOverlay(applied_template=template)
    assert resolve_agent_model("dd-code-reviewer", overlay).model != "fable"


def test_resolver_has_no_override_source_and_overlay_only_applied_template() -> None:
    """Overrides are gone from the resolver and the overlay."""
    assert get_args(mr.ResolvedSource) == ("template", "default")
    assert [f.name for f in dataclasses.fields(AgentModelPolicyOverlay)] == ["applied_template"]


def test_default_template_is_balanced() -> None:
    assert mr.DEFAULT_TEMPLATE_ID == "balanced"


@pytest.mark.parametrize(
    "claude_effort,codex_effort",
    [("low", "low"), ("medium", "medium"), ("high", "high"), ("xhigh", "high"), ("max", "high")],
)
def test_codex_effort_clamp_map(claude_effort: str, codex_effort: str) -> None:
    assert codex_effort_for_claude_effort(claude_effort) == codex_effort  # type: ignore[arg-type]


@pytest.mark.parametrize(("template", "agent"), CELLS)
def test_applied_template_resolves_its_cell(template: str, agent: str) -> None:
    cell = TEMPLATES[template][agent]
    resolved = resolve_agent_model(agent, AgentModelPolicyOverlay(applied_template=template))
    assert (resolved.model, resolved.effort, resolved.source) == (
        cell.model,
        cell.effort,
        "template",
    )


@pytest.mark.parametrize("agent", CORE_AGENTS)
def test_no_overlay_resolves_the_balanced_default(agent: str) -> None:
    cell = TEMPLATES["balanced"][agent]
    resolved = resolve_agent_model(agent, None)
    assert (resolved.model, resolved.effort, resolved.source) == (
        cell.model,
        cell.effort,
        "default",
    )


@pytest.mark.parametrize(
    ("agent", "overlay", "match"),
    [
        pytest.param("not-an-agent", None, "unknown agent", id="unknown_agent"),
        pytest.param(CORE_AGENTS[0], AgentModelPolicyOverlay(applied_template="nope"), "nope", id="unknown_applied_template"),
    ],
)  # fmt: skip
def test_resolve_agent_model_rejects_unknown(
    agent: str, overlay: AgentModelPolicyOverlay | None, match: str
) -> None:
    """An unknown agent or template is refused by name."""
    with pytest.raises(ValueError, match=match):
        resolve_agent_model(agent, overlay)
