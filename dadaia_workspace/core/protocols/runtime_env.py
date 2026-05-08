"""Python environment manager protocol."""

from typing import Protocol


class PythonEnvironmentManager(Protocol):
    def ensure_workspace_venv(self, workspace_root: str) -> str:
        """Create .dadaia/.venv/ idempotently. Returns venv path."""
        ...

    def python_executable(self, workspace_root: str) -> str:
        """Return path to .dadaia/.venv/bin/python."""
        ...

    def pip_executable(self, workspace_root: str) -> str:
        """Return path to .dadaia/.venv/bin/pip."""
        ...
