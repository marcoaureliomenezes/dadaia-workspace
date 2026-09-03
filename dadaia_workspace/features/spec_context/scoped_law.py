"""Scoped-law placement for a context's main repo: install-if-absent, never overwrite.

Each row copies ``templates/<name>`` to ``<repo>/<dest>`` through one atomic
``O_CREAT|O_EXCL|O_NOFOLLOW`` open — an existing, symlinked or raced destination is a single
indivisible refusal; a row whose parent directory is absent or symlinked is skipped.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["install_scoped_law"]

_ROWS: tuple[tuple[str, str], ...] = (
    ("repo-AGENTS.md", "AGENTS.md"),
    ("repo-CLAUDE.md", "CLAUDE.md"),
    ("tests-AGENTS.md", "tests/AGENTS.md"),
    ("tests-CLAUDE.md", "tests/CLAUDE.md"),
)
_CREATE_FLAGS = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)


def install_scoped_law(repo_path: Path, public_dir: Path) -> list[str]:
    """Install every absent row into *repo_path*; return the repo-relative paths written."""
    touched: list[str] = []
    if repo_path.is_symlink():
        return touched
    for template, dest in _ROWS:
        src = public_dir / "templates" / template
        dst = repo_path / dest
        if not src.is_file() or not dst.parent.is_dir() or dst.parent.is_symlink():
            continue
        try:
            fd = os.open(dst, _CREATE_FLAGS, 0o644)
        except OSError:
            continue
        with os.fdopen(fd, "wb") as fh:
            fh.write(src.read_bytes())
        touched.append(dest)
    return touched
