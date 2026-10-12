"""Shared leaf helpers for the SpecsDoctor decomposition.

Cross-validator free functions used by THREE validator families (release, closure_audit,
governance) plus ``doctor_structural`` (a fourth). Holds no sibling-VALIDATOR
import (no ``ReleaseValidator``/``StructuralValidator`` class ever imported here or from
here) — the release-dir discovery helpers were instance methods on ``SpecsDoctor``; they
are re-homed here as free functions taking ``specs_dir`` explicitly so no family owns
them.

``resolve_active_release`` reads which release is live and its phase; whether its state
document is valid is `release.py check`'s answer (the doctor's LEDGER-RELEASE-SCHEMA).
"""

from __future__ import annotations

import re
from pathlib import Path

from dadaia_workspace.core.gitflow import live_release_id
from dadaia_workspace.core.release_state import CANDIDATE_RE, RELEASE_STATE_FILENAME
from dadaia_workspace.core.skill_owner import load_owner

# A dir counts as a "release dir" iff it carries at least one SDD release artifact.
RELEASE_ARTIFACTS: tuple[str, ...] = ("SPEC.md", "PLAN.md", "TASKS.md")
# Candidate dirs (rc-N) and the historical alpha-N and `integration` segments live inside
# a release dir and are not releases themselves.
_SEGMENT_NAME_RE = re.compile(rf"{CANDIDATE_RE.pattern}|^alpha-\d+$|^integration$")


def resolve_active_release(specs_dir: Path) -> tuple[str | None, str | None]:
    """``(release_id, phase)`` of the ONE live release (`live_release_id`), or
    ``(None, None)`` when there is none, several, or no readable phase: `release.py check`
    reports those defects, so no rule here judges them twice."""
    release_id = live_release_id(specs_dir)
    if release_id is None:
        return None, None
    jsonl = load_owner("dd-bug-resolution", "_jsonl")
    try:
        text = (specs_dir / "releases" / release_id / RELEASE_STATE_FILENAME).read_text("utf-8")
        phase = jsonl.parse_object(text, "").get("phase")
    except (OSError, jsonl.Unreadable):
        return None, None
    return (release_id, phase) if isinstance(phase, str) and phase else (None, None)


def is_release_dir(d: Path) -> bool:
    """A dir carrying a trio document itself, or one in an ``rc-<N>/`` candidate; a
    candidate or segment dir is never a release — its id is the parent's."""
    if not d.is_dir() or _SEGMENT_NAME_RE.match(d.name):
        return False
    return any((d / a).exists() or any(d.glob(f"rc-*/{a}")) for a in RELEASE_ARTIFACTS)


def iter_archive_release_dirs(arch: Path) -> list[Path]:
    """All release dirs under ``releases/_archive/`` (recursive).

    A dir qualifies only when it carries an SDD release artifact, its own or an
    ``rc-N/`` candidate's (:func:`is_release_dir`).
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
