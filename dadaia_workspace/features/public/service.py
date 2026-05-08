"""PublicAssetService — install distributed agent artifacts into .claude/."""

from pathlib import Path

from dadaia_workspace.core.protocols.storage import PublicAssetManager


class PublicAssetService:
    def __init__(self, public_assets: PublicAssetManager) -> None:
        self._public_assets = public_assets

    def install(self, workspace_root: Path, force: bool = False) -> list[str]:
        claude_dir = workspace_root / ".claude"
        return self._public_assets.install(claude_dir, force=force)
