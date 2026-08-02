"""Storage protocols for public assets and catalog reading."""

from pathlib import Path
from typing import Literal, Protocol


class PublicAssetManager(Protocol):
    def stage(self, workspace_root: Path) -> list[str]:
        """Stage package public assets into workspace_root/.dadaia/agentic."""
        ...

    def install(
        self,
        workspace_root: Path,
        target: str = "all",
        force: bool = False,
        scope: Literal["all", "repos-only", "workspace-only"] = "all",
        only: str | None = None,
    ) -> list[str]:
        """Install staged public assets into runtime projections."""
        ...

    def list_all(self) -> dict[str, list[str]]:
        """Return all public asset names grouped by category directory."""
        ...

    def install_claude_settings(self, workspace_root: Path) -> list[str]:
        """Write dadaia's canonical hook wiring into ``.claude/settings.json``.

        Separate from :meth:`install` because ``init --skip-assets`` must still produce a
        GATED workspace: the PreToolUse entrypoint is a safety boundary, not an asset
        (bug ``init-skip-assets-writes-gateless-claude-settings``). Merges — it never
        clobbers operator-owned keys.
        """
        ...

    def doctor(self, workspace_root: Path) -> list[str]:
        """Compare package source, staging, and runtime projections."""
        ...


class ExcelReader(Protocol):
    def read_rows(self, file_path: Path) -> list[dict[str, str]]:
        """Read rows from an xlsx file. Returns empty list if file does not exist."""
        ...
