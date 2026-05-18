"""features/agents — canonical agent catalog reader.

Public API:
    AgentDTO              — data-transfer object per SPEC §5.1 shape
    read_canonical_agents — reads agent .md files from canonical location
    get_prompt            — fetch raw body (frontmatter stripped) for a single agent
    InvalidAgentIdError   — raised when agent_id fails validation or path traversal check
    AgentNotFoundError    — raised when agent_id is valid but file does not exist
"""

from dadaia_workspace.features.agents.reader import (
    AgentDTO,
    AgentNotFoundError,
    InvalidAgentIdError,
    get_prompt,
    read_canonical_agents,
)

__all__ = [
    "AgentDTO",
    "AgentNotFoundError",
    "InvalidAgentIdError",
    "get_prompt",
    "read_canonical_agents",
]
