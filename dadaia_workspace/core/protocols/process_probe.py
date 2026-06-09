"""ProcessProbe Protocol — PID liveness check abstraction.

The concrete ``OsProcessProbe`` implementation lives in
``dadaia_workspace.infrastructure.process_probe_adapter`` (moved in T-018-03
to keep ``core/`` free of I/O modules).  Only the Protocol definition belongs
in ``core/``.
"""

from typing import Protocol


class ProcessProbe(Protocol):
    def is_pid_alive(self, pid: int) -> bool: ...
