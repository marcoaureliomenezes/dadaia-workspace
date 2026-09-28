"""Which model an agent gets — the one module: the model registry, the built-in
agent-model templates (ADR 0022) and the operator overlay's resolution.

The Codex model map (``codex_assets.codex_model``, ADR-5) derives from :data:`REGISTRY`. Pure data + pure functions, stdlib only (``core-no-os-primitives``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, get_args

#: Model-cost class: ``deep`` reasoning leaves, ``dispatch`` dispatchers + gate leaves,
#: ``standard`` general implementation, ``fast`` high-volume mechanical.
Tier = Literal["deep", "dispatch", "fast", "standard"]


@dataclass(frozen=True)
class ModelEntry:
    """One model: its Claude id (agent frontmatter), Codex id and tier."""

    claude_id: str
    codex_id: str
    tier: Tier = "dispatch"


#: Every Claude model id the fleet uses, exactly once.
REGISTRY: tuple[ModelEntry, ...] = (
    ModelEntry("claude-fable-5", "gpt-5.6-sol", "deep"),
    ModelEntry("claude-fable-5-1", "gpt-5.6-sol", "deep"),
    ModelEntry("claude-opus-4-7", "gpt-5.6-sol", "dispatch"),
    ModelEntry("claude-opus-4-8", "gpt-5.6-sol", "dispatch"),
    ModelEntry("claude-opus-5", "gpt-5.6-sol", "dispatch"),
    ModelEntry("claude-opus-5-5", "gpt-5.6-sol", "dispatch"),
    ModelEntry("claude-sonnet-4-6", "gpt-5.6-terra", "standard"),
    ModelEntry("claude-sonnet-5", "gpt-5.6-terra", "standard"),
    ModelEntry("claude-haiku-4-5-20251001", "gpt-5.3-codex-spark", "fast"),
)


def registry_by_claude_id() -> dict[str, ModelEntry]:
    """The registry indexed by ``claude_id``."""
    return {entry.claude_id: entry for entry in REGISTRY}


def is_fable_model(claude_id: str) -> bool:
    """G-1 is a FAMILY rule: every registered ``claude-fable-*`` id is Fable."""
    return claude_id.startswith("claude-fable-") and claude_id in registry_by_claude_id()


CodexEffort = Literal["high", "medium", "low"]

#: Rendered Claude reasoning-effort vocabulary (D-3).
ClaudeEffort = Literal["low", "medium", "high", "xhigh", "max"]
CLAUDE_EFFORTS: tuple[ClaudeEffort, ...] = get_args(ClaudeEffort)

#: D-3 fixed clamp map: resolved Claude effort -> codex ``model_reasoning_effort``.
_CODEX_EFFORT_CLAMP: dict[ClaudeEffort, CodexEffort] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "high",
    "max": "high",
}


def codex_effort_for_claude_effort(effort: ClaudeEffort) -> CodexEffort:
    """Clamp a resolved Claude effort to the 3-valued codex effort axis (D-3)."""
    return _CODEX_EFFORT_CLAMP[effort]


#: Schema identifier for the overlay document (FR3).
_SCHEMA_VERSION = "agent-model-policy-v1"

#: Where a resolved (model, effort) came from.
ResolvedSource = Literal["override", "template", "default"]


@dataclass(frozen=True)
class AgentModelAssignment:
    """One template cell: the (model, effort) assigned to one core agent."""

    model: str
    effort: ClaudeEffort


@dataclass(frozen=True)
class AgentModelOverride:
    """A per-agent, per-field override (FR3): ``model``, ``effort``, or both."""

    model: str | None = None
    effort: ClaudeEffort | None = None

    @property
    def is_empty(self) -> bool:
        return self.model is None and self.effort is None


@dataclass(frozen=True)
class AgentModelPolicyOverlay:
    """Parsed, validated operator overlay (FR3 document shape)."""

    applied_template: str | None = None
    overrides: dict[str, AgentModelOverride] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize back to the FR3 document shape (omit empty/absent fields)."""
        doc: dict[str, object] = {"schema_version": _SCHEMA_VERSION}
        if self.applied_template is not None:
            doc["applied_template"] = self.applied_template
        if self.overrides:
            doc["overrides"] = {
                agent: {
                    k: v for k, v in (("model", o.model), ("effort", o.effort)) if v is not None
                }
                for agent, o in sorted(self.overrides.items())
            }
        return doc


@dataclass(frozen=True)
class ResolvedAgentModel:
    """The resolver's answer for one agent: model, effort, and precedence source."""

    model: str
    effort: ClaudeEffort | None
    source: ResolvedSource


@dataclass(frozen=True)
class AgentModelPolicyStoreError(Exception):
    """Actionable agent-model-policy overlay failure (missing != invalid; FR3)."""

    message: str
    path: Path | None = None

    def __str__(self) -> str:
        return self.message if self.path is None else f"{self.message}: {self.path}"


#: The three core agents every template covers (ADR 0022).
CORE_AGENTS: tuple[str, ...] = ("dd-product-engineer", "dd-software-engineer", "dd-code-reviewer")

#: Never receives a Fable-family model (G-1; the security lens runs here since ADR 0016).
FABLE_FORBIDDEN_AGENT = "dd-code-reviewer"

_DEFAULT_TEMPLATE_ID = "balanced"

#: ADR 0022's table: template id -> core agent -> (model, effort); ``balanced`` is the default.
TEMPLATES: dict[str, dict[str, AgentModelAssignment]] = {
    "balanced": {
        "dd-product-engineer": AgentModelAssignment("claude-opus-5-5", "high"),
        "dd-code-reviewer": AgentModelAssignment("claude-opus-5-5", "high"),
        "dd-software-engineer": AgentModelAssignment("claude-opus-5-5", "low"),
    },
    "max-quality": {
        "dd-product-engineer": AgentModelAssignment("claude-fable-5-1", "high"),
        "dd-code-reviewer": AgentModelAssignment("claude-opus-5-5", "xhigh"),
        "dd-software-engineer": AgentModelAssignment("claude-opus-5-5", "medium"),
    },
    "economy": {
        "dd-product-engineer": AgentModelAssignment("claude-opus-5-5", "high"),
        "dd-code-reviewer": AgentModelAssignment("claude-sonnet-5", "high"),
        "dd-software-engineer": AgentModelAssignment("claude-sonnet-5", "medium"),
    },
}


def template_by_id(template_id: str) -> dict[str, AgentModelAssignment]:
    """One template's assignments. Raises ``ValueError`` naming the valid ids."""
    if template_id not in TEMPLATES:
        valid = ", ".join(TEMPLATES)
        raise ValueError(f"unknown agent-model template {template_id!r}; valid: {valid}")
    return TEMPLATES[template_id]


def resolve_agent_model(
    agent_name: str, overlay: AgentModelPolicyOverlay | None
) -> ResolvedAgentModel:
    """One agent's (model, effort, source), per field: override > applied template >
    ``balanced`` default. Raises ``ValueError`` for a non-core agent or an unknown
    ``applied_template``."""
    if agent_name not in CORE_AGENTS:
        raise ValueError(f"unknown agent {agent_name!r}: not a core agent")
    applied = overlay.applied_template if overlay is not None else None
    base = template_by_id(applied or _DEFAULT_TEMPLATE_ID)[agent_name]
    override = overlay.overrides.get(agent_name) if overlay is not None else None
    if override is not None and not override.is_empty:
        return ResolvedAgentModel(
            model=override.model or base.model,
            effort=override.effort or base.effort,
            source="override",
        )
    return ResolvedAgentModel(base.model, base.effort, "template" if applied else "default")
