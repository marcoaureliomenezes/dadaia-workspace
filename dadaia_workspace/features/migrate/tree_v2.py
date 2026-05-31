"""Migration logic for `dadaia migrate tree-v2`.

Moves legacy scaffold artifacts to their canonical locations:

1. ``specs/foundation/`` → ``specs/releases/legacy/foundation/``
2. ``specs/SPEC.md`` → ``specs/releases/legacy/SPEC.md``

Both operations are idempotent: running the command twice is safe.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class MigrateResult:
    """Outcome of a tree-v2 migration run.

    Attributes:
        moved:   List of ``(src, dst)`` tuples for files/dirs that were moved.
        skipped: List of messages explaining why an action was skipped (idempotent).
        dry_run: When *True* no filesystem changes were made.
    """

    moved: list[tuple[Path, Path]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    dry_run: bool = False


def _timestamp_suffix() -> str:
    """Return a UTC timestamp string suitable for file-name suffixes."""
    return datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")


def migrate_tree_v2(specs_dir: Path, *, dry_run: bool = False) -> MigrateResult:
    """Migrate a consumer specs/ tree from the old layout to v2.

    Actions:
    1. If ``specs/foundation/`` exists: move its contents to
       ``specs/releases/legacy/foundation/``; remove the now-empty
       ``specs/foundation/`` directory.
    2. If ``specs/SPEC.md`` exists at root: move to
       ``specs/releases/legacy/SPEC.md`` (or add a timestamp suffix when the
       destination already exists to avoid clobbering).

    All operations are atomic at the file level (``shutil.move``).

    Args:
        specs_dir: Absolute path to the ``specs/`` directory being migrated.
        dry_run:   When *True*, compute and return the planned actions without
                   writing anything.

    Returns:
        A :class:`MigrateResult` describing what was (or would be) done.
    """
    result = MigrateResult(dry_run=dry_run)

    # ------------------------------------------------------------------ step 1
    foundation_src = specs_dir / "foundation"
    legacy_dir = specs_dir / "releases" / "legacy"

    if foundation_src.is_dir():
        foundation_dst = legacy_dir / "foundation"
        if foundation_dst.exists():
            result.skipped.append(
                "releases/legacy/foundation/ already exists — foundation/ not moved "
                "(already migrated)."
            )
        else:
            # Collect every file inside foundation/ for reporting
            contents = list(foundation_src.rglob("*"))
            if not dry_run:
                legacy_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(foundation_src), str(foundation_dst))
            # Report at directory level (simpler output)
            result.moved.append((foundation_src, foundation_dst))
            _ = contents  # keep for future verbose mode
    else:
        result.skipped.append("foundation/ not found — nothing to migrate (step 1).")

    # ------------------------------------------------------------------ step 2
    root_spec = specs_dir / "SPEC.md"

    if root_spec.is_file():
        legacy_spec_dst = legacy_dir / "SPEC.md"
        if legacy_spec_dst.exists():
            # Destination exists: add timestamp suffix to avoid clobbering
            suffix = _timestamp_suffix()
            legacy_spec_dst = legacy_dir / f"SPEC.{suffix}.md"

        if not dry_run:
            legacy_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(root_spec), str(legacy_spec_dst))
        result.moved.append((root_spec, legacy_spec_dst))
    else:
        result.skipped.append("SPEC.md not found at specs/ root — nothing to migrate (step 2).")

    return result
