"""WorkspaceService — bootstrap and management of the .dadaia/ template."""

from pathlib import Path

from dadaia_workspace.core.models.workspace import Workspace
from dadaia_workspace.core.protocols.repositories import WorkspaceRepository
from dadaia_workspace.core.protocols.runtime_env import PythonEnvironmentManager
from dadaia_workspace.core.protocols.storage import PublicAssetManager
from dadaia_workspace.infrastructure.database import bootstrap_schema

_DADAIA_DIRS = [
    "contexts",
    "data",
    "reports",
    "src",
    "tmp/python",
    "tmp/json",
]


class WorkspaceService:
    def __init__(
        self,
        workspace_repo: WorkspaceRepository,
        public_assets: PublicAssetManager,
        python_env: PythonEnvironmentManager,
    ) -> None:
        self._workspace_repo = workspace_repo
        self._public_assets = public_assets
        self._python_env = python_env

    def init(self, workspace_root: Path, skip_assets: bool = False) -> tuple[Workspace, list[str]]:
        """Bootstrap .dadaia/ template. Idempotent. Returns (workspace, installed_assets)."""
        workspace = Workspace.from_root(workspace_root)

        # Create .dadaia/ directory structure
        for subdir in _DADAIA_DIRS:
            (workspace.dadaia_dir / subdir).mkdir(parents=True, exist_ok=True)

        # Bootstrap SQLite schema
        db_path = workspace.dadaia_dir / "data" / "dadaia.db"
        bootstrap_schema(db_path)

        # Persist workspace metadata
        self._workspace_repo.save(workspace)

        # Create .venv (idempotent)
        self._python_env.ensure_workspace_venv(str(workspace_root))

        # Install public assets
        installed: list[str] = []
        if not skip_assets:
            installed = self._public_assets.install(workspace.claude_dir)

        return workspace, installed

    def is_initialized(self, workspace_root: Path) -> bool:
        db_path = workspace_root / ".dadaia" / "data" / "dadaia.db"
        return db_path.exists()
