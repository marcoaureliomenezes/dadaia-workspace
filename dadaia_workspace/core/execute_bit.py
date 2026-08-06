"""Whether this platform has a POSIX execute bit at all.

Four surfaces independently asked "is this file executable?" — the managed git
chokepoints, the kimi shims, the codex hook wrappers, and the spec-context doctor — and
all four assumed the answer was meaningful everywhere. On Windows it is not: NTFS has no
POSIX mode bits, so ``st_mode & S_IXUSR`` is always false and ``os.access(p, X_OK)`` is
always denied. Every managed script therefore read ``[drift] (not executable)``, and the
prescribed repair could never clear it, because ``chmod`` on Windows only toggles the
read-only attribute (bug doctor-reports-unrepairable-exec-bit-drift-on-windows).

Git on Windows carries the executable flag in its own index, not in the filesystem, so
there is nothing for the workspace to inspect or repair there. One definition, so the
next surface that needs the question cannot answer it differently.
"""

from __future__ import annotations

import os

_POSIX = os.name != "nt"

#: True where a file's execute permission is a real, inspectable, settable filesystem
#: property. False on Windows, where the concept does not exist.
PLATFORM_HAS_EXECUTE_BIT: bool = _POSIX

#: True where the OS can launch a ``#!``-headed script directly. On Windows it cannot —
#: ``CreateProcess`` rejects a ``.sh`` with ``[WinError 193] %1 is not a valid Win32
#: application`` — so probing a projected wrapper by running it reports a failure that
#: says nothing about the wrapper. Same predicate as above today, deliberately a separate
#: name: they are different questions, and a later platform could answer them differently.
PLATFORM_RUNS_POSIX_SCRIPTS: bool = _POSIX
