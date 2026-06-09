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

from dadaia_workspace.core.platform import PLATFORM

logger = logging.getLogger(__name__)


class OsProcessProbe:
    """Production implementation of ``ProcessProbe``.

    POSIX uses ``os.kill(pid, 0)`` (treating ``PermissionError`` as alive — see
    module docstring).  Windows uses a read-only ``OpenProcess`` existence check:
    ``os.kill`` is NOT a liveness probe there because CPython implements it as
    ``OpenProcess(PROCESS_ALL_ACCESS)`` + ``TerminateProcess(handle, sig)`` —
    calling it with sig 0 would *kill* the target, and a dead PID raises
    ERROR_INVALID_PARAMETER (87) rather than ESRCH, which the conservative
    "assume alive" fallback misread as alive (the FR-RC2 false-positive).
    Platform is decided via the ``PLATFORM.has_os_kill_liveness`` seam flag.
    """

    def is_pid_alive(self, pid: int) -> bool:
        if not PLATFORM.has_os_kill_liveness:
            return self._is_pid_alive_windows(pid)
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

    def _is_pid_alive_windows(self, pid: int) -> bool:
        """Non-destructive Windows liveness probe via ``OpenProcess``.

        Opens the process with PROCESS_QUERY_LIMITED_INFORMATION (read-only — does
        NOT terminate it) and inspects the result:

            OpenProcess succeeds + exit code STILL_ACTIVE  -> alive
            OpenProcess succeeds + concrete exit code      -> dead (exited)
            fails ERROR_ACCESS_DENIED (5)                  -> alive (exists,
                                                              unprobable; mirrors
                                                              the POSIX EPERM rule)
            fails ERROR_INVALID_PARAMETER (87) / other     -> dead (no such PID)
        """
        import ctypes

        if pid < 0:
            return False
        process_query_limited_information = 0x1000
        error_access_denied = 5
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            last_error = ctypes.get_last_error()  # type: ignore[attr-defined]
            return bool(last_error == error_access_denied)
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                # Could not query exit status — conservative: assume alive.
                return True
            return bool(int(exit_code.value) == still_active)
        finally:
            kernel32.CloseHandle(handle)
