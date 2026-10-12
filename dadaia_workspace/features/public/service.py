"""PublicAssetService — stage, install and diagnose distributed agent artifacts."""

from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.cli_line import fix_line
from dadaia_workspace.core.model_registry import (
    AgentModelPolicyOverlay,
    AgentModelPolicyStoreError,
)
from dadaia_workspace.core.models.doctor_report import DoctorLine, DoctorReport
from dadaia_workspace.features.public.model_resolution import check_model_resolution
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager

#: Loads the agent-model-policy overlay for a workspace root. Injected by
#: the composition root (``container.build_public_service``) so this feature module
#: carries no ``features -> infrastructure`` import edge.
AgentPolicyLoader = Callable[[Path], AgentModelPolicyOverlay | None]


class PublicAssetService:
    def __init__(
        self,
        public_assets: FileSystemPublicAssetManager,
        agent_policy_loader: AgentPolicyLoader | None = None,
    ) -> None:
        self._public_assets = public_assets
        self._agent_policy_loader = agent_policy_loader

    def stage(self, workspace_root: Path) -> list[str]:
        return self._public_assets.stage(workspace_root)

    def install(
        self,
        workspace_root: Path,
        harness: str | None = None,
        force: bool = False,
        template: str | None = None,
    ) -> list[str]:
        return self._public_assets.install(
            workspace_root, harness=harness, force=force, template=template
        )

    def list_all(self) -> dict[str, list[str]]:
        return self._public_assets.list_all()

    def doctor(self, workspace_root: Path) -> DoctorReport:
        reports = self._public_assets.doctor(workspace_root)
        # An invalid overlay is already a doctor ERROR line from the asset manager's pass.
        try:
            loader = self._agent_policy_loader
            overlay = loader(workspace_root) if loader else None
        except AgentModelPolicyStoreError:
            overlay = None
        reports.extend(check_model_resolution(overlay))
        return DoctorReport(lines=tuple(reports))

    def verdict(self, workspace_root: Path) -> tuple[list[DoctorLine], str]:
        """The ONE answer to "is the projection healthy": every doctor line, and the one
        remedy when any line blocks (``""`` when none does) — `public doctor` prints it and
        `dadaia doctor` carries it, so the two never disagree. The verdict is the typed
        report's, fail-closed: every blocking status fails."""
        lines = list(self.doctor(workspace_root).lines)
        blocking = [line for line in lines if line.status.blocking]
        if not blocking:
            return lines, ""
        remedy = next((line.fix for line in blocking if line.fix), "")
        return lines, remedy or fix_line(workspace_root, "public", "install")
