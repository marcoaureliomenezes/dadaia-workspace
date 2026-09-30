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

#: Loads the agent-model-policy overlay for a workspace root (v0.1.65 FR7). Injected by
#: the composition root (``container.build_public_service``) so this feature module
#: carries no ``features -> infrastructure`` import edge (D-4).
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
    ) -> list[str]:
        return self._public_assets.install(workspace_root, harness=harness, force=force)

    def list_all(self) -> dict[str, list[str]]:
        return self._public_assets.list_all()

    def doctor(self, workspace_root: Path) -> DoctorReport:
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
        return DoctorReport(lines=tuple(reports))

    def verdict(self, workspace_root: Path) -> tuple[list[DoctorLine], str]:
        """The ONE answer to "is the projection healthy": every doctor line, and the one
        remedy when any line blocks (``""`` when none does) — `public doctor` prints it and
        `dadaia doctor` carries it, so the two never disagree. The verdict is the typed
        report's, fail-closed: every blocking status fails (public-doctor-exits-zero-despite-error)."""
        lines = list(self.doctor(workspace_root).lines)
        blocking = any(line.status.blocking for line in lines)
        return lines, fix_line(workspace_root, "public", "install") if blocking else ""
