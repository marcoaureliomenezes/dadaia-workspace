"""Core agent models — `core/models/agent.py`.

Cross-feature data-transfer objects for canonical agents. Living in `core` lets
the panel feature (and any other consumer) depend on these shapes via
`core/protocols/agents_provider.py` without importing the concrete
`features.agents.reader` implementation (NEW-02 / AR-01 boundary).

`features.agents.reader` re-exports `AgentDTO`, `AgentPromptResult`,
`InvalidAgentIdError`, and `AgentNotFoundError` from here for backward
compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentDTO:
    """Data-transfer object for a canonical agent definition.

    Fields correspond to the §5.1 shape from the R3 SPEC.
    """

    id: str
    name: str
    description: str
    dispatch_band: int = 0  # 1 = orchestrator, 2 = curator, 3 = leaf specialist
    skills: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    model: str | None = None
    max_turns: int | None = None
    input_contract: dict[str, Any] | None = None
    paths: dict[str, list[str]] | None = None
    # ``plugin: true`` in the agent frontmatter marks a plugin STUB — an agent
    # that carries no behavior in the core install (constitution §14, the
    # ``plugin-scope`` rule). Plugin stubs are excluded from the panel agent
    # roster so the Agentic tab never shows ghost/uninstalled agents.
    plugin: bool = False
    # ``gate_role`` frontmatter — the agent's role at a §7 review gate or phase
    # (e.g. "implementer", "checkpoint-pre-commit"). Used to derive the
    # development-lifecycle phase(s) the agent owns or gates, honestly, from the
    # constitution §7 phase table. ``None`` when the agent declares no gate role.
    gate_role: str | None = None


@dataclass(frozen=True)
class AgentPromptResult:
    """An agent's resolved system prompt and its on-disk source path.

    Returned by `AgentsProvider.get_prompt`; replaces the bare
    `tuple[str, Path]` so the panel view layer depends on a named core type.
    """

    body: str
    source_path: Path


class InvalidAgentIdError(ValueError):
    """Raised when the agent ID fails the regex validation or path traversal check."""


class AgentNotFoundError(LookupError):
    """Raised when the agent ID is valid but no corresponding file exists."""
