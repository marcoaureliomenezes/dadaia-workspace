"""ProcessAncestry Protocol — read-only process-ancestry probe.

Bind attribution and legacy-compatible chokepoint call sites may need to answer whether
one process is an ancestor of another without touching the target process.

Three concrete adapters implement this port (T-014-06):

* Linux — walk ``/proc/<pid>/stat`` PPID chain.
* macOS — ``ps -o ppid=`` via the injected :class:`ProcessRunner` (no ``/proc``).
* Windows — read-only ``CreateToolhelp32Snapshot`` PPID walk (never destructive).

Contract red lines (verified by contract tests):

* The probe NEVER calls ``os.kill`` (no destructive signal anywhere).
* Indeterminate ancestry (unreadable ``/proc``, ``ps`` failure, snapshot failure,
  a chain that exceeds the hop budget, or a missing pid) returns the explicit
  sentinel :data:`UNKNOWN`; policy remains in the caller.

``core/`` is zero-I/O; only the Protocol and the sentinel value live here.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol


class Ancestry(Enum):
    """Result of an ancestry probe.

    ``ANCESTOR`` / ``NOT_ANCESTOR`` are determinate verdicts; ``UNKNOWN`` is the
    explicit indeterminate sentinel (DP-4: the caller maps it to ALLOW + logged WARN).
    """

    ANCESTOR = "ancestor"
    NOT_ANCESTOR = "not-ancestor"
    UNKNOWN = "unknown"


#: Module-level alias so callers can write ``Ancestry.UNKNOWN`` or ``UNKNOWN``.
UNKNOWN = Ancestry.UNKNOWN


class ProcessAncestry(Protocol):
    """Read-only process-ancestry probe.

    Implementors MUST be non-destructive (no ``os.kill``, no signals) and MUST
    return :data:`Ancestry.UNKNOWN` for any indeterminate case rather than guessing.
    """

    def is_ancestor(self, ancestor_pid: int, descendant_pid: int) -> Ancestry: ...
