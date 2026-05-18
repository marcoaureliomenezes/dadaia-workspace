"""features/agents — canonical agent catalog reader.

Public API:
    AgentDTO         — data-transfer object per SPEC §5.1 shape
    read_canonical_agents — reads agent .md files from canonical location
"""

from dadaia_workspace.features.agents.reader import AgentDTO, read_canonical_agents

__all__ = ["AgentDTO", "read_canonical_agents"]
