"""Shared leaf helpers for the SpecsDoctor decomposition (v0.1.55 FR1).

Pure leaf module: the cross-validator free functions used by THREE validator families
(release, closure_audit, governance). Imports only stdlib; holds no sibling-validator import.

``read_active_md`` is the public name of the former ``doctor._read_active_md`` (R-2 external
surface: ``cli/commands/specs.py`` consumes it directly). The release-dir discovery helpers were
instance methods on ``SpecsDoctor``; they are re-homed here as free functions taking ``specs_dir``
explicitly so no family owns them (they were cross-validator all along — SPEC-DOC-006/026/027/031).
"""

from __future__ import annotations

import re
from pathlib import Path

# A dir counts as a "release dir" iff it carries at least one SDD release artifact.
# Public name (v0.1.81 FR2): reused by doctor_release's partial-archive invariant
# (SPEC-DOC-039) so both checks share one canonical artifact-filename set.
RELEASE_ARTIFACTS: tuple[str, ...] = ("SPEC.md", "PLAN.md", "TASKS.md", "CLOSURE.md")
_RELEASE_ARTIFACTS = RELEASE_ARTIFACTS
# Segment dirs (ADR-1/ADR-5) live *inside* a release dir and are not themselves releases:
# alpha-N, rc-N, plus the historical `integration` segment container.
_SEGMENT_NAME_RE = re.compile(r"^(?:alpha|rc)-\d+$|^integration$")


def read_active_md(
    path: Path,
) -> tuple[str | None, str | None, str | None, str | None]:
    """Returns (release_id, segment, phase, error_message_or_none).

    Schema v2 (ADR-1/ADR-5): ACTIVE.md may carry an optional ``segment:`` line
    (e.g. ``alpha-2``, ``rc-1``) identifying the active segment of a release.
    ``segment`` is ``None`` for flat (pre-segment) releases — back-compatible.
    """
    if not path.exists():
        return None, None, None, "ACTIVE.md not found"
    text = path.read_text(encoding="utf-8")
    release = None
    segment = None
    phase = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("release:"):
            value = line.split(":", 1)[1].strip()
            release = value if value else None
        elif line.startswith("segment:"):
            value = line.split(":", 1)[1].strip()
            segment = value if value and value != "none" else None
        elif line.startswith("phase:"):
            value = line.split(":", 1)[1].strip()
            phase = value if value else None
    if release is None or phase is None:
        return release, segment, phase, "ACTIVE.md missing 'release:' or 'phase:' line"
    return release, segment, phase, None


def is_release_dir(d: Path) -> bool:
    if not d.is_dir() or not any((d / a).exists() for a in _RELEASE_ARTIFACTS):
        return False
    # Segment dirs (alpha-N/rc-N/integration) are an orthogonal lifecycle concept,
    # not releases — they carry artifacts but their *release id* is the parent dir.
    # Exclude them from release-id-uniqueness and naming-canon invariants.
    return _SEGMENT_NAME_RE.match(d.name) is None


def iter_archive_release_dirs(arch: Path) -> list[Path]:
    """All release dirs under ``_archive/releases/`` (recursive).

    Recurses so nested legacy milestone layouts (``v0.2.0/v0.1.9``) are
    discovered. A dir qualifies only when it carries an SDD release artifact;
    plain segment containers without artifacts are skipped (their artifact-bearing
    children are still found by the recursion).
    """
    out: list[Path] = []
    for d in sorted(p for p in arch.rglob("*") if p.is_dir()):
        if is_release_dir(d):
            out.append(d)
    return out


def is_legacy_nested_release(d: Path, releases_root: Path) -> bool:
    """True when ``d`` is a release dir nested *below* the top level of a
    releases root — i.e. its parent is itself a release dir, not the root.

    These are the documented-legacy milestone dirs (audit §4 collision:
    ``_archive/releases/v0.2.0/v0.1.{6..9}``). Per T-010-14 they earn a WARNING,
    never an ERROR, until T-010-15 renames them.
    """
    try:
        d.relative_to(releases_root)
    except ValueError:
        return False
    parent = d.parent
    return parent != releases_root and is_release_dir(parent)


def iter_all_release_dirs(specs_dir: Path) -> list[tuple[Path, Path, bool]]:
    """Enumerate every release dir across ``releases/`` and ``_archive/releases/``.

    Returns a list of ``(dir, releases_root, is_legacy_nested)`` triples. The
    active ``releases/`` root is enumerated at its top level only (a release in
    progress has no nested release dirs); the archive root is enumerated
    recursively to surface the nested-collision legacy layout.
    """
    out: list[tuple[Path, Path, bool]] = []
    live_root = specs_dir / "releases"
    if live_root.is_dir():
        for d in sorted(p for p in live_root.iterdir() if p.is_dir()):
            if is_release_dir(d):
                out.append((d, live_root, False))
    arch_root = specs_dir / "_archive" / "releases"
    if arch_root.is_dir():
        for d in iter_archive_release_dirs(arch_root):
            out.append((d, arch_root, is_legacy_nested_release(d, arch_root)))
    return out
