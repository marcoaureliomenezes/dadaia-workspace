"""Python environment manager protocol."""

from typing import Protocol


class PythonEnvironmentManager(Protocol):
    def ensure_workspace_venv(self, workspace_root: str) -> str:
        """Create the workspace virtual environment idempotently.

        Returns the path to the venv root directory
        (e.g. ``<workspace_root>/.dadaia/.venv``).
        """
        ...

    def python_executable(self, workspace_root: str) -> str:
        """Return the path to the Python executable inside the workspace venv.

        The executable lives under ``<venv>/bin/python`` on POSIX platforms
        and ``<venv>/Scripts/python.exe`` on Windows.  Implementations must
        derive the path from platform capability flags (``PLATFORM.venv_scripts_dir``
        and ``PLATFORM.venv_exe_suffix``) rather than hardcoding a specific layout.
        """
        ...

    def pip_executable(self, workspace_root: str) -> str:
        """Return the path to the pip executable inside the workspace venv.

        Same platform-specific layout applies as for ``python_executable``.
        Implementations must use ``PLATFORM.venv_scripts_dir`` and
        ``PLATFORM.venv_exe_suffix`` to construct the correct path.
        """
        ...
