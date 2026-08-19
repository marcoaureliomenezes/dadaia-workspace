"""FR29 (v0.4.3 T-043-44) — ``dadaia tmp gc``, the orphan backstop.

Intent: CONTRACT — A29.1, A29.2, A29.3, A29.4, AG.1

The **only** calendar-based deletion in this release: (a) dated scratch under
``.dadaia/tmp/<agent>/<YYYYMMDD>/`` older than 3 days, (b) any ``*cache*``-named
directory under ``.dadaia``, (c) orphaned session markers (``reconciler-last-*`` /
``ctx-inject-fired-*`` with no owning ``.dadaia/sessions/<id>.json`` record, old enough
that a just-started session's own markers are never at risk — the SessionStart-safety
property).

These fixtures drive ``run_tmp_gc`` directly against a synthetic ``.dadaia`` tree — no
real git, no real harness — mirroring ``tests/unit/features/chokepoints/
test_push_verdict_gc.py`` and ``tests/unit/hooks/test_post_gate_reap.py`` (the T-043-39/
T-043-41 precedents this task explicitly follows), including their two AG.1 lane-guard
fixture shapes.
"""

from __future__ import annotations

import json
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


def _write_marker(dadaia_root: Path, name: str, *, age_seconds: float) -> Path:
    path = dadaia_root / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("marker", encoding="utf-8")
    # Age against the SAME clock the service is given, never time.time(): mixing the
    # real clock with the frozen _NOW makes the effective age drift by the distance
    # between them, which turned a 4-day marker into a 2.99-day one at the first UTC
    # midnight after these tests were written (bug
    # tmp-gc-tests-age-files-by-the-real-clock-against-a-frozen-now).
    mtime = _NOW.timestamp() - age_seconds
    os.utime(path, (mtime, mtime))
    return path


def _write_session(dadaia_root: Path, sid: str) -> Path:
    path = dadaia_root / "sessions" / f"{sid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"session_id": sid}), encoding="utf-8")
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
# A29.2 — orphaned vs owned session markers. A marker with NO owning session record,
# old enough, is reaped; a marker whose session record still exists (owned/"live") is
# NEVER touched, however old.
# ---------------------------------------------------------------------------


def test_orphan_marker_older_than_three_days_reaped(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    marker = _write_marker(dadaia_root, "reconciler-last-ghost-session", age_seconds=4 * 86400)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert not marker.exists()
    assert outcome.orphan_markers == ("tmp/reconciler-last-ghost-session",)


def test_owned_marker_never_touched_even_when_ancient(tmp_path: Path) -> None:
    """A29.2's own words: "never deletes a live session's markers" — a session record
    existing at all is what "live/owned" means here, independent of the marker's age."""
    dadaia_root = tmp_path / ".dadaia"
    _write_session(dadaia_root, "owned-session")
    marker = _write_marker(dadaia_root, "reconciler-last-owned-session", age_seconds=30 * 86400)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert marker.exists()
    assert outcome.orphan_markers == ()


def test_fresh_orphan_marker_survives_sessionstart_safety(tmp_path: Path) -> None:
    """SessionStart-safety (A29.2): a marker for a session that has not yet written its
    own record (e.g. ctx-inject fired before the first bind) is too YOUNG to be
    considered orphaned — running gc unattended at session start can never break the
    session that just started."""
    dadaia_root = tmp_path / ".dadaia"
    marker = _write_marker(dadaia_root, "ctx-inject-fired-brand-new-session", age_seconds=5)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert marker.exists()
    assert outcome.orphan_markers == ()


def test_unrecognized_marker_prefix_never_touched(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    stray = _write_marker(dadaia_root, "some-other-file", age_seconds=30 * 86400)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert stray.exists()
    assert outcome.orphan_markers == ()


# ---------------------------------------------------------------------------
# A29.3 — dry-run reports without touching the filesystem.
# ---------------------------------------------------------------------------


def test_dry_run_reports_all_lanes_without_deleting_anything(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    stale_scratch_dir = dadaia_root / "tmp" / "software-engineer" / _dated_dir_name(days_ago=4)
    stale_scratch = _write_file(stale_scratch_dir / "note.md")
    cache_dir = dadaia_root / "tmp" / "software-engineer" / "mypy-cache"
    cache_file = _write_file(cache_dir / "x.json")
    orphan_marker = _write_marker(dadaia_root, "reconciler-last-ghost", age_seconds=4 * 86400)

    outcome = run_tmp_gc(tmp_path, dry_run=True, now=_NOW)

    assert stale_scratch.exists()
    assert cache_file.exists()
    assert orphan_marker.exists()
    assert outcome.dry_run is True
    assert outcome.scratch_dirs == (f"tmp/software-engineer/{_dated_dir_name(days_ago=4)}",)
    assert outcome.cache_dirs == ("tmp/software-engineer/mypy-cache",)
    assert outcome.orphan_markers == ("tmp/reconciler-last-ghost",)
    assert outcome.total == 3


# ---------------------------------------------------------------------------
# A29.1 — idempotency: a second run over the SAME tree reports (and changes) nothing.
# ---------------------------------------------------------------------------


def test_idempotent_second_real_run_is_a_pure_no_op(tmp_path: Path) -> None:
    dadaia_root = tmp_path / ".dadaia"
    _write_file(dadaia_root / "tmp" / "software-engineer" / _dated_dir_name(days_ago=4) / "n.md")
    _write_file(dadaia_root / "tmp" / "software-engineer" / "mypy-cache" / "x.json")
    _write_marker(dadaia_root, "reconciler-last-ghost", age_seconds=4 * 86400)

    first = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)
    assert first.total == 3

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


def test_lane_guard_refuses_an_orphan_marker_resolving_outside_dadaia(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dadaia_root = tmp_path / ".dadaia"
    outside = tmp_path / "outside-dadaia"
    outside.mkdir()
    real = _write_file(outside / "real.txt")

    escape = dadaia_root / "tmp" / "reconciler-last-escapee"
    escape.parent.mkdir(parents=True, exist_ok=True)
    escape.symlink_to(real)

    # Portable "age the symlink itself, not its target" simulation (not
    # ``os.utime(..., follow_symlinks=False)``): setting a symlink's OWN mtime without
    # following it requires OS write support this platform lacks (Windows raises
    # ``NotImplementedError: utime: follow_symlinks unavailable on this platform`` —
    # Linux/BSD ``utimensat`` supports it, Windows does not). Production code reads the
    # marker's age via ``path.lstat().st_mtime`` (never ``stat()``, precisely so a
    # symlink's own timestamp — not its target's — decides candidacy); READING a
    # symlink's own stat (``os.stat(path, follow_symlinks=False)``, what ``Path.lstat``
    # calls) is universally supported, only the WRITE side is platform-limited.
    # Monkeypatching ``Path.lstat`` to report an aged mtime for this exact symlink
    # exercises the identical age-comparison branch on every platform — same idiom as
    # the v0.4.2 unreadable-file precedent (monkeypatched ``Path.read_text``) — matched
    # by value equality, because ``run_tmp_gc`` builds its own ``Path`` instance for the
    # same file via ``iterdir()``.
    old_mtime = _NOW.timestamp() - (10 * 86400)
    real_lstat_result = os.lstat(escape)
    aged_stat = os.stat_result(
        (
            real_lstat_result.st_mode,
            real_lstat_result.st_ino,
            real_lstat_result.st_dev,
            real_lstat_result.st_nlink,
            real_lstat_result.st_uid,
            real_lstat_result.st_gid,
            real_lstat_result.st_size,
            int(old_mtime),
            int(old_mtime),
            int(old_mtime),
        ),
        {"st_atime": old_mtime, "st_mtime": old_mtime, "st_ctime": old_mtime},
    )
    real_lstat = Path.lstat

    def _lstat_aged(self: Path) -> os.stat_result:
        if self == escape:
            return aged_stat
        return real_lstat(self)

    monkeypatch.setattr(Path, "lstat", _lstat_aged)

    outcome = run_tmp_gc(tmp_path, dry_run=False, now=_NOW)

    assert real.exists()
    assert escape.exists()
    assert outcome.orphan_markers == ()
    assert outcome.lane_guard_refused == ("tmp/reconciler-last-escapee",)


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
    _write_marker(dadaia_root, "reconciler-last-ghost", age_seconds=4 * 86400)

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
    # never raises — but the UNRELATED marker lane still completed its own sweep.
    assert stale_dir.exists()
    assert outcome.scratch_dirs == ()
    assert outcome.orphan_markers == ("tmp/reconciler-last-ghost",)
