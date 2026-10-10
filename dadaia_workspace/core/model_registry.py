"""Which model an agent gets — the one module: the tier-to-Codex map, the built-in
agent-model templates (ADR 0022, ADR 0240) and the operator overlay's resolution.

Contract: templates name a tier by alias; a new model release needs no library change.
Claude resolves the alias itself; :data:`TIER_CODEX` maps it to the Codex id. Pure data +
pure functions, stdlib only (``core-no-os-primitives``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

#: Tier alias -> Codex model id (``codex_assets.codex_model`` reads it).
TIER_CODEX: dict[str, str] = {
    "opus": "gpt-5.6-sol",
    "fable": "gpt-5.6-sol",
    "sonnet": "gpt-5.6-terra",
    "haiku": "gpt-5.3-codex-spark",
}

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
ResolvedSource = Literal["template", "default"]


@dataclass(frozen=True)
class AgentModelAssignment:
    """One template cell: the (model alias, effort) assigned to one core agent."""

    model: str
    effort: ClaudeEffort


@dataclass(frozen=True)
class AgentModelPolicyOverlay:
    """Parsed, validated operator overlay (FR3 document shape)."""

    applied_template: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize back to the FR3 document shape (omit an absent template)."""
        doc: dict[str, object] = {"schema_version": _SCHEMA_VERSION}
        if self.applied_template is not None:
            doc["applied_template"] = self.applied_template
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
    fix: str | None = None

    def __str__(self) -> str:
        return self.message if self.path is None else f"{self.message}: {self.path}"


DEFAULT_TEMPLATE_ID = "balanced"

#: ADR 0022's table: template id -> core agent -> (tier alias, effort); ``balanced`` is the default.
TEMPLATES: dict[str, dict[str, AgentModelAssignment]] = {
    "balanced": {
        "dd-product-engineer": AgentModelAssignment("opus", "high"),
        "dd-software-engineer": AgentModelAssignment("sonnet", "medium"),
        "dd-code-reviewer": AgentModelAssignment("opus", "high"),
    },
    "max-quality": {
        "dd-product-engineer": AgentModelAssignment("fable", "high"),
        "dd-software-engineer": AgentModelAssignment("opus", "medium"),
        "dd-code-reviewer": AgentModelAssignment("opus", "xhigh"),
    },
    "economy": {
        "dd-product-engineer": AgentModelAssignment("sonnet", "medium"),
        "dd-software-engineer": AgentModelAssignment("sonnet", "medium"),
        "dd-code-reviewer": AgentModelAssignment("sonnet", "high"),
    },
}

#: The core agents every template covers.
CORE_AGENTS: tuple[str, ...] = tuple(TEMPLATES[DEFAULT_TEMPLATE_ID])


def template_by_id(template_id: str) -> dict[str, AgentModelAssignment]:
    """One template's assignments. Raises ``ValueError`` naming the valid ids."""
    if template_id not in TEMPLATES:
        valid = ", ".join(TEMPLATES)
        raise ValueError(f"unknown agent-model template {template_id!r}; valid: {valid}")
    return TEMPLATES[template_id]


def resolve_agent_model(
    agent_name: str, overlay: AgentModelPolicyOverlay | None
) -> ResolvedAgentModel:
    """One agent's (model, effort, source): applied template > ``balanced`` default.
    Raises ``ValueError`` for a non-core agent or an unknown ``applied_template``."""
    if agent_name not in CORE_AGENTS:
        raise ValueError(f"unknown agent {agent_name!r}: not a core agent")
    applied = overlay.applied_template if overlay is not None else None
    base = template_by_id(applied or DEFAULT_TEMPLATE_ID)[agent_name]
    return ResolvedAgentModel(base.model, base.effort, "template" if applied else "default")
