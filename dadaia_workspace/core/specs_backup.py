"""Backup-first protection for specs migrations (FR-S03 / FR-S04).

Before any migration chain step mutates ``specs/``, the whole tree is snapshotted to
``specs_bkp/<from>→<to>-<UTC>/`` *inside the repo*. The ``specs_bkp/`` directory is
gitignored and explicitly tolerated by doctor (no false ROOT warnings). If a migration
fails, the operator restores from the most recent snapshot.

The backup root name (``specs_bkp``) is intentionally distinct from ``specs`` so a
glob/rglob over ``specs/`` never sweeps the backups back into the live tree.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

#: Backup directory name, relative to the repo root (sibling of ``specs/``) — the
#: FALLBACK location when no workspace root is resolvable above the repo.
BACKUP_DIRNAME = "specs_bkp"

#: Workspace-level backup zone (v0.1.73 FR5): backups land OUTSIDE the repo worktree so
#: the repair verb's byproduct never re-trips the preflight dirty-tree gate it repairs
#: (bug ``specs-upgrade-backup-trips-preflight-dirty-gate``).
WORKSPACE_BACKUP_ZONE = ("tmp", "specs-upgrade-backups")


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _workspace_root_above(specs_dir: Path) -> Path | None:
    """Nearest ancestor that is an initialized workspace (``.dadaia/states/`` present).

    Starts ABOVE the repo dir (``specs_dir.parent.parent``) so a stray in-repo
    ``.dadaia/`` never masquerades as the workspace. Returns ``None`` when no ancestor
    qualifies (bare fixture trees keep the sibling ``specs_bkp/`` fallback).
    """
    for candidate in specs_dir.resolve().parents:
        if candidate == specs_dir.resolve().parent:
            continue  # the repo root itself — never the workspace
        if (candidate / ".dadaia" / "states").is_dir():
            return candidate
    return None


def backup_root(specs_dir: Path) -> Path:
    """Return the backup root for this ``specs/`` dir.

    Workspace-resolvable ⇒ ``<ws>/.dadaia/tmp/specs-upgrade-backups/<repo-slug>/``
    (outside the repo worktree); otherwise the legacy sibling ``specs_bkp/``.
    """
    ws = _workspace_root_above(specs_dir)
    if ws is not None:
        slug = specs_dir.resolve().parent.name
        return ws.joinpath(".dadaia", *WORKSPACE_BACKUP_ZONE, slug)
    return specs_dir.parent / BACKUP_DIRNAME


def backup_label(
    from_version: int, to_version: int, *, clock: Callable[[], datetime] = _utc_now
) -> str:
    """Build the snapshot directory label ``<from>→<to>-<UTC>``."""
    stamp = clock().strftime("%Y%m%dT%H%M%SZ")
    return f"{from_version}→{to_version}-{stamp}"


def backup_specs(
    specs_dir: Path,
    from_version: int,
    to_version: int,
    *,
    clock: Callable[[], datetime] = _utc_now,
) -> Path:
    """Snapshot ``specs/`` to ``specs_bkp/<from>→<to>-<UTC>/`` and return its path.

    The snapshot is a full copy of the current ``specs/`` tree. The ``specs_bkp/``
    root is created on demand. Raises ``FileNotFoundError`` if ``specs_dir`` is absent.
    """
    if not specs_dir.exists():
        raise FileNotFoundError(f"specs dir does not exist: {specs_dir}")
    dest = backup_root(specs_dir) / backup_label(from_version, to_version, clock=clock)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(specs_dir, dest)
    return dest


def preserve_specs(specs_dir: Path, *, clock: Callable[[], datetime] = _utc_now) -> Path:
    """Snapshot a pre-existing ``specs/`` to ``specs_bkp/preserve-<UTC>/``.

    Used by ``context alive`` before merging missing canonical files into an
    operator-authored ``specs/`` tree, so the exact prior state is always recoverable
    (FR-S06 path a — makes the v0.2.1 T-021-15 safe-preserve claim literally true).
    """
    if not specs_dir.exists():
        raise FileNotFoundError(f"specs dir does not exist: {specs_dir}")
    stamp = clock().strftime("%Y%m%dT%H%M%SZ")
    dest = backup_root(specs_dir) / f"preserve-{stamp}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(specs_dir, dest)
    return dest
