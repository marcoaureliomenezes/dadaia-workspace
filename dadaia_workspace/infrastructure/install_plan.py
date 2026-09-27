"""``InstallPlan`` — the ONE resolution of ``install()``'s port-conforming arguments.

Split out from ``public_assets.py`` (FR6, T-30-10 / K3, v0.5.1) so both the manager and
``projection_rules.py``'s record-driven rule builders can share the single resolved
plan type without a circular import between the two.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.core.models.agent_model_policy import (
    AgentModelPolicyOverlay,
    ResolvedAgentModel,
)
from dadaia_workspace.infrastructure.public_assets_common import OverwritePolicy


@dataclass(frozen=True)
class InstallPlan:
    """``install()`` builds exactly one ``InstallPlan`` from its
    ``(workspace_root, harness, force)`` parameters, THEN runs the rule
    table over it — the flags never travel any further than this dataclass. ``force``
    is resolved to an :class:`OverwritePolicy`; ``harness`` is resolved to
    the concrete harness targets and active-harness set the rule builders select on;
    the agent-model overlay and the resolved core-agent roster are loaded once and
    carried alongside so no rule builder re-reads them.
    """

    workspace_root: Path
    agentic_dir: Path
    harness: str | None
    overwrite: OverwritePolicy
    harness_targets: tuple[str, ...]
    active_harnesses: frozenset[str]
    overlay: AgentModelPolicyOverlay | None
    resolved_models: dict[str, ResolvedAgentModel]
