"""Built-in L1 agent-model templates + the single resolver (v0.1.65 FR2/FR4).

Analog of ``features/lifecycle/model_profiles.py#_BUILT_IN`` for the Layer-1 agent
roster: three named :class:`AgentModelTemplate`s (``balanced`` — the default,
``subscription-saver``, ``max-quality``), each a full 9-core-agent map of
``(model, effort)`` — the FR2 table encoded verbatim.

:func:`_assert_templates_resolve` runs at import time and fails loudly if any template
is ungoverned: incomplete 9-agent coverage, a model unknown to ``core/model_registry``,
an effort outside the D-3 vocabulary, ``claude-fable-5`` assigned to
``security-reviewer`` (operator ruling G-1 — cyber-safety classifiers can refuse
security-review-shaped work), a duplicate template id, or a missing ``balanced``
default.

:func:`resolve_agent_model` is the ONLY precedence implementation (FR4): install,
doctor, codex projection, and the panel all consume it. Per-field precedence for core
agents: per-agent overlay override > applied template > library default (``balanced``).
Plugin agents (not in the templates — G-4): override > pack-provided default (D-5),
with the F-6 asymmetry — a pack default with no override resolves the model only
(``effort`` is ``None``, never a placeholder).

Layering (D-4): pure data + pure functions, zero I/O (``core-no-os-primitives`` holds).
"""

from __future__ import annotations

from dadaia_workspace.core.model_registry import registry_by_claude_id
from dadaia_workspace.core.models.agent_model_policy import (
    CLAUDE_EFFORTS,
    AgentModelAssignment,
    AgentModelPolicyOverlay,
    AgentModelTemplate,
    ResolvedAgentModel,
)

#: The 9 core agents every template must cover exactly (G-4; constitution §14 roster).
CORE_AGENTS: tuple[str, ...] = (
    "project-manager",
    "software-architect",
    "product-engineer",
    "project-auditor",
    "security-reviewer",
    "code-reviewer",
    "ai-engineer",
    "software-engineer",
    "qa-engineer",
)

#: The default template id (G-5): used whenever no overlay / no applied_template exists.
_DEFAULT_TEMPLATE_ID = "balanced"

#: The agent that must NEVER receive claude-fable-5, in any template (G-1).
_FABLE_FORBIDDEN_AGENT = "security-reviewer"
_FABLE_MODEL = "claude-fable-5"


def _a(model: str, effort: str) -> AgentModelAssignment:
    """Terse constructor for the FR2 table below (effort narrowed by the import assert)."""
    return AgentModelAssignment(model=model, effort=effort)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# THE BUILT-IN TEMPLATES — the FR2 table, verbatim.
# ---------------------------------------------------------------------------
_BUILT_IN: tuple[AgentModelTemplate, ...] = (
    AgentModelTemplate(
        id="balanced",
        label="Balanced (default)",
        default=True,
        assignments={
            "project-manager": _a("claude-fable-5", "high"),
            "software-architect": _a("claude-fable-5", "high"),
            "product-engineer": _a("claude-opus-4-8", "high"),
            "project-auditor": _a("claude-opus-4-8", "xhigh"),
            "security-reviewer": _a("claude-opus-4-8", "xhigh"),
            "code-reviewer": _a("claude-opus-4-8", "high"),
            "ai-engineer": _a("claude-sonnet-5", "high"),
            "software-engineer": _a("claude-sonnet-5", "xhigh"),
            "qa-engineer": _a("claude-sonnet-5", "high"),
        },
    ),
    AgentModelTemplate(
        id="subscription-saver",
        label="Subscription saver",
        default=False,
        assignments={
            "project-manager": _a("claude-opus-4-8", "high"),
            "software-architect": _a("claude-opus-4-8", "high"),
            "product-engineer": _a("claude-sonnet-5", "xhigh"),
            "project-auditor": _a("claude-sonnet-5", "xhigh"),
            "security-reviewer": _a("claude-opus-4-8", "high"),
            "code-reviewer": _a("claude-sonnet-5", "xhigh"),
            "ai-engineer": _a("claude-sonnet-5", "high"),
            "software-engineer": _a("claude-sonnet-5", "xhigh"),
            "qa-engineer": _a("claude-sonnet-5", "high"),
        },
    ),
    AgentModelTemplate(
        id="max-quality",
        label="Max quality",
        default=False,
        assignments={
            "project-manager": _a("claude-fable-5", "high"),
            "software-architect": _a("claude-fable-5", "high"),
            "product-engineer": _a("claude-fable-5", "high"),
            "project-auditor": _a("claude-fable-5", "high"),
            "security-reviewer": _a("claude-opus-4-8", "xhigh"),
            "code-reviewer": _a("claude-opus-4-8", "xhigh"),
            "ai-engineer": _a("claude-opus-4-8", "medium"),
            "software-engineer": _a("claude-sonnet-5", "xhigh"),
            "qa-engineer": _a("claude-opus-4-8", "high"),
        },
    ),
)


def _assert_templates_resolve(templates: tuple[AgentModelTemplate, ...] = _BUILT_IN) -> None:
    """Fail loudly if any template is ungoverned (mirrors ``_assert_profiles_resolve``).

    Raises:
        ValueError: on a duplicate template id; a roster not covering exactly the 9
            core agents; a model unknown to the registry; an effort outside the D-3
            vocabulary; ``claude-fable-5`` on ``security-reviewer`` (G-1); or when no
            template is the ``balanced`` default.
    """
    known_models = registry_by_claude_id()
    ids: set[str] = set()
    for template in templates:
        if template.id in ids:
            raise ValueError(f"duplicate agent-model template id {template.id!r}")
        ids.add(template.id)
        covered = set(template.assignments)
        expected = set(CORE_AGENTS)
        if covered != expected:
            missing = sorted(expected - covered)
            extra = sorted(covered - expected)
            raise ValueError(
                f"template {template.id!r} must cover exactly the 9 core agents; "
                f"missing: {missing}; unexpected: {extra}"
            )
        for agent, assignment in template.assignments.items():
            if assignment.model not in known_models:
                raise ValueError(
                    f"template {template.id!r} assigns unknown model "
                    f"{assignment.model!r} to {agent!r}; not in core/model_registry"
                )
            if assignment.effort not in CLAUDE_EFFORTS:
                raise ValueError(
                    f"template {template.id!r} assigns invalid effort "
                    f"{assignment.effort!r} to {agent!r}; "
                    f"valid: {', '.join(CLAUDE_EFFORTS)}"
                )
        if template.assignments[_FABLE_FORBIDDEN_AGENT].model == _FABLE_MODEL:
            raise ValueError(
                f"template {template.id!r} assigns {_FABLE_MODEL!r} to "
                f"{_FABLE_FORBIDDEN_AGENT!r}; Fable is NEVER assigned to "
                "security-reviewer (operator ruling G-1)"
            )
    defaults = [t.id for t in templates if t.default]
    if defaults != [_DEFAULT_TEMPLATE_ID]:
        raise ValueError(
            f"exactly one default template named {_DEFAULT_TEMPLATE_ID!r} is required; "
            f"got defaults: {defaults}"
        )


_assert_templates_resolve()


def list_templates() -> tuple[AgentModelTemplate, ...]:
    """Return the built-in templates in presentation order."""
    return _BUILT_IN


def default_template() -> AgentModelTemplate:
    """Return the library default template (``balanced``)."""
    for template in _BUILT_IN:
        if template.default:
            return template
    raise ValueError("no default agent-model template")  # unreachable (import assert)


def template_by_id(template_id: str) -> AgentModelTemplate:
    """Resolve a template id.

    Raises:
        ValueError: on an unknown template id (names the valid ids).
    """
    for template in _BUILT_IN:
        if template.id == template_id:
            return template
    valid = ", ".join(t.id for t in _BUILT_IN)
    raise ValueError(f"unknown agent-model template {template_id!r}; valid: {valid}")


def resolve_agent_model(
    agent_name: str,
    overlay: AgentModelPolicyOverlay | None,
    *,
    pack_default: str | None = None,
) -> ResolvedAgentModel:
    """Resolve one agent's (model, effort, source) — the ONLY precedence implementation.

    Core agents (per-field): override > applied template > ``balanced`` default.
    Plugin agents (``pack_default`` supplied, agent not in templates): override >
    pack default; a pack default with no effort override resolves ``effort=None``
    (F-6 — the render seam then omits ``effort:`` entirely).

    Raises:
        ValueError: for an agent that is neither a core agent nor supplied with a
            ``pack_default``, or an unknown ``applied_template`` id in the overlay.
    """
    override = overlay.overrides.get(agent_name) if overlay is not None else None

    if agent_name in CORE_AGENTS:
        if overlay is not None and overlay.applied_template is not None:
            template = template_by_id(overlay.applied_template)
            base_source = "template"
        else:
            template = default_template()
            base_source = "default"
        assignment = template.assignments[agent_name]
        if override is not None and not override.is_empty:
            return ResolvedAgentModel(
                model=override.model if override.model is not None else assignment.model,
                effort=override.effort if override.effort is not None else assignment.effort,
                source="override",
            )
        return ResolvedAgentModel(
            model=assignment.model,
            effort=assignment.effort,
            source="template" if base_source == "template" else "default",
        )

    if pack_default is None:
        raise ValueError(
            f"unknown agent {agent_name!r}: not a core agent and no pack default "
            "supplied (plugin agents resolve only when their pack provides a default)"
        )
    if override is not None and not override.is_empty:
        return ResolvedAgentModel(
            model=override.model if override.model is not None else pack_default,
            effort=override.effort,
            source="override",
        )
    return ResolvedAgentModel(model=pack_default, effort=None, source="pack")


__all__ = [
    "CORE_AGENTS",
    "default_template",
    "list_templates",
    "resolve_agent_model",
    "template_by_id",
]
