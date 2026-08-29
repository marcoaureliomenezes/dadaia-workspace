"""``dadaia tmp gc`` — the FR29/T-043-44 orphan backstop (v0.4.3 alpha-5, WS-G).

The doctrine (SPEC segment `alpha-5`): "an artifact dies when the thing it exists for
dies, not when a clock says so. Calendar-based deletion survives ONLY in FR29's
backstop." Every OTHER GC capability this release ships is event-driven — it fires
because something specific happened (a push landed, a release closed, the PostToolUse
reconciler's own throttled pass). This module is the deliberate exception: a
manually-invoked (or ``SessionStart``-invoked) sweep that catches whatever the
event-driven mechanisms missed, using nothing but age as its signal. It never imports
``hooks`` (features must not import hooks — this module is a self-contained
``features``-layer sibling of FR24's ``features.chokepoints.service``, not a caller of
it) and duplicates its small, already-proven AG.1 lane-guard idiom locally rather than
reaching across a layer/feature boundary for it.

Two lanes, one dataclass outcome (:class:`TmpGcOutcome`):

(a) **Dated scratch** — ``.dadaia/tmp/<agent>/<YYYYMMDD>/`` directories whose OWN
    embedded calendar date (never mtime, which floats every time a file inside is
    touched) is more than :data:`_MAX_AGE_DAYS` days before "now". A directory name
    that does not match ``^\\d{8}$`` (or is not a real calendar date) is never a
    candidate — A29.2's "never deletes ... a non-dated path".
(b) **Cache directories** — any directory anywhere under ``.dadaia`` whose NAME
    contains ``cache`` (case-insensitive), regardless of age — evidence this release
    measured (FR28/T-043-43): duplicate mypy caches recreated under ``.dadaia/tmp/**``
    faster than a purely event-driven sweep would catch them. The walk never descends
    into the managed venv (``.dadaia/.venv`` — an "Artifacts / managed environment" in
    the workspace doctor's own taxonomy, never a GC target) or the PROTECTED
    session-identity store (``.dadaia/sessions``), and never matches or descends into a
    symlinked directory (AG.1).

A third, calendar-based lane used to also sweep orphaned session throttle/sentinel
markers here (``reconciler-last-<sid>`` / ``ctx-inject-fired-<sid>``) — release 0.5.1 K2
("presence owns liveness end-to-end") retired it: every advisory marker under
``.dadaia/tmp/`` this codebase writes is now reaped by the ONE reaper,
:func:`dadaia_workspace.features.spec_context.presence.gc`, on the PostToolUse
reconciler's own throttle cadence and at ``doctor --fix`` — a second, independent,
calendar-gated copy of that exact sweep is exactly the kind of duplicated-TTL-authority
this codebase's bug history warns against.

AG.1 lane guard, uniformly across every target: resolved before removal, refused if the
resolved path falls outside ``.dadaia/``, and a symlinked directory is never followed —
mirrors ``features.chokepoints.service`` (FR24/T-043-39), the established precedent for
this exact idiom in this segment.

Idempotent by construction (A29.1): every lane re-derives its candidate set from the
filesystem on each call, so once a candidate is gone (deleted by a prior run, or never
existed) it is simply absent from the next scan — no separate "already processed" state
is needed or kept.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["TmpGcOutcome", "run_tmp_gc"]

#: The ONE age threshold this whole verb is built around (FR29: "the only
#: calendar-based deletion in the release"). Lane (a) measures it against a dated
#: directory's OWN embedded date; lane (c) measures it against a marker's mtime (no
#: embedded date to read). Lane (b) is name-matched and deliberately unconditional on
#: age — a cache directory is safe to delete the moment it is discovered, at any age.
_MAX_AGE_DAYS = 3
_MAX_MARKER_AGE_SECONDS = _MAX_AGE_DAYS * 86400

#: ``.dadaia/tmp/<agent>/<YYYYMMDD>/`` — the dated-scratch directory-name shape.
_DATED_DIR_RE = re.compile(r"^\d{8}$")

#: Lane (b)'s name match — case-insensitive substring, matching the real-workspace
#: evidence this release measured (``mypy-cache``, ``mypy_cache``,
#: ``mypy-cache-final``, ``mypy-cache-noStubs``, ...).
_CACHE_NAME_RE = re.compile("cache", re.IGNORECASE)

#: Top-level ``.dadaia/`` zones the cache walk never descends into: ``.venv`` is a
#: managed environment (never a GC target, and walking it would be both wasteful and
#: risk matching an installed package's own "*cache*"-named data directory);
#: ``sessions`` is the PROTECTED session-identity store (``DADAIA.md`` §3) — this verb
#: never even walks it, let alone deletes from it.
_CACHE_SWEEP_EXCLUDED_TOP_LEVEL: frozenset[str] = frozenset({".venv", "sessions"})


@dataclass(frozen=True)
class TmpGcOutcome:
    """Result of one FR29/T-043-44 sweep.

    Every field is a tuple of ``.dadaia``-relative POSIX paths (never absolute paths —
    consistent with keeping report/handoff evidence free of operator-local paths),
    sorted for determinism. In dry-run mode the tuples name what WOULD be removed
    (A29.3); in real mode they name what WAS actually removed — a target that could not
    be removed (a swallowed ``OSError``) is silently absent from both its own lane
    tuple and ``lane_guard_refused`` (best-effort, matching the segment's established
    fail-open posture for GC sweeps).
    """

    dry_run: bool
    scratch_dirs: tuple[str, ...] = ()
    cache_dirs: tuple[str, ...] = ()
    lane_guard_refused: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        """Count of items acted on (or, in dry-run, that would be) across all lanes."""
        return len(self.scratch_dirs) + len(self.cache_dirs)


def _resolved_within(path: Path, boundary: Path) -> bool:
    """AG.1: True iff *path*, fully resolved (symlinks included), falls under
    *boundary* (already resolved). Mirrors ``features.chokepoints.service.
    _resolved_within`` / ``hooks.sdd_post_gate._resolved_within`` — the established
    deletion-lane-guard idiom in this codebase: resolve, then ``relative_to`` inside
    ``try/except``, never a string-prefix check (CWE-22 class)."""
    try:
        path.resolve().relative_to(boundary)
    except (ValueError, OSError):
        return False
    return True


def _relpath(path: Path, boundary: Path) -> str:
    try:
        return path.relative_to(boundary).as_posix()
    except ValueError:
        return path.as_posix()


def _sorted_real_subdirs(root: Path) -> list[Path]:
    """Non-recursive, sorted subdirectories of *root* — a symlinked entry is EXCLUDED
    outright (AG.1: never follow, and never even treat as a candidate)."""
    try:
        entries = list(root.iterdir())
    except OSError:
        return []
    return sorted(p for p in entries if not p.is_symlink() and p.is_dir())


def _scratch_candidates(dadaia_root: Path, *, today: datetime, max_age_days: int) -> list[Path]:
    """Lane (a): ``tmp/<agent>/<YYYYMMDD>/`` directories older than *max_age_days*,
    measured against the directory name's OWN embedded date (never mtime)."""
    tmp_dir = dadaia_root / "tmp"
    if not tmp_dir.is_dir():
        return []
    today_date = today.date()
    candidates: list[Path] = []
    for agent_dir in _sorted_real_subdirs(tmp_dir):
        for dated_dir in _sorted_real_subdirs(agent_dir):
            if not _DATED_DIR_RE.fullmatch(dated_dir.name):
                continue
            try:
                dir_date = datetime.strptime(dated_dir.name, "%Y%m%d").date()
            except ValueError:
                continue
            if (today_date - dir_date).days > max_age_days:
                candidates.append(dated_dir)
    return candidates


def _cache_candidates(dadaia_root: Path) -> list[Path]:
    """Lane (b): every ``*cache*``-named directory under ``.dadaia``, excluding the
    managed venv and the sessions store, never descending into (or matching) a
    symlinked directory, and never descending further once a match is found (the whole
    matched directory is one candidate, not each of its own subdirectories too)."""
    if not dadaia_root.is_dir():
        return []
    candidates: list[Path] = []
    try:
        walker = os.walk(dadaia_root, followlinks=False)
        for dirpath, dirnames, _filenames in walker:
            current = Path(dirpath)
            if current == dadaia_root:
                dirnames[:] = [d for d in dirnames if d not in _CACHE_SWEEP_EXCLUDED_TOP_LEVEL]
            keep: list[str] = []
            for name in dirnames:
                child = current / name
                if child.is_symlink():
                    continue  # AG.1 — never follow OR treat as a candidate.
                if _CACHE_NAME_RE.search(name):
                    candidates.append(child)
                    continue  # matched: do not descend further into it.
                keep.append(name)
            dirnames[:] = keep
    except OSError:
        return candidates
    return sorted(candidates)


def _remove(path: Path) -> bool:
    """Best-effort delete; True iff *path* no longer exists on disk afterward."""
    try:
        if path.is_symlink():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def _apply_lane(
    targets: list[Path], dadaia_root: Path, *, dry_run: bool
) -> tuple[list[str], list[str]]:
    """AG.1 + A29.3: resolve-then-boundary-check every target before acting on it. In
    dry-run, a target that passes the guard is reported (never touched); in real mode,
    it is only reported once :func:`_remove` confirms it is actually gone (best-effort
    — a swallowed failure is silently omitted from both tuples, matching the segment's
    established fail-open GC posture)."""
    acted: list[str] = []
    refused: list[str] = []
    for path in targets:
        rel = _relpath(path, dadaia_root)
        if not _resolved_within(path, dadaia_root):
            refused.append(rel)
            continue
        if dry_run:
            acted.append(rel)
            continue
        if _remove(path):
            acted.append(rel)
    return acted, refused


def run_tmp_gc(
    workspace_root: Path,
    *,
    dry_run: bool,
    now: datetime | None = None,
) -> TmpGcOutcome:
    """FR29/A29.1-A29.4/AG.1 — run the orphan-backstop sweep once.

    Lane order matters for REAL (non-dry-run) runs: scratch (a) executes first, so a
    stale dated directory is removed as ONE unit (with anything cache-named nested
    inside it) before the cache walk (b) re-scans the tree; a cache directory nested
    inside a dated directory that SURVIVES lane (a) is still discovered and swept
    individually by lane (b). In dry-run mode nothing is actually removed between
    lanes, so a preview MAY name the same physical directory from two lanes at once —
    an honest "either would remove it" preview, never acted on twice for real.
    """
    clock = now or datetime.now(tz=UTC)
    dadaia_root = (workspace_root / ".dadaia").resolve()

    scratch_targets = _scratch_candidates(dadaia_root, today=clock, max_age_days=_MAX_AGE_DAYS)
    scratch_dirs, refused_a = _apply_lane(scratch_targets, dadaia_root, dry_run=dry_run)

    cache_targets = _cache_candidates(dadaia_root)
    cache_dirs, refused_b = _apply_lane(cache_targets, dadaia_root, dry_run=dry_run)

    return TmpGcOutcome(
        dry_run=dry_run,
        scratch_dirs=tuple(sorted(scratch_dirs)),
        cache_dirs=tuple(sorted(cache_dirs)),
        lane_guard_refused=tuple(sorted(refused_a + refused_b)),
    )
