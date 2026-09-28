"""Derived inventory of ``dadaia_workspace/public/**`` (v0.4.5 FR3,
``byte-golden-test-inventory-roster-split``).

The single, DERIVED source of the public-asset inventory dimension: it scans
``dadaia_workspace/public/**`` at test time so no test hand-pins a per-file roster that
drifts whenever a skill/agent/rule file is added or removed (v0.4.4 AR-1).

It reuses ``iter_public_files`` (the real ignore rules) rather than reimplementing the
include/exclude rules by hand — that walk is the EXACT enumeration ``install()``,
``doctor()`` and ``stage()`` call internally (``dadaia_workspace/infrastructure/
public_assets.py``), so this roster can never drift from the product's own discovery.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.public_assets_common import iter_public_files


def default_public_dir() -> Path:
    """The package's real ``dadaia_workspace/public/`` tree — the same root
    ``install()``/``doctor()``/``stage()`` read from by default."""
    return FileSystemPublicAssetManager()._public_dir  # noqa: SLF001


def scan(public_dir: Path | None = None) -> list[str]:
    """Every real (non-ignored) asset file under *public_dir*, POSIX-relative, sorted.

    Defaults to :func:`default_public_dir` — the real package tree. A caller
    exercising a mutated COPY of ``public/`` (never the real tree) passes that copy's
    root explicitly, so the roster stays self-consistent with whatever was actually
    scanned to produce the capture under test.
    """
    root = public_dir if public_dir is not None else default_public_dir()
    return sorted(p.relative_to(root).as_posix() for p in iter_public_files(root))
