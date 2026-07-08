"""Unit tests for the L1 agent-model template registry + resolver (v0.1.65 FR2/FR4).

Covers the FR2 built-in templates (9-core-agent coverage, registry-known models,
effort vocabulary, never-Fable-on-security — G-1, unique ids, ``balanced`` default),
the import-time assert failure modes, the D-3 claude→codex effort clamp map, and the
``resolve_agent_model`` precedence matrix (FR4): per-agent overlay override > applied
template > library default (``balanced``); plugin agents: override > pack default,
with the F-6 asymmetry (pack default with no override resolves model only —
``effort`` is ``None``, never a placeholder).
"""

from __future__ import annotations

import pytest

from dadaia_workspace.core.agent_model_templates import (
    _BUILT_IN,
    CORE_AGENTS,
    _assert_templates_resolve,
    default_template,
    list_templates,
    resolve_agent_model,
)
from dadaia_workspace.core.model_registry import registry_by_claude_id
from dadaia_workspace.core.models.agent_model_policy import (
    CLAUDE_EFFORTS,
    AgentModelAssignment,
    AgentModelOverride,
    AgentModelPolicyOverlay,
    AgentModelTemplate,
    codex_effort_for_claude_effort,
)

# ---------------------------------------------------------------------------
# FR2 — built-in templates
# ---------------------------------------------------------------------------


def test_exactly_three_templates_with_expected_ids() -> None:
    assert [t.id for t in list_templates()] == [
        "balanced",
        "subscription-saver",
        "max-quality",
    ]


def test_balanced_is_the_default_template() -> None:
    assert default_template().id == "balanced"
    defaults = [t for t in list_templates() if t.default]
    assert len(defaults) == 1 and defaults[0].id == "balanced"


def test_every_template_covers_exactly_the_nine_core_agents() -> None:
    for template in list_templates():
        assert set(template.assignments) == set(CORE_AGENTS), template.id
        assert len(template.assignments) == 9


def test_every_template_model_is_registry_known_and_effort_in_vocab() -> None:
    known = registry_by_claude_id()
    for template in list_templates():
        for agent, assignment in template.assignments.items():
            assert assignment.model in known, f"{template.id}:{agent}"
            assert assignment.effort in CLAUDE_EFFORTS, f"{template.id}:{agent}"


def test_no_template_assigns_fable_to_security_reviewer() -> None:
    """G-1 hard constraint: Fable is NEVER assigned to security-reviewer."""
    for template in list_templates():
        assert template.assignments["security-reviewer"].model != "claude-fable-5", template.id


def test_balanced_roster_matches_fr2_table() -> None:
    balanced = default_template()
    expected = {
        "project-manager": ("claude-fable-5", "high"),
        "software-architect": ("claude-fable-5", "high"),
        "product-engineer": ("claude-opus-4-8", "high"),
        "project-auditor": ("claude-opus-4-8", "xhigh"),
        "security-reviewer": ("claude-opus-4-8", "xhigh"),
        "code-reviewer": ("claude-opus-4-8", "high"),
        "ai-engineer": ("claude-sonnet-5", "high"),
        "software-engineer": ("claude-sonnet-5", "xhigh"),
        "qa-engineer": ("claude-sonnet-5", "high"),
    }
    assert {a: (v.model, v.effort) for a, v in balanced.assignments.items()} == expected


# ---------------------------------------------------------------------------
# Import-time assert failure modes (synthetic templates through the same assert)
# ---------------------------------------------------------------------------


def _template_with(agent: str, model: str, effort: str, **kwargs: object) -> AgentModelTemplate:
    base = dict(default_template().assignments)
    base[agent] = AgentModelAssignment(model=model, effort=effort)  # type: ignore[arg-type]
    return AgentModelTemplate(
        id=str(kwargs.get("id", "synthetic")),
        label="synthetic",
        default=True,
        assignments=base,
    )


def test_assert_fails_on_unknown_model() -> None:
    bad = _template_with("qa-engineer", "claude-unknown-9-9", "high")
    with pytest.raises(ValueError, match="claude-unknown-9-9"):
        _assert_templates_resolve((bad,))


def test_assert_fails_on_invalid_effort() -> None:
    bad = _template_with("qa-engineer", "claude-sonnet-5", "turbo")
    with pytest.raises(ValueError, match="turbo"):
        _assert_templates_resolve((bad,))


def test_assert_fails_on_fable_on_security_reviewer() -> None:
    bad = _template_with("security-reviewer", "claude-fable-5", "high")
    with pytest.raises(ValueError, match="security-reviewer"):
        _assert_templates_resolve((bad,))


def test_assert_fails_on_incomplete_coverage() -> None:
    partial = dict(default_template().assignments)
    partial.pop("qa-engineer")
    bad = AgentModelTemplate(id="partial", label="x", default=True, assignments=partial)
    with pytest.raises(ValueError, match="qa-engineer"):
        _assert_templates_resolve((bad,))


def test_assert_fails_on_duplicate_template_id() -> None:
    t = default_template()
    with pytest.raises(ValueError, match="duplicate"):
        _assert_templates_resolve((t, t))


def test_assert_fails_when_balanced_default_missing() -> None:
    only = AgentModelTemplate(
        id="other", label="x", default=True, assignments=dict(default_template().assignments)
    )
    with pytest.raises(ValueError, match="balanced"):
        _assert_templates_resolve((only,))


def test_live_built_in_passes_the_assert() -> None:
    _assert_templates_resolve(_BUILT_IN)  # must not raise


# ---------------------------------------------------------------------------
# D-3 — claude→codex effort clamp map
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "claude_effort,codex_effort",
    [("low", "low"), ("medium", "medium"), ("high", "high"), ("xhigh", "high"), ("max", "high")],
)
def test_codex_effort_clamp_map(claude_effort: str, codex_effort: str) -> None:
    assert codex_effort_for_claude_effort(claude_effort) == codex_effort  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# FR4 — resolve_agent_model precedence matrix
# ---------------------------------------------------------------------------


def test_no_overlay_resolves_balanced_with_source_default() -> None:
    resolved = resolve_agent_model("software-engineer", None)
    assert (resolved.model, resolved.effort, resolved.source) == (
        "claude-sonnet-5",
        "xhigh",
        "default",
    )


def test_applied_template_resolves_with_source_template() -> None:
    overlay = AgentModelPolicyOverlay(applied_template="subscription-saver", overrides={})
    resolved = resolve_agent_model("project-manager", overlay)
    assert (resolved.model, resolved.effort, resolved.source) == (
        "claude-opus-4-8",
        "high",
        "template",
    )


def test_ac3_per_field_override_merges_with_applied_template() -> None:
    """AC-3: template subscription-saver + override {SE: model=opus-4-8} →
    SE = opus-4-8 (override model) / xhigh (template effort), source=override."""
    overlay = AgentModelPolicyOverlay(
        applied_template="subscription-saver",
        overrides={"software-engineer": AgentModelOverride(model="claude-opus-4-8")},
    )
    resolved = resolve_agent_model("software-engineer", overlay)
    assert (resolved.model, resolved.effort, resolved.source) == (
        "claude-opus-4-8",
        "xhigh",
        "override",
    )
    # All other agents keep the applied template's values.
    other = resolve_agent_model("qa-engineer", overlay)
    assert (other.model, other.effort, other.source) == ("claude-sonnet-5", "high", "template")


def test_effort_only_override_keeps_template_model() -> None:
    overlay = AgentModelPolicyOverlay(
        applied_template=None,
        overrides={"qa-engineer": AgentModelOverride(effort="max")},
    )
    resolved = resolve_agent_model("qa-engineer", overlay)
    assert (resolved.model, resolved.effort, resolved.source) == (
        "claude-sonnet-5",
        "max",
        "override",
    )


def test_full_override_beats_template() -> None:
    overlay = AgentModelPolicyOverlay(
        applied_template="max-quality",
        overrides={
            "ai-engineer": AgentModelOverride(model="claude-haiku-4-5-20251001", effort="low")
        },
    )
    resolved = resolve_agent_model("ai-engineer", overlay)
    assert (resolved.model, resolved.effort, resolved.source) == (
        "claude-haiku-4-5-20251001",
        "low",
        "override",
    )


def test_plugin_pack_default_without_override_resolves_model_only() -> None:
    """F-6 asymmetry: pack default with no override → model only; effort is None."""
    resolved = resolve_agent_model("frontend-engineer", None, pack_default="claude-sonnet-5")
    assert (resolved.model, resolved.effort, resolved.source) == ("claude-sonnet-5", None, "pack")


def test_plugin_override_beats_pack_default() -> None:
    overlay = AgentModelPolicyOverlay(
        applied_template=None,
        overrides={"frontend-engineer": AgentModelOverride(model="claude-opus-4-8", effort="high")},
    )
    resolved = resolve_agent_model("frontend-engineer", overlay, pack_default="claude-sonnet-5")
    assert (resolved.model, resolved.effort, resolved.source) == (
        "claude-opus-4-8",
        "high",
        "override",
    )


def test_plugin_effort_only_override_keeps_pack_model() -> None:
    overlay = AgentModelPolicyOverlay(
        applied_template=None,
        overrides={"frontend-engineer": AgentModelOverride(effort="medium")},
    )
    resolved = resolve_agent_model("frontend-engineer", overlay, pack_default="claude-sonnet-5")
    assert (resolved.model, resolved.effort, resolved.source) == (
        "claude-sonnet-5",
        "medium",
        "override",
    )


def test_unknown_agent_without_pack_default_raises() -> None:
    with pytest.raises(ValueError, match="unknown agent"):
        resolve_agent_model("not-an-agent", None)


def test_unknown_applied_template_raises() -> None:
    overlay = AgentModelPolicyOverlay(applied_template="nope", overrides={})
    with pytest.raises(ValueError, match="nope"):
        resolve_agent_model("qa-engineer", overlay)
