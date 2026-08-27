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

from dadaia_workspace.features.migrate.agent_tier_frontmatter import (
    migrate_agent_tier_frontmatter,
)
from dadaia_workspace.features.migrate.bugs_jsonl import migrate_bugs_jsonl
from dadaia_workspace.features.migrate.bugs_single_file import migrate_bugs_single_file
from dadaia_workspace.features.migrate.retired_frontmatter_keys import (
    migrate_retired_frontmatter_keys,
)
from dadaia_workspace.features.migrate.tree_v2 import MigrateResult, migrate_tree_v2


def migrate_canon_v6_stamp(specs_dir: Path, *, dry_run: bool = False) -> MigrateResult:
    """Declarative v5 -> v6 stamp-only hop (v0.5.0 T-050-06A).

    Carries no filesystem action. The canon-v6 tree-shape changes are applied by hand
    via ``specs doctor --recipe`` (FR1's explicit "no rename automation" ruling); this
    step exists solely so the migration-chain registry has a ``from_version=5`` entry,
    keeping ``dadaia specs upgrade`` (and its dry-run) from raising ``ValueError`` for
    any tree already stamped at pattern version 5.
    """
    result = MigrateResult(dry_run=dry_run)
    result.skipped.append(
        "v5 -> v6 is a stamp-only hop: run `dadaia specs doctor --recipe` for the "
        "canon-shape steps (memory file renames, specs/assets/ retirement, "
        "specs/backlog/remote-bugs/ removal) and apply them by hand."
    )
    return result


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
    MigrationStep(from_version=1, to_version=2, key="bugs-jsonl", apply=migrate_bugs_jsonl),
    # v0.1.72 FR1: the missing migration for the v0.1.61 agent_tier schema-drop — a
    # schema-drop MUST ship its migration (bug memory-agent-tier-migration-deadlock).
    MigrationStep(
        from_version=2,
        to_version=3,
        key="agent-tier-frontmatter",
        apply=migrate_agent_tier_frontmatter,
    ),
    # v0.1.73 FR1: consolidate the drifted per-hour bug logs into the single canonical
    # bugs.jsonl + collapse _archive/*.md into one archive.jsonl (operator contract,
    # bug bugs-store-fragments-into-hourly-files).
    MigrationStep(
        from_version=3,
        to_version=4,
        key="bugs-single-file",
        apply=migrate_bugs_single_file,
    ),
    # Bug specs-upgrade-emits-atoms-violating-frontmatter-schema: the agent_tier step
    # above repaired ONE dropped key; a closed schema needs the class repaired. This step
    # derives the retired set from the shipped schema, so later drops need no new step.
    MigrationStep(
        from_version=4,
        to_version=5,
        key="retired-frontmatter-keys",
        apply=migrate_retired_frontmatter_keys,
    ),
    # v0.5.0 T-050-06A: CANONICAL_SPECS_VERSION 5 -> 6 (canon-v6 tree shape, FR1). FR1
    # explicitly retires `specs upgrade`'s automated-rename surface (software-architect
    # change 3, specs/releases/0.5.0/SPEC.md FR1) — the canon-v6 shape changes (memory
    # file renames, specs/assets/ retirement, specs/backlog/remote-bugs/ removal) are
    # `specs doctor --recipe` steps, applied BY HAND (as this repo's own T-050-06
    # migration did), never automated here. This step carries NO filesystem action of
    # its own; it exists ONLY so the registry chain still resolves current=5 -> target=6
    # and the version stamp stays reachable for a tree already at v5 — an omitted step
    # here would make `dadaia specs upgrade` (and its dry-run) raise
    # ``ValueError: no migration step registered from version 5`` for every consumer
    # sitting at v5 the moment CANONICAL_SPECS_VERSION became 6.
    MigrationStep(
        from_version=5,
        to_version=6,
        key="canon-v6-stamp",
        apply=migrate_canon_v6_stamp,
    ),
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
