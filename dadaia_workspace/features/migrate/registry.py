"""Ordered migration-chain registry (FR-S02 / FR-S03).

Generalizes the single ``migrate tree-v2`` transform into a registry of versioned
steps walked ``current → target``. Each step:

* declares ``from_version`` → ``to_version`` (consecutive integers),
* is **idempotent** (re-running a completed step is a safe no-op), and
* is **dry-run-capable** (computes its plan without writing).

The existing ``tree_v2`` transform is registered as the first step (v0 → v1): it moves
the legacy flat layout (``specs/foundation/`` + root ``specs/SPEC.md``) into
``specs/releases/legacy/``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dadaia_workspace.features.migrate.tree_v2 import MigrateResult, migrate_tree_v2


@dataclass(frozen=True)
class MigrationStep:
    """One versioned, idempotent, dry-run-capable migration step."""

    from_version: int
    to_version: int
    key: str
    apply: Callable[..., MigrateResult]

    def run(self, specs_dir: Path, *, dry_run: bool = False) -> MigrateResult:
        return self.apply(specs_dir, dry_run=dry_run)


#: The ordered registry. Steps MUST be consecutive (``to_version == from_version + 1``)
#: and registered in ascending order so the chain walker can splice any sub-range.
REGISTRY: tuple[MigrationStep, ...] = (
    MigrationStep(from_version=0, to_version=1, key="tree-v2", apply=migrate_tree_v2),
)


def latest_version() -> int:
    """Highest ``to_version`` reachable through the registry (0 if empty)."""
    return max((step.to_version for step in REGISTRY), default=0)


def plan(current: int, target: int) -> list[MigrationStep]:
    """Return the ordered steps that walk ``current → target``.

    Raises ``ValueError`` if ``target < current`` (no downgrades) or if the registry
    has a gap that prevents reaching ``target`` from ``current``.
    """
    if target < current:
        raise ValueError(f"cannot downgrade specs pattern ({current} → {target})")
    if target == current:
        return []
    steps: list[MigrationStep] = []
    cursor = current
    by_from = {step.from_version: step for step in REGISTRY}
    while cursor < target:
        step = by_from.get(cursor)
        if step is None:
            raise ValueError(f"no migration step registered from version {cursor}")
        steps.append(step)
        cursor = step.to_version
    return steps


def run_chain(
    specs_dir: Path,
    current: int,
    target: int,
    *,
    dry_run: bool = False,
) -> list[tuple[MigrationStep, MigrateResult]]:
    """Walk ``current → target``, running each step. Returns (step, result) pairs.

    With ``dry_run=True`` no step writes; each result reports its planned actions.
    """
    results: list[tuple[MigrationStep, MigrateResult]] = []
    for step in plan(current, target):
        results.append((step, step.run(specs_dir, dry_run=dry_run)))
    return results
