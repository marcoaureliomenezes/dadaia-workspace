"""ProcessProbe Protocol — PID liveness check abstraction."""

import os
from typing import Protocol


class ProcessProbe(Protocol):
    def is_pid_alive(self, pid: int) -> bool: ...


class OsProcessProbe:
    """Production implementation using os.kill(pid, 0)."""

    def is_pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False
