"""features/agents — canonical agent catalog reader.

Public API:
    AgentDTO              — data-transfer object per SPEC §5.1 shape
    read_canonical_agents — reads agent .md files from canonical location
    get_prompt            — fetch raw body (frontmatter stripped) for a single agent
    InvalidAgentIdError   — raised when agent_id fails validation or path traversal check
    AgentNotFoundError    — raised when agent_id is valid but file does not exist
    MissingDispatchBandError — raised when an agent frontmatter has an invalid band value (present but non-int or out of {1,2,3})
    MissingTierError      — DEPRECATED alias of MissingDispatchBandError (v0.1.64 rename window)
"""

from dadaia_workspace.features.agents.reader import (
    AgentDTO,
    AgentNotFoundError,
    InvalidAgentIdError,
    MissingDispatchBandError,
    MissingTierError,
    get_prompt,
    read_canonical_agents,
)

__all__ = [
    "AgentDTO",
    "AgentNotFoundError",
    "InvalidAgentIdError",
    "MissingDispatchBandError",
    "MissingTierError",
    "get_prompt",
    "read_canonical_agents",
]
