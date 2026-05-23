"""PublicAssetService — stage, install and diagnose distributed agent artifacts."""

from pathlib import Path
from typing import Literal

from dadaia_workspace.core.protocols.storage import PublicAssetManager


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
    ) -> list[str]:
        return self._public_assets.install(workspace_root, target=target, force=force, scope=scope)

    def doctor(self, workspace_root: Path) -> list[str]:
        return self._public_assets.doctor(workspace_root)
