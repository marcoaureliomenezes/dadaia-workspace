"""``dadaia specs upgrade`` orchestration (FR-S04 / FR-S05).

Sequence (mutating run):

1. **Backup-first** — snapshot ``specs/`` to ``specs_bkp/<from>→<to>-<UTC>/``.
2. **Apply chain** — walk ``current → target`` through the registry.
3. **Re-stamp** — write the new ``specs_pattern_version`` into the constitution.

Idempotent: when the tree is already at the target version the plan is empty and the
run is a no-op (no backup, no writes). Dry-run computes the plan and the would-be
backup label without touching the filesystem.

Restore-on-failure is the caller's contract: if a step raises, the backup from step 1
is the recovery point. ``upgrade()`` surfaces the backup path in the result so the CLI
can point the operator at it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.core import specs_backup as _backup
from dadaia_workspace.core import specs_version as _version
from dadaia_workspace.features.migrate import registry as _registry
from dadaia_workspace.features.migrate.tree_v2 import MigrateResult


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass
class UpgradeResult:
    """Outcome of an upgrade run."""

    from_version: int
    to_version: int
    dry_run: bool
    no_op: bool = False
    backup_path: Path | None = None
    steps: list[tuple[str, MigrateResult]] = field(default_factory=list)


def upgrade(
    specs_dir: Path,
    *,
    target: int | None = None,
    dry_run: bool = False,
    clock: Callable[[], datetime] = _utc_now,
) -> UpgradeResult:
    """Upgrade ``specs/`` from its stamped version to ``target`` (default: canonical).

    Backup-first → apply chain → re-stamp. No-op when already at target.
    """
    current = _version.read_pattern_version(specs_dir)
    goal = _version.CANONICAL_SPECS_VERSION if target is None else target

    steps = _registry.plan(current, goal)
    if not steps:
        return UpgradeResult(from_version=current, to_version=goal, dry_run=dry_run, no_op=True)

    if dry_run:
        planned = [(step.key, step.run(specs_dir, dry_run=True)) for step in steps]
        return UpgradeResult(
            from_version=current,
            to_version=goal,
            dry_run=True,
            backup_path=_backup.backup_root(specs_dir)
            / _backup.backup_label(current, goal, clock=clock),
            steps=planned,
        )

    # 1. Backup-first.
    backup_path = _backup.backup_specs(specs_dir, current, goal, clock=clock)

    # 2. Apply chain.
    applied: list[tuple[str, MigrateResult]] = []
    for step in steps:
        applied.append((step.key, step.run(specs_dir, dry_run=False)))

    # 3. Re-stamp to the goal version.
    _version.write_pattern_version(specs_dir, goal)

    return UpgradeResult(
        from_version=current,
        to_version=goal,
        dry_run=False,
        backup_path=backup_path,
        steps=applied,
    )
