"""File-lock Protocols — workspace-wide and per-context exclusive locks.

The concrete POSIX implementations live in
``dadaia_workspace.infrastructure.file_lock_posix``; the Windows implementation
lives in ``dadaia_workspace.infrastructure.file_lock_windows``.

``core/`` is zero-I/O — only Protocol definitions live here.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol


class WorkspaceLock(Protocol):
    """Exclusive workspace-wide lock wrapping spec_contexts.json mutations.

    Tier: operational — blocks concurrent load→mutate→dump cycles.
    On Linux/macOS: backed by ``fcntl.flock`` (POSIX).
    On Windows: backed by ``msvcrt.locking`` or raises
    ``PlatformCapabilityError`` if ``msvcrt`` is unavailable.
    """

    @contextmanager
    def acquire(self, workspace_root: Path) -> Generator[None, None, None]: ...


class ContextLock(Protocol):
    """Exclusive per-context lock wrapping git clone/rmtree for a slug.

    Two different slugs lock independently; same slug is exclusive.

    Tier: operational — same platform backing as ``WorkspaceLock``.
    """

    @contextmanager
    def acquire(self, workspace_root: Path, repo_slug: str) -> Generator[None, None, None]: ...
