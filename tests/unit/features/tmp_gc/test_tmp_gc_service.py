"""FR29 (v0.4.3 T-043-44) — ``dadaia tmp gc``, the orphan backstop.

Intent: CONTRACT — A29.1, A29.3, A29.4, AG.1

The **only** calendar-based deletion in this codebase: (a) dated scratch under
``.dadaia/tmp/<agent>/<YYYYMMDD>/`` older than 3 days, (b) any ``*cache*``-named
directory under ``.dadaia``. A third, calendar-gated lane used to also sweep orphaned
session throttle/sentinel markers here — release 0.5.1 K2 retired it in favor of the
ONE reaper, ``features.spec_context.presence.gc`` (event-driven, tested in
``tests/unit/features/spec_context/test_presence_gc.py``).

These fixtures drive ``run_tmp_gc`` directly against a synthetic ``.dadaia`` tree — no
real git, no real harness — mirroring ``tests/unit/features/chokepoints/
test_push_verdict_gc.py`` (the T-043-39 precedent this task explicitly follows),
including its AG.1 lane-guard fixture shape.
"""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.features.tmp_gc.service import TmpGcOutcome, run_tmp_gc

_NOW = datetime(2026, 8, 18, 0, 0, 0, tzinfo=UTC)


def _dated_dir_name(*, days_ago: int) -> str:
    return (_NOW - timedelta(days=days_ago)).strftime("%Y%m%d")


def _write_file(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# A29.1/A29.2 — dated-scratch age boundary. "Older than 3 days" is a STRICT
# inequality: exactly 3 days old survives, 4+ dies.
# ---------------------------------------------------------------------------


def test_two_day_old_scratch_dir_survives(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    survivor = _write_file(
        dadaia_root / "tmp" / "software-engineer" / _dated_dir_name(days_ago=2) / "note.md"
    )

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert survivor.exists()
    assert outcome.scratch_dirs == ()


def test_four_day_old_scratch_dir_deleted(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    victim_dir = dadaia_root / "tmp" / "software-engineer" / _dated_dir_name(days_ago=4)
    victim = _write_file(victim_dir / "note.md")

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert not victim.exists()
    assert not victim_dir.exists()
    assert outcome.scratch_dirs == (f"tmp/software-engineer/{_dated_dir_name(days_ago=4)}",)


def test_exactly_three_day_old_scratch_dir_survives(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    survivor_dir = dadaia_root / "tmp" / "software-engineer" / _dated_dir_name(days_ago=3)
    survivor = _write_file(survivor_dir / "note.md")

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert survivor.exists()
    assert outcome.scratch_dirs == ()


def test_non_dated_path_under_tmp_never_touched(tmp_path: Path) -> None:
    """A29.2's "never deletes ... a non-dated path" — a directory whose name is NOT
    ``^\\d{8}$`` (e.g. a tool's own working dir) is never a scratch candidate, no
    matter how old its mtime is."""
    dadaia_root = tmp_path / ".dadaia"
    doc = _write_file(dadaia_root / "tmp" / "AGENTS.md")
    ancient = _write_file(dadaia_root / "tmp" / "mypy-check" / "notes.txt")
    old_mtime = _NOW.timestamp() - (30 * 86400)
    os.utime(ancient, (old_mtime, old_mtime))

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert doc.exists()
    assert ancient.exists()
    assert outcome.scratch_dirs == ()


# ---------------------------------------------------------------------------
# Cache-directory sweep — name-matched, unconditional on age; excludes the managed
# venv and the PROTECTED session-identity store.
# ---------------------------------------------------------------------------


def test_cache_named_directory_swept_regardless_of_age(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    fresh_cache = _write_file(dadaia_root / "tmp" / "software-engineer" / "mypy-cache" / "3.12")

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert not fresh_cache.exists()
    assert not (dadaia_root / "tmp" / "software-engineer" / "mypy-cache").exists()
    assert outcome.cache_dirs == ("tmp/software-engineer/mypy-cache",)


def test_cache_dir_nested_inside_a_surviving_dated_dir_is_still_swept(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    dated = _dated_dir_name(days_ago=1)
    nested_cache = _write_file(
        dadaia_root / "tmp" / "software-engineer" / dated / "mypy-cache" / "f.json"
    )
    sibling = _write_file(dadaia_root / "tmp" / "software-engineer" / dated / "notes.md")

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert not nested_cache.exists()
    assert sibling.exists()  # the dated dir itself survives (only 1 day old)
    assert outcome.cache_dirs == (f"tmp/software-engineer/{dated}/mypy-cache",)
    assert outcome.scratch_dirs == ()


def test_cache_sweep_excludes_managed_venv_and_sessions_store(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    venv_cache = _write_file(dadaia_root / ".venv" / "lib" / "somepkg-cache" / "x.txt")
    sessions_cache = _write_file(dadaia_root / "sessions" / "cache-decoy" / "x.txt")

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert venv_cache.exists()
    assert sessions_cache.exists()
    assert outcome.cache_dirs == ()


# ---------------------------------------------------------------------------
# A29.3 — dry-run reports without touching the filesystem.
# ---------------------------------------------------------------------------


def test_dry_run_reports_all_lanes_without_deleting_anything(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    stale_scratch_dir = dadaia_root / "tmp" / "software-engineer" / _dated_dir_name(days_ago=4)
    stale_scratch = _write_file(stale_scratch_dir / "note.md")
    cache_dir = dadaia_root / "tmp" / "software-engineer" / "mypy-cache"
    cache_file = _write_file(cache_dir / "x.json")

    outcome = run_tmp_gc(tmp_path, dry_run=True, now=_NOW)

    assert stale_scratch.exists()
    assert cache_file.exists()
    assert outcome.dry_run is True
    assert outcome.scratch_dirs == (f"tmp/software-engineer/{_dated_dir_name(days_ago=4)}",)
    assert outcome.cache_dirs == ("tmp/software-engineer/mypy-cache",)
    assert outcome.total == 2


# ---------------------------------------------------------------------------
# A29.1 — idempotency: a second run over the SAME tree reports (and changes) nothing.
# ---------------------------------------------------------------------------


def test_idempotent_second_real_run_is_a_pure_no_op(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    _write_file(dadaia_root / "tmp" / "software-engineer" / _dated_dir_name(days_ago=4) / "n.md")
    _write_file(dadaia_root / "tmp" / "software-engineer" / "mypy-cache" / "x.json")

    first = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)
    assert first.total == 2

    second = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert second == TmpGcOutcome(dry_run=False)


# ---------------------------------------------------------------------------
# AG.1 — every deletion target is resolved before removal, refused if the resolved
# target falls outside .dadaia/, and a symlinked directory is never followed. Mirrors
# tests/unit/features/chokepoints/test_push_verdict_gc.py's two lane-guard fixtures.
# ---------------------------------------------------------------------------


def test_lane_guard_never_follows_a_symlinked_agent_directory(tmp_path: Path) -> None:
    """Isolates the "never follow a symlinked directory" clause: the decoy's real
    target lives INSIDE .dadaia/ itself, so a bare "resolves inside .dadaia/" check
    would happily accept it — only the non-following walk keeps it safe. Verified with
    the T-043-39/41 trick during development: temporarily allowing traversal through
    the symlink makes the decoy get discovered and reaped, proving the guard is
    load-bearing."""
    dadaia_root = tmp_path / ".dadaia"
    real_target = dadaia_root / "states" / "decoy-agent-dir"
    decoy = _write_file(real_target / _dated_dir_name(days_ago=10) / "secret.md")

    tmp_dir = dadaia_root / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "linked-agent").symlink_to(real_target, target_is_directory=True)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert decoy.exists()
    assert (tmp_dir / "linked-agent").exists()
    assert outcome.scratch_dirs == ()
    assert outcome.lane_guard_refused == ()


def test_lane_guard_never_matches_a_symlinked_cache_directory(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    outside = tmp_path / "outside-dadaia"
    real_cache = outside / "real-cache"
    _write_file(real_cache / "leak.txt")

    tmp_dir = dadaia_root / "tmp" / "software-engineer"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    (tmp_dir / "linked-cache").symlink_to(real_cache, target_is_directory=True)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert real_cache.exists()
    assert (tmp_dir / "linked-cache").exists()
    assert outcome.cache_dirs == ()
    assert outcome.lane_guard_refused == ()


# ---------------------------------------------------------------------------
# Best-effort: an unlink/rmtree failure never aborts the sweep of the other lanes.
# ---------------------------------------------------------------------------


def test_unlink_failure_is_best_effort_and_does_not_abort_other_lanes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dadaia_root = tmp_path / ".dadaia"
    protected_parent = dadaia_root / "tmp" / "software-engineer"
    stale_dir = protected_parent / _dated_dir_name(days_ago=4)
    _write_file(stale_dir / "note.md")
    _write_file(dadaia_root / "tmp" / "software-engineer" / "mypy-cache" / "x.json")

    # Portable removal-failure simulation (not ``os.chmod`` on the containing
    # directory): the POSIX read-only-directory permission model is a platform no-op
    # for ``shutil.rmtree`` on Windows (the read-only attribute NTFS exposes there does
    # not block content deletion the way a POSIX write-permission bit does), so the
    # chmod-based simulation never actually denies the removal and the best-effort
    # branch goes unexercised. Monkeypatching ``shutil.rmtree`` to raise for this exact
    # target — same idiom as the v0.4.2 unreadable-file precedent (monkeypatched
    # ``Path.read_text``) — exercises the identical ``except OSError`` branch
    # identically on every platform.
    real_rmtree = shutil.rmtree

    def _rmtree_denied(path: str | os.PathLike[str]) -> None:
        if Path(path) == stale_dir:
            raise PermissionError(13, "Permission denied", str(path))
        real_rmtree(path)

    monkeypatch.setattr(shutil, "rmtree", _rmtree_denied)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    # The stale dated dir could not be removed (rmtree denied) — best-effort,
    # never raises — but the UNRELATED cache lane still completed its own sweep.
    assert stale_dir.exists()
    assert outcome.scratch_dirs == ()
    assert outcome.cache_dirs == ("tmp/software-engineer/mypy-cache",)
