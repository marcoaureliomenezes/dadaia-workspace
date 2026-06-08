"""WorkflowLauncher infrastructure adapter — subprocess + os.kill implementation.

Design (T-016-P06):
  Production implementation of the WorkflowLauncher protocol.
  subprocess.Popen and os.kill belong here — never in the features layer
  (constitution §6 / no-subprocess-outside-infrastructure guardrail).

  Liveness semantics mirror OsProcessProbe (core/protocols/process_probe.py):
    - ProcessLookupError → False (definitely dead)
    - PermissionError    → True  (alive but unprobable)
    - other OSError      → True  (conservative; log warning)
"""

from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class SubprocessWorkflowLauncher:
    """Production WorkflowLauncher using subprocess.Popen + os.kill.

    Only this class (and test fakes) may call subprocess.Popen or os.kill
    for workflow management.
    """

    def launch(
        self,
        workflow_name: str,
        workspace_root: str,
        *,
        python_executable: str,
    ) -> int:
        """Spawn ``<python> -m dadaia_workspace orchestrate <workflow_name>``.

        stdout and stderr are discarded (DEVNULL) — the workflow writes its
        own run-state to ``.dadaia/runs/``.

        Returns the PID of the spawned process.
        """
        proc = subprocess.Popen(
            [python_executable, "-m", "dadaia_workspace", "orchestrate", workflow_name],
            cwd=workspace_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(
            "WorkflowLauncher: launched workflow %r as PID %d (cwd=%s)",
            workflow_name,
            proc.pid,
            workspace_root,
        )
        return proc.pid

    def is_alive(self, pid: int) -> bool:
        """Return True if process *pid* is still running.

        Uses os.kill(pid, 0) — a zero-signal probe that does NOT kill the process.

        Error handling mirrors OsProcessProbe:
          - ProcessLookupError → False (process is gone)
          - PermissionError    → True  (process exists but is owned by another user)
          - other OSError      → True  (conservative; log warning)
        """
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # PID exists but is owned by another user — treat as alive.
            return True
        except OSError as exc:
            logger.warning(
                "WorkflowLauncher.is_alive: unexpected OSError on os.kill(%d, 0): %s"
                " — assuming alive (conservative)",
                pid,
                exc,
            )
            return True
