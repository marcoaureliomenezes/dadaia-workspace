"""Python venv manager — creates .dadaia/.venv/ idempotently.

Executable paths are constructed using ``PLATFORM.venv_scripts_dir`` and
``PLATFORM.venv_exe_suffix`` so that the paths are correct on both POSIX
(``bin/python``) and Windows (``Scripts/python.exe``).
"""

import os
import subprocess
import venv
from importlib import metadata
from pathlib import Path

import dadaia_workspace
from dadaia_workspace.core.platform import PLATFORM


class WorkspaceVenvBootstrapError(RuntimeError):
    """Workspace venv bootstrap could not install the running distribution."""


class VenvPythonEnvironmentManager:
    def _venv_path(self, workspace_root: str) -> Path:
        return Path(workspace_root) / ".dadaia" / ".venv"

    def _dadaia_entrypoint(self, workspace_root: str) -> Path:
        return (
            self._venv_path(workspace_root)
            / PLATFORM.venv_scripts_dir
            / f"dadaia{PLATFORM.venv_exe_suffix}"
        )

    def _install_spec(self) -> str:
        """Resolve what to ``pip install`` so the venv mirrors the running distribution.

        Self-hosting (the package importable from a source checkout with a
        ``pyproject.toml``): install that checkout editable, so the workspace venv tracks
        source edits. Otherwise (wheel install, e.g. pipx/PyPI): pin the exact running
        version from the index.
        """
        candidate = os.environ.get("DADAIA_BOOTSTRAP_PACKAGE", "").strip()
        if candidate:
            candidate_path = Path(candidate).expanduser().resolve()
            if not candidate_path.is_file() or candidate_path.suffix != ".whl":
                raise ValueError("DADAIA_BOOTSTRAP_PACKAGE must name an existing local wheel")
            return str(candidate_path)
        src_root = Path(dadaia_workspace.__file__).resolve().parent.parent
        if (src_root / "pyproject.toml").is_file():
            return str(src_root)
        return f"dadaia-workspace=={metadata.version('dadaia-workspace')}"

    def ensure_workspace_venv(self, workspace_root: str) -> str:
        """Ensure a venv that satisfies doctor VENV-1: create it AND install the package.

        Idempotent repair, not exists-check-and-bail: an existing venv missing the
        ``dadaia`` entrypoint (the exact state doctor VENV-1 flags) is repaired by
        installing ``dadaia_workspace`` into it (bug
        init-venv-never-installs-dadaia-workspace).
        """
        venv_dir = self._venv_path(workspace_root)
        if not venv_dir.exists():
            venv.create(str(venv_dir), with_pip=True)
        if not self._dadaia_entrypoint(workspace_root).exists():
            spec = self._install_spec()
            install_cmd = [self.pip_executable(workspace_root), "install", "--quiet"]
            if Path(spec).is_dir():
                install_cmd.append("--editable")
            install_cmd.append(spec)
            try:
                subprocess.run(install_cmd, check=True)
            except subprocess.CalledProcessError as exc:
                # Unpublished candidate wheels are the consumer-validation norm: the
                # exact-version PyPI pin cannot resolve, and a raw CalledProcessError
                # traceback pointed nowhere (validation-028 F-02..F-23 cascade). Name
                # the escape hatch that exists for exactly this case.
                raise WorkspaceVenvBootstrapError(
                    f"workspace venv bootstrap failed installing '{spec}'. If this "
                    "version is not published on the index (e.g. a candidate wheel "
                    "under validation) or the index is unreachable, point "
                    "DADAIA_BOOTSTRAP_PACKAGE at the local wheel file and retry, e.g. "
                    "DADAIA_BOOTSTRAP_PACKAGE=/path/to/dadaia_workspace-X.Y.Z-py3-none-any.whl "
                    "dadaia init"
                ) from exc
        return str(venv_dir)

    def python_executable(self, workspace_root: str) -> str:
        return str(
            self._venv_path(workspace_root)
            / PLATFORM.venv_scripts_dir
            / f"python{PLATFORM.venv_exe_suffix}"
        )

    def pip_executable(self, workspace_root: str) -> str:
        return str(
            self._venv_path(workspace_root)
            / PLATFORM.venv_scripts_dir
            / f"pip{PLATFORM.venv_exe_suffix}"
        )
