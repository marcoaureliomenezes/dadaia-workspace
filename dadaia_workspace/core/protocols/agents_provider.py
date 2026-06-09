"""AgentsProvider Protocol — canonical-agent read surface for the panel."""

from pathlib import Path
from typing import Protocol

from dadaia_workspace.core.models.agent import AgentDTO, AgentPromptResult


class AgentsProvider(Protocol):
    """Minimum read surface that PanelService requires from the agents feature.

    The concrete implementation lives in ``features.agents.reader``
    (``FileSystemAgentsProvider``); the panel depends only on this protocol so
    no concrete sibling-feature import is needed (NEW-02 / AR-01 boundary).
    """

    def read_canonical_agents(self, workspace_root: Path) -> list[AgentDTO]: ...

    def get_prompt(self, agent_id: str, workspace_root: Path) -> AgentPromptResult: ...
