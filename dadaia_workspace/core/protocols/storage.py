"""Storage protocols for public assets and catalog reading."""

from pathlib import Path
from typing import Literal, Protocol

from dadaia_workspace.core.models.doctor_report import DoctorLine


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

    def doctor(self, workspace_root: Path) -> list[DoctorLine]:
        """Compare package source, staging, and runtime projections."""
        ...


class ExcelReader(Protocol):
    def read_rows(self, file_path: Path) -> list[dict[str, str]]:
        """Read rows from an xlsx file. Returns empty list if file does not exist."""
        ...
