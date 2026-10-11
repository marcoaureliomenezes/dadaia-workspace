#!/usr/bin/env python3
"""The one atomic writer: symlink refusal, uuid temp sibling, mode, swap retry. Stdlib only."""

from __future__ import annotations

import contextlib
import os
import shutil
import time
import uuid
from pathlib import Path

__all__ = ["SymlinkRefusedError", "atomic_write"]


class SymlinkRefusedError(OSError):
    """*path* is a symlink: the writer never replaces an operator's link nor writes its
    target (CWE-59). The verb that reports it adds the fix line."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"{path} is a symlink; refusing to write it")
        self.path = path


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
    The temp sibling never survives a failure. A held-open destination (``PermissionError``,
    Windows) is retried 49 times 0.01 s apart before the final raising swap; the retry is
    platform-blind because POSIX never raises it there.
    """
    if path.is_symlink():
        raise SymlinkRefusedError(path)
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
            tmp.write_text(content, encoding="utf-8", newline=newline)
        if preserve_mode and path.exists():
            with contextlib.suppress(OSError):
                shutil.copymode(path, tmp)
        for _ in range(49):
            with contextlib.suppress(PermissionError):
                return os.replace(tmp, path)
            time.sleep(0.01)
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
