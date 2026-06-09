"""WorkflowLauncher Protocol — abstracts subprocess launch + PID liveness check.

Design (T-016-P06):
  Defines the WorkflowLauncher protocol consumed by PanelService.run_workflow().
  Production implementation lives in infrastructure/workflow_launcher_adapter.py.
  Fakes used in tests implement the same interface.

  Separating subprocess + os.kill from the features layer keeps the features
  layer free of I/O side-effects (constitution §6: features must not call
  subprocess directly outside infrastructure).
"""

from __future__ import annotations

from typing import Protocol


class WorkflowLauncher(Protocol):
    """Launch a workflow subprocess and probe its PID liveness.

    Implementors MUST NOT raise on a liveness check for a non-existent PID;
    they MUST return False (dead) instead of raising ProcessLookupError.
    """

    def launch(
        self,
        workflow_name: str,
        workspace_root: str,
        *,
        python_executable: str,
    ) -> int:
        """Spawn ``python -m dadaia_workspace orchestrate <workflow_name>``.

        Parameters
        ----------
        workflow_name:
            The name of the workflow to launch (already validated by the caller).
        workspace_root:
            Absolute path to the workspace root; used as cwd for the subprocess.
        python_executable:
            Path to the Python interpreter that runs ``dadaia_workspace``.

        Returns
        -------
        int
            The PID of the spawned process.
        """
        ...

    def is_alive(self, pid: int) -> bool:
        """Return True if the process *pid* is still running.

        Must NOT raise — unknown / dead PIDs return False.
        """
        ...
