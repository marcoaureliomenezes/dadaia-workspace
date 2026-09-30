"""``InstallPlan`` — the ONE resolution of ``install()``'s arguments, shared by the rule builders."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.model_registry import AgentModelPolicyOverlay, ResolvedAgentModel


@dataclass(frozen=True)
class InstallPlan:
    """Built once per ``install()``; the flags travel no further. Overlay and roster load once here."""

    workspace_root: Path
    agentic_dir: Path
    harness: str | None
    force: bool
    harness_targets: tuple[str, ...]
    active_harnesses: frozenset[str]
    overlay: AgentModelPolicyOverlay | None
    resolved_models: dict[str, ResolvedAgentModel]
