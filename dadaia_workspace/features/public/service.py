"""PublicAssetService — stage, install and diagnose distributed agent artifacts."""

from pathlib import Path
from typing import Literal

from dadaia_workspace.core.protocols.storage import PublicAssetManager
from dadaia_workspace.features.public.model_resolution import check_model_resolution


class PublicAssetService:
    def __init__(self, public_assets: PublicAssetManager) -> None:
        self._public_assets = public_assets

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
        reports.extend(check_model_resolution(public_dir))
        return reports
