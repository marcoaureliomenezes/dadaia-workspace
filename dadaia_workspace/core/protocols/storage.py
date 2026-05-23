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
    ) -> list[str]:
        """Install staged public assets into runtime projections."""
        ...

    def doctor(self, workspace_root: Path) -> list[str]:
        """Compare package source, staging, and runtime projections."""
        ...


class ExcelReader(Protocol):
    def read_rows(self, file_path: Path) -> list[dict[str, str]]:
        """Read rows from an xlsx file. Returns empty list if file does not exist."""
        ...
