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

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from dadaia_workspace.core.specs_version import RELEASE_SEMVER_RE
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


# Segment naming (ADR-1/ADR-5): alpha-N or rc-N (1-indexed, hyphenated).
_SEGMENT_RE = re.compile(r"^(alpha|rc)-\d+$")

_SEGMENT_SPEC_STUB = """\
# SPEC: {version_id} {segment} - <slug>

**Status:** Draft
**Release ID:** {version_id}
**Segment:** {segment}
**Owner:** product-engineer
**Created:** {today}

---

## Objective

(Define this segment's objective.)
"""

_SEGMENT_PLAN_STUB = """\
# PLAN: {version_id} {segment} - <slug>

**Status:** Draft
**Release ID:** {version_id}
**Segment:** {segment}
**Owner:** product-engineer
**Created:** {today}

---

## Approach

(Define the implementation approach for this segment.)

## Validation Dependency Table

| Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
|---|---|---|---|---|
| WS-1 | (deliverable of this segment) | (how it is validated in isolation) | none | none |
"""

_SEGMENT_TASKS_STUB = """\
# TASKS: {version_id} {segment} - <slug>

**Status:** Draft
**Release ID:** {version_id}
**Segment:** {segment}
**Owner:** product-engineer
**Created:** {today}

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

## Tasks

- [ ] T1 - (Add tasks here)
  - **Owner:** software-engineer
  - **Acceptance:** (acceptance criteria)
"""


def scaffold_release_segment(
    specs_dir: Path,
    version_id: str,
    segment: str,
    force: bool = False,
) -> ScaffoldResult:
    """Scaffold a release **segment** under specs/releases/<version_id>/<segment>/.

    Creates SPEC.md + PLAN.md + TASKS.md stubs for an `alpha-N` or `rc-N` segment
    (ADR-1/ADR-5). The parent release directory is created if absent.

    Args:
        specs_dir: Target specs/ directory.
        version_id: SemVer release id (e.g. ``v0.1.6``); must match ``^v\\d+\\.\\d+\\.\\d+$``.
        segment: Segment name; must match ``^(alpha|rc)-\\d+$`` (e.g. ``alpha-1``, ``rc-2``).
        force: Overwrite existing files when True; otherwise skip them.

    Returns:
        ScaffoldResult with created/skipped/errors.

    Raises:
        ValueError: If version_id is not SemVer or segment is malformed.
    """
    if not RELEASE_SEMVER_RE.match(version_id):
        raise ValueError(
            f"version_id {version_id!r} does not match SemVer pattern "
            "^v<MAJOR>.<MINOR>.<PATCH>$ (e.g. v0.1.6)."
        )
    if not _SEGMENT_RE.match(segment):
        raise ValueError(
            f"segment {segment!r} is not valid. Use 'alpha-<N>' or 'rc-<N>' "
            "(1-indexed, hyphenated), e.g. alpha-1, rc-2."
        )

    result = ScaffoldResult()
    today = date.today().isoformat()
    seg_dir = specs_dir / "releases" / version_id / segment
    ctx = {"version_id": version_id, "segment": segment, "today": today}

    def _write(path: Path, content: str) -> None:
        if path.exists() and not force:
            result.skipped.append(path)
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            result.created.append(path)
        except OSError as exc:
            result.errors.append(f"Failed to write {path}: {exc}")

    _write(seg_dir / "SPEC.md", _SEGMENT_SPEC_STUB.format(**ctx))
    _write(seg_dir / "PLAN.md", _SEGMENT_PLAN_STUB.format(**ctx))
    _write(seg_dir / "TASKS.md", _SEGMENT_TASKS_STUB.format(**ctx))

    return result
