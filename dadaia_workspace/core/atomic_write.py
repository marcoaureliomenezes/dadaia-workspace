"""The package's door to the one atomic writer, ``dd-bug-resolution/scripts/_atomic.py`` (ADR 0246)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from dadaia_workspace.core.skill_owner import load_owner

__all__ = ["SymlinkRefusedError", "atomic_write"]


class _Writer(Protocol):
    def __call__(
        self,
        path: Path,
        content: str | bytes | None,
        *,
        preserve_mode: bool = ...,
        newline: str | None = ...,
        ensure_parent: bool = ...,
    ) -> None: ...


_owner = load_owner("dd-bug-resolution", "_atomic")
atomic_write: _Writer = _owner.atomic_write
if TYPE_CHECKING:

    class SymlinkRefusedError(OSError):
        path: Path
else:
    SymlinkRefusedError = _owner.SymlinkRefusedError
