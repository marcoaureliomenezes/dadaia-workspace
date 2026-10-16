#!/usr/bin/env python3
"""The one atomic writer: symlink refusal, uuid temp sibling, mode, swap retry. Stdlib only."""

from __future__ import annotations

import contextlib
import shutil
import uuid
from pathlib import Path

from _platform import replace, write_text

__all__ = ["SymlinkRefusedError", "atomic_write", "refuse_symlink"]


class SymlinkRefusedError(OSError):
    """*path* is a symlink: the writer never replaces an operator's link nor writes its
    target (CWE-59). The verb that reports it adds the fix line."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"{path} is a symlink; refusing to write it")
        self.path = path


def refuse_symlink(path: Path) -> None:
    """The writer's one symlink rule, for a caller that swaps content in by another act."""
    if path.is_symlink():
        raise SymlinkRefusedError(path)


def atomic_write(
    path: Path,
    content: str | bytes | None,
    *,
    preserve_mode: bool = False,
    newline: str | None = "",
    ensure_parent: bool = False,
) -> None:
    """Restore *path* to *content*: write atomically, or unlink for ``None``.

    *newline* is ``Path.write_text``'s (``""`` keeps LF on every platform; ignored for bytes).
    *preserve_mode* copies the old mode onto the temp sibling; *ensure_parent* makes the parent.
    The temp sibling never survives a failure; the swap is the boundary's ``replace``.
    """
    refuse_symlink(path)
    if content is None:
        path.unlink(missing_ok=True)
        return
    if ensure_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        if isinstance(content, bytes):
            tmp.write_bytes(content)
        else:
            write_text(tmp, content, newline=newline)
        if preserve_mode and path.exists():
            with contextlib.suppress(OSError):
                shutil.copymode(path, tmp)
        replace(tmp, path)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
