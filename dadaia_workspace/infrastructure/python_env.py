"""Python venv manager — creates .dadaia/.venv/ idempotently."""

import venv
from pathlib import Path


class VenvPythonEnvironmentManager:
    def _venv_path(self, workspace_root: str) -> Path:
        return Path(workspace_root) / ".dadaia" / ".venv"

    def ensure_workspace_venv(self, workspace_root: str) -> str:
        venv_dir = self._venv_path(workspace_root)
        if not venv_dir.exists():
            venv.create(str(venv_dir), with_pip=True)
        return str(venv_dir)

    def python_executable(self, workspace_root: str) -> str:
        return str(self._venv_path(workspace_root) / "bin" / "python")

    def pip_executable(self, workspace_root: str) -> str:
        return str(self._venv_path(workspace_root) / "bin" / "pip")
