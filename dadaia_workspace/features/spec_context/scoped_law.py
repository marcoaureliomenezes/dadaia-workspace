"""Scoped-law placement for a context's main repo (F013, 20260830 audit).

``SpecContextService.alive()`` used to inline these two hardened writes; the concern
now has one home. Both writes are install-if-absent, never overwrite, and refuse
symlinked destinations:

- ``<repo>/AGENTS.md`` from ``public/templates/repo-AGENTS.md`` — via a SINGLE atomic
  ``os.open(O_CREAT|O_EXCL|O_NOFOLLOW)`` so "already exists", "is a symlink" (dangling
  or not) and "was swapped mid-window" are ONE indivisible refusal (v0.4.3 T-043-23,
  CWE-367/CWE-59).
- ``<repo>/tests/AGENTS.md`` from ``public/templates/tests-AGENTS.md`` — ONLY where a
  real ``tests/`` directory already exists (v0.7.0 FR3/T-070-07: never invent the
  directory, never overwrite a repo's own scoped law, refuse symlinked dir/dest).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

__all__ = ["install_scoped_law"]


def install_scoped_law(repo_path: Path, public_dir: Path) -> list[str]:
    """Install the scoped law files into *repo_path*; return the repo-relative paths
    written (empty when everything was already in place or refused)."""
    touched: list[str] = []

    repo_agents_dst = repo_path / "AGENTS.md"
    repo_agents_src = public_dir / "templates" / "repo-AGENTS.md"
    if not repo_path.is_symlink() and repo_agents_src.exists():
        open_flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(repo_agents_dst, open_flags, 0o644)
        except OSError:
            pass  # exists, is a symlink, or was raced mid-window — refused, no-op.
        else:
            with os.fdopen(fd, "wb") as fh:
                fh.write(repo_agents_src.read_bytes())
            touched.append("AGENTS.md")

    tests_agents_dst = repo_path / "tests" / "AGENTS.md"
    tests_agents_src = public_dir / "templates" / "tests-AGENTS.md"
    tests_dir = repo_path / "tests"
    if (
        tests_dir.is_dir()
        and not tests_dir.is_symlink()  # a symlinked tests/ escapes the repo tree
        and not tests_agents_dst.exists()
        # A DANGLING destination symlink reports not-exists yet copy2 would write
        # through it — same refusal posture as the repo-AGENTS seam above.
        and not tests_agents_dst.is_symlink()
        and tests_agents_src.exists()
    ):
        shutil.copy2(tests_agents_src, tests_agents_dst)
        touched.append(Path("tests", "AGENTS.md").as_posix())

    return touched
