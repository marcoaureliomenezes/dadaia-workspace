"""Scan host for TCP listeners not present in the registry (v0.1.1 / Bug D).

Pure parsing logic + a single subprocess call to ``ss -tlnp``.  The function
is read-only: it never kills processes, never registers anything, never
writes to disk.  The CLI (``dadaia server scan``) and panel "Unregistered"
section both consume this.

Linux-only (``/proc`` required).  ``ss`` is part of the iproute2 package and
ships on every modern Linux distro.  On platforms without ``/proc``
(macOS / Windows) the function returns an empty list with an INFO log.
Use ``PLATFORM.has_proc_fs`` to guard all ``/proc`` access — never test
``sys.platform`` directly in this module.

Privacy invariant (T1): no message bodies, no file contents, no env vars
are read.  Only ``/proc/<pid>/cmdline`` (the same data ``ps`` exposes) and
``/proc/<pid>/cwd`` (the working directory).
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Iterable

from dadaia_workspace.core.models.server_registry import (
    PortEntry,
    UnregisteredListener,
)
from dadaia_workspace.core.platform import PLATFORM

logger = logging.getLogger(__name__)

# Skip privileged ports (system services, mail, DNS, etc.).
_PORT_FLOOR = 1024

# Truncation budgets for display.
_CMDLINE_MAX = 200
_CWD_MAX = 200

# ``ss -tlnp`` line format (one example):
#   LISTEN 0    4096   127.0.0.1:4999     0.0.0.0:*    users:(("dadaia",pid=3440084,fd=4))
# We pull bind + port from column 4, then optionally pid from the users:(...) trailer.
_LOCAL_ADDR_RE = re.compile(r"^(?P<bind>.+):(?P<port>\d+)$")
_USERS_PID_RE = re.compile(r'\("(?P<exe>[^"]+)",pid=(?P<pid>\d+)')


def _ss_command_output() -> str | None:
    """Return raw ``ss -tlnp`` stdout, or None if ss is unavailable / errored.

    Delegates to ``dadaia_workspace.infrastructure.subprocess_runner.SubprocessProcessRunner``
    so that this module never imports ``subprocess`` directly.
    """
    from dadaia_workspace.infrastructure.subprocess_runner import SubprocessProcessRunner

    runner = SubprocessProcessRunner()
    try:
        result = runner.run(["ss", "-tlnp"], timeout=5.0)
    except FileNotFoundError:
        logger.warning("scan: ss not found on PATH — orphan detection unavailable")
        return None
    except TimeoutError:
        logger.warning("scan: ss -tlnp timed out after 5s — orphan detection unavailable")
        return None

    if result.returncode != 0:
        logger.warning(
            "scan: ss -tlnp returned %s; stderr=%s",
            result.returncode,
            result.stderr.strip()[:200],
        )
        return None
    return result.stdout


def _parse_ss_line(line: str) -> tuple[int, str, int | None] | None:
    """Parse one ss line, returning (port, bind, pid|None) or None to skip.

    Lines we skip:
    - Header row (starts with "State")
    - Empty lines
    - Rows whose Local Address doesn't end in :<digits>
    """
    if not line or line.startswith("State"):
        return None
    parts = line.split()
    # Expect at least: State Recv-Q Send-Q Local-Addr Peer-Addr [users:...]
    if len(parts) < 4:
        return None
    local_addr = parts[3]
    m = _LOCAL_ADDR_RE.match(local_addr)
    if not m:
        return None
    try:
        port = int(m.group("port"))
    except ValueError:
        return None
    bind = m.group("bind")
    # Normalise IPv6 wildcard ``[::]`` and ``*`` to canonical forms.
    bind = bind.lstrip("[").rstrip("]")
    if bind == "*":
        bind = "0.0.0.0"

    pid: int | None = None
    if len(parts) >= 6:
        users = " ".join(parts[5:])
        pm = _USERS_PID_RE.search(users)
        if pm:
            try:
                pid = int(pm.group("pid"))
            except ValueError:
                pid = None
    return (port, bind, pid)


def _read_cmdline(pid: int) -> str:
    """Read ``/proc/<pid>/cmdline``.

    Returns empty string when ``/proc`` is unavailable on this platform.
    """
    if not PLATFORM.has_proc_fs:
        return ""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            raw = f.read()
    except (OSError, ValueError):
        return ""
    # /proc/.../cmdline uses NUL separators; replace with space.
    text = raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    if len(text) > _CMDLINE_MAX:
        text = text[: _CMDLINE_MAX - 1] + "…"
    return text


def _read_cwd(pid: int) -> str:
    """Read ``/proc/<pid>/cwd`` symlink.

    Returns empty string when ``/proc`` is unavailable on this platform.
    """
    if not PLATFORM.has_proc_fs:
        return ""
    try:
        cwd = os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return ""
    if len(cwd) > _CWD_MAX:
        cwd = cwd[: _CWD_MAX - 1] + "…"
    return cwd


def _pid_belongs_to_current_user(pid: int) -> bool:
    """Return True if ``pid`` is owned by the current UID.

    Returns False when ``/proc`` is unavailable on this platform, or when
    ``os.getuid`` does not exist (Windows).
    """
    if not PLATFORM.has_proc_fs:
        return False
    get_uid = getattr(os, "getuid", None)
    if get_uid is None:
        return False
    try:
        return bool(os.stat(f"/proc/{pid}").st_uid == get_uid())
    except OSError:
        return False


def scan_unregistered_listeners(
    registry_entries: Iterable[PortEntry],
    *,
    _output_provider: object = None,
) -> list[UnregisteredListener]:
    """Return TCP listeners not present in the registry.

    On platforms without ``/proc`` (macOS, Windows) this function returns
    ``[]`` immediately with an INFO log.  Use ``PLATFORM.has_proc_fs`` to
    detect this condition — do not compare ``sys.platform`` directly.

    Parameters
    ----------
    registry_entries:
        Current registry. Ports in this set are filtered out of the result.
    _output_provider:
        Test seam — if provided, must be callable returning the raw ss
        output. Defaults to running ``ss -tlnp`` via subprocess.

    Returns
    -------
    Sorted (by port) list of UnregisteredListener.
    """
    if not PLATFORM.has_proc_fs:
        logger.info("scan: /proc not available on this platform — orphan detection disabled")
        return []

    registered_ports = {e.port for e in registry_entries}

    raw = _ss_command_output() if _output_provider is None else _output_provider()  # type: ignore[operator]

    if raw is None:
        return []

    findings: list[UnregisteredListener] = []
    for line in raw.splitlines():
        parsed = _parse_ss_line(line)
        if parsed is None:
            continue
        port, bind, pid = parsed
        if port < _PORT_FLOOR:
            continue
        if port in registered_ports:
            continue
        # Require a pid we can attribute. Pidless listeners (NFS, Docker
        # swarm, kernel-held sockets) are noise for the operator — they're
        # not actionable from the panel. Listeners owned by other users
        # are also filtered out.
        if pid is None:
            continue
        if not _pid_belongs_to_current_user(pid):
            continue

        cmdline = _read_cmdline(pid)
        cwd = _read_cwd(pid)
        findings.append(
            UnregisteredListener(
                port=port,
                bind=bind,
                pid=pid,
                cmdline=cmdline,
                cwd=cwd,
                lan_exposed=bind in {"0.0.0.0", "::"},
            )
        )

    findings.sort(key=lambda f: f.port)
    return findings
