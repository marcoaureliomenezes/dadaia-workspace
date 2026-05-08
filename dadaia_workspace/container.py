"""Composition root — builds services with concrete infrastructure."""

from pathlib import Path

from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.features.public.service import PublicAssetService
from dadaia_workspace.features.repos.service import ReposService
from dadaia_workspace.features.spec_context.service import SpecContextService
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.database import get_connection
from dadaia_workspace.infrastructure.excel_reader import OpenpyxlExcelReader
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager
from dadaia_workspace.infrastructure.sqlite_repositories import (
    SQLiteSpecContextRepository,
    SQLiteWorkspaceRepository,
)


def _db_path(workspace_root: Path) -> Path:
    return workspace_root / ".dadaia" / "data" / "dadaia.db"


def build_workspace_service(workspace_root: Path) -> WorkspaceService:
    db = _db_path(workspace_root)
    return WorkspaceService(
        workspace_repo=SQLiteWorkspaceRepository(db),
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    )


def build_spec_context_service(workspace_root: Path) -> SpecContextService:
    db = _db_path(workspace_root)
    if not db.exists():
        raise WorkspaceNotInitializedError(
            f"Workspace not initialized at '{workspace_root}'. Run 'dadaia init' first."
        )
    return SpecContextService(
        repo=SQLiteSpecContextRepository(db),
        git=GitSubprocessClient(),
        workspace_root=workspace_root,
    )


def build_public_service() -> PublicAssetService:
    return PublicAssetService(public_assets=FileSystemPublicAssetManager())


def build_repos_service() -> ReposService:
    return ReposService(excel_reader=OpenpyxlExcelReader())
