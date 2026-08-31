"""Scaffolder for SDD release-lifecycle specs directory structure.

Pure module — no I/O outside the supplied specs_dir/templates_dir.
Creates the canonical SDD directory tree for new repositories.

``scaffold()`` is a thin, CLI-facing wrapper (v0.5.1 K4): "what a specs tree
contains" lives ONCE, in :data:`~dadaia_workspace.features.specs.canon.CANON` — this
module folds over that ONE table (no second, hand-kept file list) and adapts its
result shape to the long-standing :class:`ScaffoldResult` (created/skipped/errors)
contract every caller (``cli/commands/specs.py``'s ``init`` verb, this module's own
test suite) already depends on.
"""

from __future__ import annotations

from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE

__all__ = ["RELEASE_SEMVER_RE", "scaffold"]

from dataclasses import dataclass, field
from pathlib import Path

from dadaia_workspace.features.specs import canon


@dataclass
class ScaffoldResult:
    """Result of a scaffold() call."""

    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def scaffold(
    specs_dir: Path,
    project_name: str,
    force: bool,
    templates_dir: Path,
) -> ScaffoldResult:
    """Scaffold the SDD release-lifecycle directory structure — scaffold is canon
    rendered (:func:`~dadaia_workspace.features.specs.canon.scaffold`).

    Args:
        specs_dir: Target specs/ directory (will be created if absent).
        project_name: Human-readable project name used in rendered templates.
        force: If True, overwrite existing files. If False, skip existing files.
        templates_dir: Directory containing the canonical templates
            (``dadaia_workspace/public/templates/``); its sibling ``../scaffold/``
            supplies every area's ``AGENTS.md``/memory-atom source content.

    Returns:
        ScaffoldResult with lists of created, skipped, and error entries.
    """
    result = ScaffoldResult()
    public_dir = templates_dir.parent
    required_dests: list[str] = [
        entry.dest for entry in canon.CANON if entry.required_at_birth and entry.dest
    ]
    pre_existing = {dest for dest in required_dests if (specs_dir / dest).exists()}

    try:
        created = canon.scaffold(
            specs_dir, project_name=project_name, force=force, public_dir=public_dir
        )
    except OSError as exc:
        result.errors.append(f"Scaffold error: {exc}")
        created = []

    created_rel = {p.relative_to(specs_dir).as_posix() for p in created}
    for dest in required_dests:
        target = specs_dir / dest
        if dest in created_rel:
            result.created.append(target)
        elif dest in pre_existing and not force:
            result.skipped.append(target)

    return result
