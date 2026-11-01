"""Which model an agent gets — the one module: the tier-to-Codex map, the built-in
agent-model templates and the operator overlay's resolution.

Contract: templates name a tier by alias; a new model release needs no library change.
Claude resolves the alias itself; :data:`TIER_CODEX` maps it to the Codex id. Pure data +
pure functions, stdlib only (``core-no-os-primitives``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, get_args

from dadaia_workspace.core.exceptions import DadaiaError

#: Tier alias -> Codex model id (``codex_assets.codex_model`` reads it).
TIER_CODEX: dict[str, str] = {
    "opus": "gpt-5.6-sol",
    "fable": "gpt-5.6-sol",
    "sonnet": "gpt-5.6-terra",
    "haiku": "gpt-5.3-codex-spark",
}

CodexEffort = Literal["high", "medium", "low"]

#: Rendered Claude reasoning-effort vocabulary.
ClaudeEffort = Literal["low", "medium", "high", "xhigh", "max"]
CLAUDE_EFFORTS: tuple[ClaudeEffort, ...] = get_args(ClaudeEffort)

#: Fixed clamp map: resolved Claude effort -> codex ``model_reasoning_effort``.
_CODEX_EFFORT_CLAMP: dict[ClaudeEffort, CodexEffort] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "high",
    "max": "high",
}


def codex_effort_for_claude_effort(effort: ClaudeEffort) -> CodexEffort:
    """Clamp a resolved Claude effort to the 3-valued codex effort axis."""
    return _CODEX_EFFORT_CLAMP[effort]


#: Schema identifier for the overlay document.
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
    """Parsed, validated operator overlay."""

    applied_template: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Serialize back to the document shape (omit an absent template)."""
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


class AgentModelPolicyStoreError(DadaiaError):
    """Actionable agent-model-policy overlay failure (missing != invalid).

    *problem* is the finding; *fix* its one remedy (``""`` when none), joined into the
    message the CLI boundary prints, like ``SchemaVersionError``.
    """

    def __init__(self, message: str, path: Path | None = None, fix: str = "") -> None:
        super().__init__(message if path is None else f"{message}: {path}", fix)


DEFAULT_TEMPLATE_ID = "balanced"

#: The table: template id -> core agent -> (tier alias, effort); ``balanced`` is the default.
TEMPLATES: dict[str, dict[str, AgentModelAssignment]] = {
    "balanced": {
        "dd-product-engineer": AgentModelAssignment("opus", "high"),
        "dd-code-reviewer": AgentModelAssignment("opus", "high"),
        "dd-sw-engineer-sr": AgentModelAssignment("sonnet", "medium"),
        "dd-sw-engineer-jr": AgentModelAssignment("haiku", "medium"),
        "dd-researcher": AgentModelAssignment("haiku", "medium"),
    },
    "max-quality": {
        "dd-product-engineer": AgentModelAssignment("fable", "high"),
        "dd-code-reviewer": AgentModelAssignment("opus", "xhigh"),
        "dd-sw-engineer-sr": AgentModelAssignment("opus", "medium"),
        "dd-sw-engineer-jr": AgentModelAssignment("sonnet", "medium"),
        "dd-researcher": AgentModelAssignment("sonnet", "medium"),
    },
    "economy": {
        "dd-product-engineer": AgentModelAssignment("sonnet", "medium"),
        "dd-code-reviewer": AgentModelAssignment("sonnet", "high"),
        "dd-sw-engineer-sr": AgentModelAssignment("sonnet", "medium"),
        "dd-sw-engineer-jr": AgentModelAssignment("haiku", "low"),
        "dd-researcher": AgentModelAssignment("haiku", "low"),
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
