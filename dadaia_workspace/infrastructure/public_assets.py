"""Public asset manager — copies dadaia_workspace/public/ to target .claude/."""

import shutil
from pathlib import Path

from dadaia_workspace.core.exceptions import PublicAssetError


class FileSystemPublicAssetManager:
    def __init__(self) -> None:
        # Locate public/ relative to this file: dadaia_workspace/infrastructure/ -> dadaia_workspace/public/
        self._public_dir = Path(__file__).parent.parent / "public"

    def install(self, target_claude_dir: Path, force: bool = False) -> list[str]:
        if not self._public_dir.exists():
            raise PublicAssetError(f"Public assets directory not found: {self._public_dir}")

        installed: list[str] = []
        target_claude_dir.mkdir(parents=True, exist_ok=True)

        for asset_type in ("rules", "skills", "commands"):
            src_dir = self._public_dir / asset_type
            if not src_dir.exists():
                continue
            dst_dir = target_claude_dir / asset_type
            dst_dir.mkdir(parents=True, exist_ok=True)

            for src_path in src_dir.rglob("*"):
                if not src_path.is_file():
                    continue
                relative = src_path.relative_to(src_dir)
                dst_path = dst_dir / relative
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                if dst_path.exists() and not force:
                    installed.append(f"[skip] {dst_path}")
                    continue
                shutil.copy2(src_path, dst_path)
                installed.append(f"[ok]   {dst_path}")

        return installed
