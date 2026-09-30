"""Shared leaf helpers for the SpecsDoctor decomposition (v0.1.55 FR1).

Cross-validator free functions used by THREE validator families (release, closure_audit,
governance) plus ``doctor_structural`` (a fourth). Holds no sibling-VALIDATOR
import (no ``ReleaseValidator``/``StructuralValidator`` class ever imported here or from
here) — the release-dir discovery helpers were instance methods on ``SpecsDoctor``; they
are re-homed here as free functions taking ``specs_dir`` explicitly so no family owns
them (they were cross-validator all along — SPEC-DOC-006/026/031).

``resolve_active_release`` reads which release is live and its phase; whether its state
document is valid is `release.py check`'s answer (the doctor's LEDGER-RELEASE-SCHEMA).
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.gitflow import resolve_live_release_id
from dadaia_workspace.core.release_state import RELEASE_STATE_FILENAME, read_phase

# A dir counts as a "release dir" iff it carries at least one SDD release artifact.
#
# v0.5.0 T-050-25A (A4.4): ``CLOSURE.md`` dropped — FR4/T-050-21A retired it as a
# going-forward artifact, so a lone CLOSURE.md with no SPEC/PLAN/TASKS is now an
# anomaly, never legitimate. Every archived release in this repo's own history already
# carries a surviving artifact alongside its CLOSURE.md, so this changes zero
# classification here.
RELEASE_ARTIFACTS: tuple[str, ...] = ("SPEC.md", "PLAN.md", "TASKS.md")
_RELEASE_ARTIFACTS = RELEASE_ARTIFACTS
# Segment dirs (ADR-1/ADR-5) live *inside* a release dir and are not themselves releases:
# alpha-N, rc-N, plus the historical `integration` segment container.
_SEGMENT_NAME_RE = re.compile(r"^(?:alpha|rc)-\d+$|^integration$")


def resolve_active_release(specs_dir: Path) -> tuple[str | None, str | None]:
    """``(release_id, phase)`` of the ONE live release (core.gitflow's reader, `release.py`'s
    `live_ids` rule), or ``(None, None)`` when there is none, several, or no readable
    phase: `release.py check` reports those defects, so no rule here judges them twice."""
    if (release_id := resolve_live_release_id(specs_dir)) is None:
        return None, None
    try:
        phase = read_phase(
            (specs_dir / "releases" / release_id / RELEASE_STATE_FILENAME).read_text("utf-8")
        )
    except OSError:
        phase = None
    return (release_id, phase) if phase else (None, None)


def is_release_dir(d: Path) -> bool:
    if not d.is_dir() or not any((d / a).exists() for a in _RELEASE_ARTIFACTS):
        return False
    # Segment dirs (alpha-N/rc-N/integration) are an orthogonal lifecycle concept,
    # not releases — they carry artifacts but their *release id* is the parent dir.
    # Exclude them from release-id-uniqueness and naming-canon invariants.
    return _SEGMENT_NAME_RE.match(d.name) is None


def iter_archive_release_dirs(arch: Path) -> list[Path]:
    """All release dirs under ``releases/_archive/`` (recursive).

    A dir qualifies only when it carries an SDD release artifact; segment containers
    (``rc-N``) are skipped by :func:`is_release_dir` while any artifact-bearing child
    is still found by the recursion.
    """
    out: list[Path] = []
    for d in sorted(p for p in arch.rglob("*") if p.is_dir()):
        if is_release_dir(d):
            out.append(d)
    return out


def iter_all_release_dirs(specs_dir: Path) -> list[tuple[Path, Path]]:
    """Enumerate every release dir across ``releases/`` and ``releases/_archive/``.

    Returns a list of ``(dir, releases_root)`` pairs. The live ``releases/`` root is
    enumerated at its top level only (a release in progress has no nested release
    dirs); the archive root is enumerated recursively.
    """
    out: list[tuple[Path, Path]] = []
    live_root = specs_dir / "releases"
    arch_root = live_root / "_archive"
    if live_root.is_dir():
        for d in sorted(p for p in live_root.iterdir() if p.is_dir()):
            if is_release_dir(d):
                out.append((d, live_root))
    if arch_root.is_dir():
        for d in iter_archive_release_dirs(arch_root):
            out.append((d, arch_root))
    return out
