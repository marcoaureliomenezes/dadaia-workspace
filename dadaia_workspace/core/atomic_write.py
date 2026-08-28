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
"""

from __future__ import annotations

import contextlib
import os
import shutil
import uuid
from pathlib import Path


def atomic_write(
    path: Path,
    content: str | bytes,
    *,
    preserve_mode: bool = False,
    newline: str | None = "",
    ensure_parent: bool = False,
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

    Temp cleanup is unconditional on every failure path — content-write failure or
    ``os.replace`` failure alike — so no ``.tmp`` sibling is ever left behind. Cleanup
    itself is exception-suppressed so a cleanup-time error never masks the original one.
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
        os.replace(tmp, path)
        replaced = True
    finally:
        if not replaced:
            with contextlib.suppress(OSError):
                tmp.unlink(missing_ok=True)


__all__ = ["atomic_write"]
