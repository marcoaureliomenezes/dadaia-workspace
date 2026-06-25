"""WorkflowLauncher infrastructure adapter — subprocess + OsProcessProbe.

Design (T-016-P06 / T-018-11):
  Production implementation of the WorkflowLauncher protocol.
  subprocess.Popen belongs here — never in the features layer
  (constitution §6 / no-subprocess-outside-infrastructure guardrail).

  Liveness is now delegated to OsProcessProbe.is_pid_alive() rather than
  inlining a duplicate os.kill probe (T-018-11 done criterion).
"""

from __future__ import annotations

import logging
import subprocess

from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe

logger = logging.getLogger(__name__)

_probe = OsProcessProbe()


class SubprocessWorkflowLauncher:
    """Production WorkflowLauncher using subprocess.Popen + OsProcessProbe.

    Only this class (and test fakes) may call subprocess.Popen for workflow
    management.  Process liveness is delegated to OsProcessProbe so there is
    a single implementation of os.kill(pid, 0) semantics in the codebase.
    """

    def launch(
        self,
        workflow_name: str,
        workspace_root: str,
        *,
        python_executable: str,
    ) -> int:
        """Spawn ``<python> -m dadaia_workspace orchestrate run <workflow_name>``.

        Since WS-3 (release ``multiharness-engine-v0116``), ``orchestrate run`` is a
        reference-only no-op: it validates the workflow name, prints the
        "execution moved to ``dadaia lifecycle``" notice, and exits 0. The explicit
        ``run`` subcommand is required — a bare ``orchestrate <workflow_name>`` is
        parsed by Typer as an unknown subcommand and would exit non-zero.

        stdout and stderr are discarded (DEVNULL); the process exits cleanly.

        Returns the PID of the spawned process.
        """
        proc = subprocess.Popen(
            [python_executable, "-m", "dadaia_workspace", "orchestrate", "run", workflow_name],
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

        Delegates to ``OsProcessProbe.is_pid_alive()``.  See
        ``process_probe_adapter.py`` for the full semantics (PermissionError →
        True, ProcessLookupError → False, other OSError → True + warning).
        """
        return _probe.is_pid_alive(pid)
