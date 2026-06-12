"""Concrete ``ProcessAncestry`` adapters — Linux / macOS / Windows (T-014-06).

Each adapter answers "is ``ancestor_pid`` an ancestor of ``descendant_pid``?" by
walking the PPID chain upward from ``descendant_pid`` for at most
:data:`_MAX_HOPS` hops. None of them ever calls ``os.kill`` or sends a signal — the
probe is strictly read-only (FR-W1-01 contract red line). Any indeterminate case
(unreadable source, missing pid, runner failure, hop budget exhausted) returns
:data:`~dadaia_workspace.core.protocols.process_ancestry.Ancestry.UNKNOWN`; the
ALLOW+WARN decision lives in the caller.

Platform selection happens in the composition root (``container.py``) via the
``PLATFORM.has_proc_fs`` / ``has_os_kill_liveness`` seam, never by an in-adapter
``sys.platform`` branch.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.core.protocols.process_ancestry import Ancestry
from dadaia_workspace.core.protocols.process_runner import ProcessRunner

#: Upper bound on PPID hops walked before declaring the relationship indeterminate.
#: Guards against a corrupt/cyclic ppid chain looping forever; a real ancestry
#: chain in any harness is far shallower than this.
_MAX_HOPS = 64

#: pid 0 / 1 are the kernel/init roots — walking past them yields nothing useful and
#: they are never a meaningful ``ancestor_pid`` for a chokepoint allow.
_ROOT_PIDS = frozenset({0, 1})


def _walk(
    ancestor_pid: int,
    descendant_pid: int,
    ppid_of: Callable[[int], int | None],
) -> Ancestry:
    """Walk the PPID chain from ``descendant_pid`` looking for ``ancestor_pid``.

    ``ppid_of(pid)`` returns the parent pid, or ``None`` when it cannot be resolved.
    A ``None`` mid-walk ⇒ :data:`Ancestry.UNKNOWN` (we cannot prove non-ancestry from
    an unreadable link). Reaching a root pid without a match ⇒ ``NOT_ANCESTOR``.
    """
    if ancestor_pid <= 0 or descendant_pid <= 0:
        return Ancestry.UNKNOWN
    if ancestor_pid == descendant_pid:
        return Ancestry.ANCESTOR
    current = descendant_pid
    for _ in range(_MAX_HOPS):
        parent = ppid_of(current)
        if parent is None:
            return Ancestry.UNKNOWN
        if parent == ancestor_pid:
            return Ancestry.ANCESTOR
        if parent in _ROOT_PIDS:
            return Ancestry.NOT_ANCESTOR
        current = parent
    # Hop budget exhausted without resolving the chain → indeterminate, not a verdict.
    return Ancestry.UNKNOWN


class LinuxProcAncestry:
    """Linux adapter: read ``/proc/<pid>/stat`` to resolve each PPID.

    ``/proc/<pid>/stat`` field 4 (1-indexed) is the parent pid. The comm field
    (field 2) is parenthesised and may itself contain spaces/parens, so we split on
    the LAST ``")"`` and index into the remainder — the canonical robust parse.
    """

    def __init__(self, proc_root: Path | None = None) -> None:
        self._proc_root = proc_root or Path("/proc")

    def _ppid_of(self, pid: int) -> int | None:
        try:
            raw = (self._proc_root / str(pid) / "stat").read_text(encoding="utf-8")
        except (OSError, ValueError):
            return None
        rparen = raw.rfind(")")
        if rparen < 0:
            return None
        fields = raw[rparen + 1 :].split()
        # After the ")", fields are: state ppid ... → ppid is index 1.
        if len(fields) < 2:
            return None
        try:
            return int(fields[1])
        except ValueError:
            return None

    def is_ancestor(self, ancestor_pid: int, descendant_pid: int) -> Ancestry:
        return _walk(ancestor_pid, descendant_pid, self._ppid_of)


class PsProcessAncestry:
    """macOS / POSIX-without-/proc adapter: ``ps -o ppid= -p <pid>`` via ProcessRunner.

    Uses the injected :class:`ProcessRunner` so the feature/composition layers never
    touch ``subprocess`` directly. A non-zero exit, empty output, timeout, or a
    non-integer body ⇒ ``None`` (indeterminate link).
    """

    def __init__(self, runner: ProcessRunner) -> None:
        self._runner = runner

    def _ppid_of(self, pid: int) -> int | None:
        try:
            result = self._runner.run(["ps", "-o", "ppid=", "-p", str(pid)], timeout=5.0)
        except (TimeoutError, OSError):
            return None
        if result.returncode != 0:
            return None
        body = result.stdout.strip()
        if not body:
            return None
        try:
            return int(body.split()[0])
        except (ValueError, IndexError):
            return None

    def is_ancestor(self, ancestor_pid: int, descendant_pid: int) -> Ancestry:
        return _walk(ancestor_pid, descendant_pid, self._ppid_of)


class WindowsToolhelpAncestry:
    """Windows adapter: read-only ``CreateToolhelp32Snapshot`` PPID walk.

    Enumerates the process table once into a ``{pid: ppid}`` map via Toolhelp32, then
    walks the chain in-process. ``CreateToolhelp32Snapshot`` / ``Process32First`` /
    ``Process32Next`` are read-only enumeration calls — no handle is opened on the
    target and no signal is ever sent. Any ctypes/Win32 failure ⇒ every link
    resolves to ``None`` ⇒ :data:`Ancestry.UNKNOWN`.

    ``snapshot`` is injectable for tests (a ``{pid: ppid}`` dict); production passes
    ``None`` and the Toolhelp32 enumeration is performed lazily.
    """

    def __init__(self, snapshot: dict[int, int] | None = None) -> None:
        self._snapshot = snapshot

    def _table(self) -> dict[int, int] | None:
        if self._snapshot is not None:
            return self._snapshot
        return self._toolhelp_snapshot()

    @staticmethod
    def _toolhelp_snapshot() -> dict[int, int] | None:  # pragma: no cover - Windows-only path
        import ctypes
        from ctypes import wintypes

        th32cs_snapprocess = 0x00000002
        invalid_handle_value = -1

        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_char * 260),
            ]

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
            kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
            kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
            kernel32.Process32First.restype = ctypes.c_int
            kernel32.Process32First.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32)]
            kernel32.Process32Next.restype = ctypes.c_int
            kernel32.Process32Next.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32)]
            kernel32.CloseHandle.restype = ctypes.c_int
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

            handle = kernel32.CreateToolhelp32Snapshot(th32cs_snapprocess, 0)
            if not handle or handle == invalid_handle_value:
                return None
            try:
                entry = PROCESSENTRY32()
                entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
                table: dict[int, int] = {}
                if not kernel32.Process32First(handle, ctypes.byref(entry)):
                    return None
                while True:
                    table[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
                    if not kernel32.Process32Next(handle, ctypes.byref(entry)):
                        break
                return table
            finally:
                kernel32.CloseHandle(handle)
        except Exception:  # noqa: BLE001 — any Win32/ctypes failure ⇒ indeterminate.
            return None

    def _ppid_of(self, pid: int) -> int | None:
        table = self._table()
        if table is None:
            return None
        return table.get(pid)

    def is_ancestor(self, ancestor_pid: int, descendant_pid: int) -> Ancestry:
        return _walk(ancestor_pid, descendant_pid, self._ppid_of)
