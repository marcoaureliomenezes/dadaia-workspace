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

_EMPTY_CONTEXTS = {"schema_version": "2", "contexts": []}
_EMPTY_ACADEMY = {"version": "1", "courses": []}
_EMPTY_SERVER_REGISTRY = {
    "version": "1",
    "range": {"min_port": 3000, "max_port": 3999},
    "entries": [],
}

# Legacy ctx-inject.sh basename — used to detect stale registrations that must
# be superseded (replaced) by the new Python hook command (T-018-17).
_CTX_INJECT_SH_BASENAME = "ctx-inject.sh"

# Canonical Python module for the ctx-inject hook (T-018-17).
_CTX_INJECT_MODULE = "dadaia_workspace.hooks.ctx_inject"


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

        # Configure the ctx-inject hook (Python module command; the legacy
        # ctx-inject.sh script was retired in v0.1.10, Decision D-1).
        self._configure_hook(workspace)

        return workspace, installed

    def is_initialized(self, workspace_root: Path) -> bool:
        return (workspace_root / ".dadaia" / "states" / "spec_contexts.json").exists()

    def _init_json_file(self, path: Path, empty: dict) -> None:  # type: ignore[type-arg]
        if not path.exists():
            path.write_text(json.dumps(empty, indent=2), encoding="utf-8")

    def _install_repos_catalog(self, workspace: Workspace) -> None:
        dest = workspace.dadaia_dir / "src" / "repos.xlsx"
        if not dest.exists():
            src = Path(__file__).parent.parent.parent / "public" / "data" / "repos.xlsx"
            if src.exists():
                shutil.copy2(src, dest)

    def _configure_hook(self, workspace: Workspace) -> None:
        # T-018-17: emit the Python hook command instead of the .sh path.
        hook_command = self._canonical_hook_command(workspace)

        # Canonical Claude Code hook schema: a matcher entry carrying a nested
        # `hooks` array. This is the same schema `public_assets.py` writes, so
        # the two paths agree and never produce a malformed duplicate entry.
        hook_entry = {
            "matcher": "",
            "hooks": [{"type": "command", "command": hook_command}],
        }

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

        # T-018-17: SUPERSEDE — replace stale .sh entries with the canonical Python command.
        # If the Python command is already registered, skip. If a stale .sh entry exists,
        # replace it. Otherwise append.
        if self._hook_command_present(existing, hook_command):
            # Already up-to-date — nothing to do.
            return

        updated = self._supersede_stale_sh(existing, hook_entry)
        hooks[_HOOK_KEY] = updated
        settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    @staticmethod
    def _canonical_hook_command(workspace: Workspace) -> str:
        """Return the canonical ctx-inject hook command for *workspace* (Python module form)."""
        import sys

        from dadaia_workspace.core.platform import PLATFORM

        venv_python = (
            workspace.dadaia_dir
            / ".venv"
            / PLATFORM.venv_scripts_dir
            / f"python{PLATFORM.venv_exe_suffix}"
        )
        if venv_python.is_file():
            python_bin = str(venv_python)
        elif sys.executable:
            python_bin = sys.executable
        else:
            python_bin = "python"
        return f"{python_bin} -m {_CTX_INJECT_MODULE}"

    @staticmethod
    def _supersede_stale_sh(
        existing: object,
        new_entry: dict,  # type: ignore[type-arg]
    ) -> list:  # type: ignore[type-arg]
        """Replace any stale ctx-inject.sh entry in *existing* with *new_entry*.

        If no stale `.sh` entry is found, appends *new_entry*. This ensures the
        projection SUPERSEDES (replaces) a stale `.sh` registration rather than
        appending a second hook (T-018-17 done-criterion: not appends).
        """
        if not isinstance(existing, list):
            return [new_entry]

        result = []
        replaced = False
        for entry in existing:
            if not isinstance(entry, dict):
                result.append(entry)
                continue
            if _is_stale_sh_entry(entry):
                if not replaced:
                    result.append(new_entry)
                    replaced = True
                # Drop the stale entry (or extra duplicates of the new one already added)
                continue
            result.append(entry)
        if not replaced:
            result.append(new_entry)
        return result

    @staticmethod
    def _hook_command_present(existing: object, hook_command: str) -> bool:
        """True if ``hook_command`` is already registered.

        Detects the command in either the nested canonical schema
        (``entry["hooks"][i]["command"]``) or the legacy flat schema
        (``entry["command"]``). Also recognizes the stale ``.sh`` path as
        "present" to avoid double-appending — use ``_supersede_stale_sh`` to
        replace it with the Python command.

        T-018-17: also checks whether *hook_command* is the Python ctx-inject
        command and if so, recognizes the old `.sh` path as "already handled"
        so callers that only need a presence check (not supersede) work correctly.
        """
        if not isinstance(existing, list):
            return False
        for entry in existing:
            if not isinstance(entry, dict):
                continue
            if entry.get("command") == hook_command:
                return True
            nested = entry.get("hooks")
            if isinstance(nested, list) and any(
                isinstance(h, dict) and h.get("command") == hook_command for h in nested
            ):
                return True
        return False


def _is_stale_sh_entry(entry: dict) -> bool:  # type: ignore[type-arg]
    """Return True if *entry* references the legacy ctx-inject.sh command."""
    # Check nested schema (canonical)
    nested = entry.get("hooks")
    if isinstance(nested, list):
        for h in nested:
            if isinstance(h, dict):
                cmd = str(h.get("command", ""))
                if cmd.endswith(_CTX_INJECT_SH_BASENAME) or _CTX_INJECT_SH_BASENAME in cmd:
                    return True
    # Check legacy flat schema
    cmd = str(entry.get("command", ""))
    return cmd.endswith(_CTX_INJECT_SH_BASENAME) or _CTX_INJECT_SH_BASENAME in cmd
