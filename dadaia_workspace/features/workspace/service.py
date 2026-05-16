"""WorkspaceService — bootstrap and management of the .dadaia/ template."""

import json
import shutil
from pathlib import Path

from dadaia_workspace.core.models.workspace import Workspace
from dadaia_workspace.core.protocols.runtime_env import PythonEnvironmentManager
from dadaia_workspace.core.protocols.storage import PublicAssetManager

# Durable directories — must not be cleared by maintenance routines
_DADAIA_DURABLE_DIRS = [
    "academy",
    "agentic",
    "reports",
    "scripts",
    "states",
    "src",
]

# Ephemeral directories — can be recreated or cleared at any time
_DADAIA_EPHEMERAL_DIRS = [
    "tmp/python",
    "tmp/json",
]

_DADAIA_DIRS = _DADAIA_DURABLE_DIRS + _DADAIA_EPHEMERAL_DIRS

_HOOK_KEY = "UserPromptSubmit"

_EMPTY_CONTEXTS = {"version": "1", "contexts": []}
_EMPTY_ACADEMY = {"version": "1", "courses": []}
_EMPTY_SERVER_REGISTRY = {
    "version": "1",
    "range": {"min_port": 3000, "max_port": 3999},
    "entries": [],
}


class WorkspaceService:
    def __init__(
        self,
        public_assets: PublicAssetManager,
        python_env: PythonEnvironmentManager,
    ) -> None:
        self._public_assets = public_assets
        self._python_env = python_env

    def init(self, workspace_root: Path, skip_assets: bool = False) -> tuple[Workspace, list[str]]:
        """Bootstrap .dadaia/ template. Idempotent. Returns (workspace, installed_assets)."""
        workspace = Workspace.from_root(workspace_root)

        # Create .dadaia/ directory structure
        for subdir in _DADAIA_DIRS:
            (workspace.dadaia_dir / subdir).mkdir(parents=True, exist_ok=True)
        (workspace.root / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
        workspace.claude_dir.mkdir(parents=True, exist_ok=True)
        (workspace.root / ".codex").mkdir(parents=True, exist_ok=True)
        (workspace.root / ".opencode").mkdir(parents=True, exist_ok=True)

        # Initialize JSON state files (idempotent — never overwrite existing data)
        self._init_json_file(workspace.states_dir / "spec_contexts.json", _EMPTY_CONTEXTS)
        self._init_json_file(workspace.dadaia_dir / "academy" / "academy.json", _EMPTY_ACADEMY)
        self._init_json_file(workspace.states_dir / "server_registry.json", _EMPTY_SERVER_REGISTRY)

        # Create .venv (idempotent)
        self._python_env.ensure_workspace_venv(str(workspace_root))

        # Install public assets
        installed: list[str] = []
        if not skip_assets:
            installed.extend(self._public_assets.stage(workspace_root))
            installed.extend(self._public_assets.install(workspace_root, target="all"))

        # Install repos.xlsx catalog (idempotent — never overwrite)
        self._install_repos_catalog(workspace)

        # Install ctx-inject.sh and configure the hook
        self._install_hook_script(workspace)
        self._configure_hook(workspace)

        return workspace, installed

    def is_initialized(self, workspace_root: Path) -> bool:
        return (workspace_root / ".dadaia" / "states" / "spec_contexts.json").exists()

    def _init_json_file(self, path: Path, empty: dict) -> None:  # type: ignore[type-arg]
        if not path.exists():
            path.write_text(json.dumps(empty, indent=2))

    def _install_repos_catalog(self, workspace: Workspace) -> None:
        dest = workspace.dadaia_dir / "src" / "repos.xlsx"
        if not dest.exists():
            src = Path(__file__).parent.parent.parent / "public" / "data" / "repos.xlsx"
            if src.exists():
                shutil.copy2(src, dest)

    def _install_hook_script(self, workspace: Workspace) -> None:
        scripts_dir = workspace.dadaia_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        dest = scripts_dir / "ctx-inject.sh"
        src = Path(__file__).parent.parent.parent / "public" / "scripts" / "ctx-inject.sh"
        if src.exists():
            shutil.copy2(src, dest)
            dest.chmod(0o755)

    def _configure_hook(self, workspace: Workspace) -> None:
        hook_script = workspace.dadaia_dir / "scripts" / "ctx-inject.sh"
        hook_entry = {"type": "command", "command": str(hook_script)}

        claude_dir = workspace.claude_dir
        claude_dir.mkdir(parents=True, exist_ok=True)
        settings_path = claude_dir / "settings.json"

        settings: dict = {}  # type: ignore[type-arg]
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                settings = {}

        hooks = settings.setdefault("hooks", {})
        existing = hooks.get(_HOOK_KEY, [])
        already_installed = any(
            isinstance(e, dict) and e.get("command") == hook_entry["command"] for e in existing
        )
        if not already_installed:
            hooks[_HOOK_KEY] = existing + [hook_entry]
            settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
