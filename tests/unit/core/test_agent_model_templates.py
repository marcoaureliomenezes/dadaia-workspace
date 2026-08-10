"""Unit tests for the L1 agent-model template registry + resolver (v0.1.65 FR2/FR4).

Covers the FR2 built-in templates (9-core-agent coverage, registry-known models,
effort vocabulary, never-Fable-on-security — G-1, unique ids, ``balanced`` default),
the import-time assert failure modes, the D-3 claude→codex effort clamp map, and the
``resolve_agent_model`` precedence matrix (FR4): per-agent overlay override > applied
template > library default (``balanced``),
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
# G-1 hard constraint: Fable is NEVER assigned to security-reviewer — kept standalone
# (model-governance security constraint, not merged with other template shape checks).
# ---------------------------------------------------------------------------


def test_no_template_assigns_fable_to_security_reviewer() -> None:
    for template in list_templates():
        assert template.assignments["security-reviewer"].model != "claude-fable-5", template.id


# ---------------------------------------------------------------------------
# FR2 — built-in templates: ids/default, 9-core coverage, registry+vocab validity.
# ---------------------------------------------------------------------------


def test_template_ids_default_and_balanced_roster_golden() -> None:
    assert [t.id for t in list_templates()] == [
        "balanced",
        "subscription-saver",
        "max-quality",
    ]
    assert default_template().id == "balanced"
    defaults = [t for t in list_templates() if t.default]
    assert len(defaults) == 1 and defaults[0].id == "balanced"

    balanced = default_template()
    expected = {
        "project-manager": ("claude-fable-5", "high"),
        "software-architect": ("claude-fable-5", "high"),
        "product-engineer": ("claude-opus-5", "high"),
        "project-auditor": ("claude-opus-5", "xhigh"),
        "security-reviewer": ("claude-opus-5", "xhigh"),
        "code-reviewer": ("claude-opus-5", "high"),
        "ai-engineer": ("claude-sonnet-5", "high"),
        "software-engineer": ("claude-sonnet-5", "xhigh"),
        "qa-engineer": ("claude-sonnet-5", "high"),
    }
    assert {a: (v.model, v.effort) for a, v in balanced.assignments.items()} == expected


def test_every_template_covers_nine_core_agents_with_registry_known_effort_vocab() -> None:
    known = registry_by_claude_id()
    for template in list_templates():
        assert set(template.assignments) == set(CORE_AGENTS), template.id
        assert len(template.assignments) == 9
        for agent, assignment in template.assignments.items():
            assert assignment.model in known, f"{template.id}:{agent}"
            assert assignment.effort in CLAUDE_EFFORTS, f"{template.id}:{agent}"


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


@pytest.mark.parametrize(
    ("name", "build_fn", "match"),
    [
        (
            "unknown_model",
            lambda: (_template_with("qa-engineer", "claude-unknown-9-9", "high"),),
            "claude-unknown-9-9",
        ),
        (
            "invalid_effort",
            lambda: (_template_with("qa-engineer", "claude-sonnet-5", "turbo"),),
            "turbo",
        ),
        (
            # The import-time assert retains the fable-on-security synthetic case
            # (a model-governance security constraint check, separate from G-1's
            # standalone live-registry sweep above).
            "fable_on_security_reviewer",
            lambda: (_template_with("security-reviewer", "claude-fable-5", "high"),),
            "security-reviewer",
        ),
        (
            "incomplete_coverage",
            lambda: (
                AgentModelTemplate(
                    id="partial",
                    label="x",
                    default=True,
                    assignments={
                        k: v
                        for k, v in default_template().assignments.items()
                        if k != "qa-engineer"
                    },
                ),
            ),
            "qa-engineer",
        ),
        ("duplicate_template_id", lambda: (default_template(), default_template()), "duplicate"),
        (
            "balanced_default_missing",
            lambda: (
                AgentModelTemplate(
                    id="other",
                    label="x",
                    default=True,
                    assignments=dict(default_template().assignments),
                ),
            ),
            "balanced",
        ),
    ],
)
def test_assert_templates_resolve_rejects_malformed(
    name: str, build_fn: object, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        _assert_templates_resolve(build_fn())  # type: ignore[operator]

    if name == "duplicate_template_id":
        # Companion positive proof: the live built-in roster passes the same
        # assert cleanly (must not raise).
        _assert_templates_resolve(_BUILT_IN)


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


@pytest.mark.parametrize(
    ("name", "agent", "overlay_fn", "expected"),
    [
        (
            "no_overlay_resolves_balanced_default",
            "software-engineer",
            lambda: None,
            ("claude-sonnet-5", "xhigh", "default"),
        ),
        (
            "applied_template_resolves_source_template",
            "project-manager",
            lambda: AgentModelPolicyOverlay(applied_template="subscription-saver", overrides={}),
            ("claude-opus-5", "high", "template"),
        ),
        (
            # AC-3: template subscription-saver + override {SE: model=opus-4-8} →
            # SE = opus-4-8 (override model) / xhigh (template effort), source=override.
            "per_field_override_merges_with_applied_template",
            "software-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template="subscription-saver",
                overrides={"software-engineer": AgentModelOverride(model="claude-opus-4-8")},
            ),
            ("claude-opus-4-8", "xhigh", "override"),
        ),
        (
            "effort_only_override_keeps_template_model",
            "qa-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template=None,
                overrides={"qa-engineer": AgentModelOverride(effort="max")},
            ),
            ("claude-sonnet-5", "max", "override"),
        ),
        (
            "full_override_beats_template",
            "ai-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template="max-quality",
                overrides={
                    "ai-engineer": AgentModelOverride(
                        model="claude-haiku-4-5-20251001", effort="low"
                    )
                },
            ),
            ("claude-haiku-4-5-20251001", "low", "override"),
        ),
        (
            # AC-3: an unrelated agent keeps the applied template when only ONE
            # other agent in the overlay is overridden.
            "ac3_other_agents_keep_applied_template_when_only_one_overridden",
            "qa-engineer",
            lambda: AgentModelPolicyOverlay(
                applied_template="subscription-saver",
                overrides={"software-engineer": AgentModelOverride(model="claude-opus-4-8")},
            ),
            ("claude-sonnet-5", "high", "template"),
        ),
    ],
)
def test_resolve_agent_model_precedence_table(
    name: str,
    agent: str,
    overlay_fn: object,
    expected: tuple[str, str | None, str],
) -> None:
    overlay = overlay_fn()  # type: ignore[operator]
    resolved = resolve_agent_model(agent, overlay)
    assert (resolved.model, resolved.effort, resolved.source) == expected


@pytest.mark.parametrize(
    ("name", "agent", "overlay_fn", "match"),
    [
        ("unknown_agent", "not-an-agent", lambda: None, "unknown agent"),
        (
            "unknown_applied_template",
            "qa-engineer",
            lambda: AgentModelPolicyOverlay(applied_template="nope", overrides={}),
            "nope",
        ),
    ],
)
def test_resolve_agent_model_rejects_unknown(
    name: str, agent: str, overlay_fn: object, match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        resolve_agent_model(agent, overlay_fn())  # type: ignore[operator]
