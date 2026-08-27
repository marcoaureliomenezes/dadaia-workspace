"""One atomic-write primitive (release v0.4.5, FR2 / T-045-12; AR-1 ruling: UPHOLD D5).

Eleven writers across ``hooks/``, ``infrastructure/`` and ``features/`` each hand-kept
their own tmp-file + ``os.replace`` idiom; two of them diverged and leaked their temp
sibling on an injected ``os.replace`` failure (bug
``two-atomic-writers-leak-temp-file-on-injected-os-replace-failure``, superseded by this
consolidation). This module is the single home for that idiom, on the same precedent as
``core/specs_repair``: a pure ``core`` leaf shared by every consumer layer (``features``,
``infrastructure``, ``hooks``) without a forbidden sibling edge.

AR-1 conditions this module is bound to: zero ``dadaia_workspace.*`` imports (not even a
``core`` sibling), stateless (no module-level mutable state), and cleanup on *every*
failure path, for every parameter combination.

Layering: a pure ``core`` leaf — stdlib only, no upward import, no internal import.

``expected_previous`` (bug ``bugs-record-store-append-clobbers-concurrent-update-batch``,
v0.5.0 A2.9) closes the compare-then-swap race a caller doing its OWN
read-before / re-read-after check around a *separate* call to this function cannot: that
caller's re-read necessarily happens BEFORE this function starts serializing content to
its temp sibling, so a concurrent writer landing during that serialization is invisible
to the caller's check and gets silently discarded by the swap that follows. Passing
*expected_previous* moves the re-read to be the LAST thing this function does before
``os.replace`` — nothing but the comparison itself sits between the read and the swap —
and raises :class:`ConcurrentModificationError` instead of replacing when the live file
no longer matches, so a rewrite is never applied to a tree the caller never saw (never
last-write-wins, one race semantics: refuse-stale, caller retries).
"""

from __future__ import annotations

import contextlib
import os
import shutil
import uuid
from pathlib import Path


class ConcurrentModificationError(Exception):
    """Raised by :func:`atomic_write` when *expected_previous* is given and the live
    file no longer matches it at swap time.

    Checked as the LAST read this function performs, immediately before ``os.replace`` —
    the compare-then-swap gap holds nothing but the comparison itself. A pure ``core``
    type: no ``dadaia_workspace`` import (AR-1) — a caller with its own domain-specific
    stale-write error (e.g. ``core.protocols.record_store.StaleRecordWriteError``)
    catches this and re-raises its own.
    """

    def __init__(self, path: Path) -> None:
        super().__init__(f"{path} changed since it was last read; refusing to overwrite it")
        self.path = path


def atomic_write(
    path: Path,
    content: str | bytes,
    *,
    preserve_mode: bool = False,
    newline: str | None = "",
    ensure_parent: bool = False,
    expected_previous: str | bytes | None = None,
) -> None:
    """Write ``content`` to ``path`` atomically via a uuid-suffixed temp sibling + ``os.replace``.

    ``os.replace`` is atomic-over-existing on both POSIX and Windows, unlike
    ``os.rename``. The destination either ends up holding the full new content or is left
    completely unchanged — a reader never observes a partial write.

    ``content``: ``str`` writes in text mode (``encoding="utf-8"``); ``bytes`` writes in
    binary mode (no newline translation applies). ``newline`` matches the stdlib
    ``open()``/``Path.write_text`` parameter and is ignored for ``bytes`` content:
    ``""`` (the default) disables universal-newline translation, so the bytes on disk are
    exactly ``content.encode("utf-8")`` (LF-preserving on every platform); ``None``
    restores platform-default translation (``\\n`` -> ``os.linesep`` on write).
    ``preserve_mode`` copies the existing target's mode onto the temp file before the
    swap, so the atomic rename does not silently narrow it to the temp file's creation
    mode. ``ensure_parent`` creates ``path.parent`` (with parents) before writing.

    ``expected_previous``, when given, re-reads *path*'s CURRENT content (``""``/``b""``
    when it does not exist) right before ``os.replace`` — after the temp sibling is
    already fully written — and raises :class:`ConcurrentModificationError` instead of
    replacing when it no longer equals *expected_previous* (module docstring). Its kind
    (``str``/``bytes``) must match *content*'s.

    Temp cleanup is unconditional on every failure path — content-write failure, a
    refused stale swap, or ``os.replace`` failure alike — so no ``.tmp`` sibling is ever
    left behind. Cleanup itself is exception-suppressed so a cleanup-time error never
    masks the original one.
    """
    if ensure_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    replaced = False
    try:
        if isinstance(content, bytes):
            tmp.write_bytes(content)
        else:
            tmp.write_text(content, encoding="utf-8", newline=newline)
        if preserve_mode and path.exists():
            with contextlib.suppress(OSError):
                shutil.copymode(path, tmp)
        if expected_previous is not None:
            binary = isinstance(expected_previous, bytes)
            current: str | bytes
            if not path.is_file():
                current = b"" if binary else ""
            else:
                current = path.read_bytes() if binary else path.read_text(encoding="utf-8")
            if current != expected_previous:
                raise ConcurrentModificationError(path)
        os.replace(tmp, path)
        replaced = True
    finally:
        if not replaced:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)


__all__ = ["ConcurrentModificationError", "atomic_write"]
