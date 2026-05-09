"""PublicAssetService — install distributed agent artifacts into .claude/ and workspace root."""

import shutil
from pathlib import Path

from dadaia_workspace.core.protocols.storage import PublicAssetManager

_PUBLIC_DATA_DIR = Path(__file__).parent.parent.parent / "public" / "data"


class PublicAssetService:
    def __init__(self, public_assets: PublicAssetManager) -> None:
        self._public_assets = public_assets

    def install(self, workspace_root: Path, force: bool = False) -> list[str]:
        claude_dir = workspace_root / ".claude"
        installed = self._public_assets.install(claude_dir, force=force)

        # Install workspace-root data files (e.g. AGENTS.md) alongside .claude/
        for name in ("AGENTS.md",):
            src = _PUBLIC_DATA_DIR / name
            if not src.exists():
                continue
            dst = workspace_root / name
            if dst.exists() and not force:
                installed.append(f"[skip] {dst}")
            else:
                shutil.copy2(src, dst)
                installed.append(f"[ok]   {dst}")

        return installed
