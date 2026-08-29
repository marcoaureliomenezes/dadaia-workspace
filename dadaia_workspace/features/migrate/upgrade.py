"""``dadaia specs upgrade`` orchestration (FR-S04 / FR-S05; simplified v0.5.1 T-051-16).

Sequence (v0.5.1 K10): resolve the current pattern version, then apply the registry's
one surviving rule (:func:`~dadaia_workspace.features.migrate.registry.check_upgradable`)
-- ``current < goal`` raises :class:`~dadaia_workspace.features.migrate.registry.UpgradeRefused`
without touching the filesystem; ``current >= goal`` is a no-op except for the
unconditional template-artifact repair (bug
scaffold-repair-cannot-remediate-invalid-placeholder-atom), which runs regardless of
version since it is unrelated to the retired migration chain.

No backup is taken on either path: refusal never writes, and the no-op path's only
possible write (placeholder removal) was never backed up before this simplification
either.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.core import specs_version as _version
from dadaia_workspace.core.specs_repair import remove_placeholder_atoms
from dadaia_workspace.features.migrate import registry as _registry


@dataclass
class UpgradeResult:
    """Outcome of an upgrade run."""

    from_version: int
    to_version: int
    dry_run: bool
    no_op: bool = False
    #: Placeholder atoms removed by the unconditional template-artifact repair
    #: (planned-only when ``dry_run``).
    placeholder_removed: list[Path] = field(default_factory=list)


def upgrade(
    specs_dir: Path,
    *,
    target: int | None = None,
    dry_run: bool = False,
) -> UpgradeResult:
    """Upgrade ``specs/`` from its stamped version to ``target`` (default: canonical).

    Raises :class:`~dadaia_workspace.features.migrate.registry.UpgradeRefused` when
    the tree sits below ``target`` — see that exception's message for the fix.
    """
    current = _version.read_pattern_version(specs_dir)
    goal = _version.CANONICAL_SPECS_VERSION if target is None else target

    _registry.check_upgradable(current, goal)

    if dry_run:
        placeholder_planned = remove_placeholder_atoms(specs_dir, dry_run=True)
        return UpgradeResult(
            from_version=current,
            to_version=goal,
            dry_run=True,
            no_op=not placeholder_planned,
            placeholder_removed=placeholder_planned,
        )

    removed = remove_placeholder_atoms(specs_dir)
    return UpgradeResult(
        from_version=current,
        to_version=goal,
        dry_run=False,
        no_op=not removed,
        placeholder_removed=removed,
    )
