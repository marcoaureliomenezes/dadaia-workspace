"""Pure data model for the Layer-1 agent-model policy (v0.1.65 FR2/FR3/FR4).

Typed overlay shapes
for the L1 agent roster: an operator overlay (``applied_template`` + per-agent per-field
``overrides``) layered over library-shipped templates, resolved by the single resolver in
``core/agent_model_templates.py``.

Layering (SPEC D-4): pure data, zero I/O, stdlib-only imports plus
``core.model_registry`` — importable from both ``infrastructure`` (install pipeline) and
``features`` (panel service) under the import-linter contracts
(``core-no-os-primitives`` holds).

D-3: the rendered Claude ``effort:`` vocabulary is ``low|medium|high|xhigh|max``; the
codex ``model_reasoning_effort`` derives from the RESOLVED per-agent effort via the fixed
clamp map :data:`_CODEX_EFFORT_CLAMP` (``CodexEffort`` stays 3-valued).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, get_args

from dadaia_workspace.core.model_registry import CodexEffort

#: Schema identifier for the overlay document (FR3).
_SCHEMA_VERSION = "agent-model-policy-v1"

#: Rendered Claude reasoning-effort vocabulary (D-3).
ClaudeEffort = Literal["low", "medium", "high", "xhigh", "max"]

#: The effort vocabulary as an ordered tuple (validation + panel payloads).
CLAUDE_EFFORTS: tuple[ClaudeEffort, ...] = get_args(ClaudeEffort)

#: Where a resolved (model, effort) came from (FR8 resolved-roster tagging).
ResolvedSource = Literal["override", "template", "default", "pack"]

#: D-3 fixed clamp map: resolved Claude effort → codex ``model_reasoning_effort``.
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


@dataclass(frozen=True)
class AgentModelAssignment:
    """One template cell: the (model, effort) assigned to one core agent."""

    model: str
    effort: ClaudeEffort


@dataclass(frozen=True)
class AgentModelTemplate:
    """A library-shipped named template covering the full 9-core-agent roster (FR2)."""

    id: str
    label: str
    default: bool
    assignments: dict[str, AgentModelAssignment]


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
    """Parsed, validated operator overlay (in-memory; FR3 document shape)."""

    applied_template: str | None = None
    overrides: dict[str, AgentModelOverride] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize back to the FR3 document shape (omit empty/absent fields)."""
        doc: dict[str, object] = {"schema_version": _SCHEMA_VERSION}
        if self.applied_template is not None:
            doc["applied_template"] = self.applied_template
        if self.overrides:
            overrides: dict[str, dict[str, str]] = {}
            for agent, override in sorted(self.overrides.items()):
                entry: dict[str, str] = {}
                if override.model is not None:
                    entry["model"] = override.model
                if override.effort is not None:
                    entry["effort"] = override.effort
                overrides[agent] = entry
            doc["overrides"] = overrides
        return doc


@dataclass(frozen=True)
class ResolvedAgentModel:
    """The resolver's answer for one agent: model, effort (``None`` only for a plugin
    agent resolved from its pack default with no effort override — F-6), and source."""

    model: str
    effort: ClaudeEffort | None
    source: ResolvedSource


@dataclass(frozen=True)
class AgentModelPolicyStoreError(Exception):
    """Actionable agent-model-policy overlay failure (missing ≠ invalid; FR3)."""

    message: str
    path: Path | None = None

    def __str__(self) -> str:
        if self.path is None:
            return self.message
        return f"{self.message}: {self.path}"


__all__ = [
    "CLAUDE_EFFORTS",
    "AgentModelAssignment",
    "AgentModelOverride",
    "AgentModelPolicyOverlay",
    "AgentModelPolicyStoreError",
    "AgentModelTemplate",
    "ClaudeEffort",
    "ResolvedAgentModel",
    "ResolvedSource",
    "codex_effort_for_claude_effort",
]
