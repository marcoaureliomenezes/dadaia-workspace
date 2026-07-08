"""PublicAssetService — stage, install and diagnose distributed agent artifacts."""

from collections.abc import Callable
from pathlib import Path
from typing import Literal

from dadaia_workspace.core.models.agent_model_policy import (
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
)
from dadaia_workspace.core.protocols.storage import PublicAssetManager
from dadaia_workspace.features.public.model_resolution import check_model_resolution

#: Loads the agent-model-policy overlay for a workspace root (v0.1.65 FR7). Injected by
#: the composition root (``container.build_public_service``) so this feature module
#: carries no ``features -> infrastructure`` import edge (D-4).
AgentPolicyLoader = Callable[[Path], AgentModelPolicyOverlay | None]


class PublicAssetService:
    def __init__(
        self,
        public_assets: PublicAssetManager,
        agent_policy_loader: AgentPolicyLoader | None = None,
    ) -> None:
        self._public_assets = public_assets
        self._agent_policy_loader = agent_policy_loader

    def stage(self, workspace_root: Path) -> list[str]:
        return self._public_assets.stage(workspace_root)

    def install(
        self,
        workspace_root: Path,
        target: str = "all",
        force: bool = False,
        scope: Literal["all", "repos-only", "workspace-only"] = "all",
        only: str | None = None,
    ) -> list[str]:
        return self._public_assets.install(
            workspace_root, target=target, force=force, scope=scope, only=only
        )

    def list_all(self) -> dict[str, list[str]]:
        return self._public_assets.list_all()

    def doctor(self, workspace_root: Path) -> list[str]:
        reports = self._public_assets.doctor(workspace_root)
        # R8b (T-010-24): model-resolution guard against
        # model-catalog-modelmap-pricing-drift-no-registry. Runs against the
        # canonical packaged public/ source (same dir the asset manager stages from),
        # not the workspace projection, so it validates the source of truth.
        public_dir = Path(__file__).resolve().parent.parent.parent / "public"
        # v0.1.65 FR7: validate the RESOLVED roster (templates + overlay) too. An
        # invalid overlay is already reported as a doctor ERROR line by the asset
        # manager's doctor pass, so it degrades to defaults here (no duplicate line).
        overlay: AgentModelPolicyOverlay | None = None
        if self._agent_policy_loader is not None:
            try:
                overlay = self._agent_policy_loader(workspace_root)
            except AgentModelPolicyStoreError:
                overlay = None
        reports.extend(check_model_resolution(public_dir, overlay=overlay))
        return reports
