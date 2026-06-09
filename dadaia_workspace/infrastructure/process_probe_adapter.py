"""OsProcessProbe — production implementation of ``ProcessProbe``.

Moved from ``core/protocols/process_probe.py`` in T-018-03 to enforce the
layer-boundary law: ``core/`` must be zero-I/O; ``os.kill`` belongs in
``infrastructure/``.

Semantics (v0.1.1 / Bug C fix):

    Exit condition of os.kill(pid, 0)   →   is_pid_alive()
    ----------------------------------       ----------------
    success (process exists, signalable)      True
    ProcessLookupError                        False (definitely dead)
    PermissionError                           True  (alive but unprobable;
                                                     e.g. root-owned PID
                                                     from a non-root user)
    other OSError                             True  + warning (conservative)

Rationale: false-active (entry retained when PID is actually dead but
inaccessible) is strictly safer than false-stale (entry deleted before
its owning process actually exits). The registry sweep deletes stale
entries on every register() call; a single false-stale destroys real
state, while a false-active is corrected later by the TTL or by an
explicit ``dadaia server clean``.

The previous implementation (v0.1.0) collapsed PermissionError and
ProcessLookupError into "dead", which meant docker-proxy and other
root-owned PIDs got swept the next time any project called ``register()``.

Windows note: ``os.kill(pid, 0)`` is available on Windows (Python 3.8+),
but PermissionError semantics differ.  The conservative "assume alive on
PermissionError" rule is still correct: we cannot confirm death, so we
retain the entry.
"""

import logging
import os

logger = logging.getLogger(__name__)


class OsProcessProbe:
    """Production implementation using ``os.kill(pid, 0)``.

    Treats ``PermissionError`` as alive (unprobable) — see module docstring
    for the rationale.
    """

    def is_pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            # PID exists and is owned by another user (or is a kernel PID).
            # We cannot signal it but it IS alive. Returning False here would
            # cause the registry sweep to delete a valid entry — see Bug C.
            return True
        except OSError as exc:
            # Unknown failure mode (e.g. EINTR, EINVAL). Conservative default:
            # assume alive, log a warning so operators can investigate.
            logger.warning(
                "OsProcessProbe: unexpected OSError on os.kill(%d, 0): %s "
                "— assuming alive (conservative)",
                pid,
                exc,
            )
            return True
