"""Unit tests for the directory-aware retention SWEEP (D5 — the deleter).

These pin the destructive-safety contract. ``RetentionSweep`` is the deleter layered
on the WS-6 ``slop_scan`` metric: it reclaims past-TTL / non-canonical entries from the
recognised swept ``.dadaia/`` zones via ``rmtree``/``unlink``, but ONLY when ``apply=True``,
and NEVER when an entry is (a) claimed by a live lifecycle run, (b) operator-marked
important, (c) a canonical workspace-root manifest entry, (d) outside the workspace
``.dadaia/``, or (e) a symlink whose resolved target escapes ``.dadaia/``.

Every test is hermetic: it builds a ``.dadaia`` skeleton with ``mkdir`` under ``tmp_path``,
NEVER calls ``WorkspaceService.init``, NEVER touches the real workspace, and injects a
fixed clock so reclaim decisions are deterministic.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.features.lifecycle.antislop.retention import (
    RetentionResult,
    RetentionSkipReason,
    RetentionSweep,
)

NOW = dt.datetime(2026, 6, 20, 5, 0, tzinfo=dt.UTC)
_TMP_TTL = SlopPolicy().tmp_ttl_seconds


def _write(path: Path, *, size: int = 7, age: dt.timedelta = dt.timedelta(0)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    timestamp = (NOW - age).timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def _sweep(
    workspace_root: Path,
    *,
    live_claims: frozenset[str] = frozenset(),
    important: frozenset[str] = frozenset(),
    policy: SlopPolicy | None = None,
) -> RetentionSweep:
    return RetentionSweep(
        workspace_root,
        now=NOW,
        policy=policy or SlopPolicy(),
        live_claims=lambda: live_claims,
        important_paths=lambda: important,
    )


# --- dry-run vs apply, directory trees, reclaimed bytes ----------------------------


def test_dry_run_is_default_and_deletes_nothing(tmp_path: Path) -> None:
    tree = tmp_path / ".dadaia" / "tmp" / "agent" / "20260101" / "venv"
    _write(tree / "bin" / "python", size=100, age=dt.timedelta(seconds=_TMP_TTL + 10))
    _write(tree / "pyvenv.cfg", size=50, age=dt.timedelta(seconds=_TMP_TTL + 10))

    # Default call — no apply kw — must preview only.
    result = _sweep(tmp_path).sweep()

    assert isinstance(result, RetentionResult)
    assert result.applied is False
    assert tree.exists(), "dry-run must never delete"
    # The candidate is reported with its recursive byte size even in dry-run.
    assert result.reclaimed_bytes == 150
    reclaimed = {p for p in result.reclaimed_paths}
    assert ".dadaia/tmp/agent/20260101/venv" in reclaimed


def test_apply_reclaims_past_ttl_dir_tree_via_rmtree(tmp_path: Path) -> None:
    tree = tmp_path / ".dadaia" / "tmp" / "agent" / "20260101" / "venv"
    _write(tree / "bin" / "python", size=100, age=dt.timedelta(seconds=_TMP_TTL + 10))
    _write(tree / "lib" / "site" / "mod.py", size=250, age=dt.timedelta(seconds=_TMP_TTL + 10))
    _write(tree / "pyvenv.cfg", size=50, age=dt.timedelta(seconds=_TMP_TTL + 10))

    result = _sweep(tmp_path).sweep(apply=True)

    assert result.applied is True
    assert not tree.exists(), "whole directory tree must be removed via rmtree"
    assert result.reclaimed_bytes == 400, "recursive byte size of the reclaimed tree"
    assert ".dadaia/tmp/agent/20260101/venv" in set(result.reclaimed_paths)


def test_apply_reclaims_past_ttl_file_via_unlink(tmp_path: Path) -> None:
    stale = _write(
        tmp_path / ".dadaia" / "tmp" / "stale.bin",
        size=99,
        age=dt.timedelta(seconds=_TMP_TTL + 10),
    )

    result = _sweep(tmp_path).sweep(apply=True)

    assert not stale.exists()
    assert result.reclaimed_bytes == 99
    assert ".dadaia/tmp/stale.bin" in set(result.reclaimed_paths)


def test_fresh_within_ttl_is_never_reclaimed(tmp_path: Path) -> None:
    fresh = _write(
        tmp_path / ".dadaia" / "tmp" / "fresh.bin",
        size=10,
        age=dt.timedelta(seconds=_TMP_TTL - 60),
    )

    result = _sweep(tmp_path).sweep(apply=True)

    assert fresh.exists()
    assert result.reclaimed_paths == ()
    assert result.reclaimed_bytes == 0


# --- liveness gate (HARD, EPIC D6) -------------------------------------------------


def test_live_run_tmp_dir_not_reclaimed_even_past_ttl(tmp_path: Path) -> None:
    claimed_rel = ".dadaia/tmp/run-live"
    tree = tmp_path / ".dadaia" / "tmp" / "run-live"
    _write(tree / "work.tmp", size=500, age=dt.timedelta(seconds=_TMP_TTL + 99))

    result = _sweep(tmp_path, live_claims=frozenset({claimed_rel})).sweep(apply=True)

    assert tree.exists(), "a live run's tmp dir must NEVER be reclaimed mid-flight"
    assert claimed_rel not in set(result.reclaimed_paths)
    skipped = {path: reason for path, reason in result.skipped}
    assert skipped[claimed_rel] is RetentionSkipReason.LIVE


def test_child_of_live_claim_not_reclaimed(tmp_path: Path) -> None:
    # A live run claims its tmp root; a stale leaf nested under it must also be spared,
    # because reclaiming inside a live worker's tree is the worse incident.
    claimed_rel = ".dadaia/tmp/run-live"
    leaf = tmp_path / ".dadaia" / "tmp" / "run-live" / "nested" / "old.tmp"
    _write(leaf, size=20, age=dt.timedelta(seconds=_TMP_TTL + 99))

    result = _sweep(tmp_path, live_claims=frozenset({claimed_rel})).sweep(apply=True)

    assert leaf.exists()
    assert all(not p.startswith(claimed_rel) for p in result.reclaimed_paths)


def test_terminal_or_absent_run_tmp_is_reclaimed(tmp_path: Path) -> None:
    # No live claim => deregistered/terminal run => the past-TTL tmp dir IS reclaimed.
    tree = tmp_path / ".dadaia" / "tmp" / "run-dead"
    _write(tree / "work.tmp", size=42, age=dt.timedelta(seconds=_TMP_TTL + 99))

    result = _sweep(tmp_path, live_claims=frozenset()).sweep(apply=True)

    assert not tree.exists(), "a terminal/absent run's tmp dir is reclaimed next sweep"
    assert ".dadaia/tmp/run-dead" in set(result.reclaimed_paths)


# --- important protection -----------------------------------------------------------


def test_important_marked_report_not_reclaimed(tmp_path: Path) -> None:
    important_rel = ".dadaia/reports/ctx/agent/keep.html"
    report = _write(
        tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "keep.html",
        size=123,
        age=dt.timedelta(seconds=SlopPolicy().reports_ttl_seconds + 999),
    )

    result = _sweep(tmp_path, important=frozenset({important_rel})).sweep(apply=True)

    assert report.exists(), "operator-marked important reports are never reclaimed"
    # The directory-aware candidate (the leaf dir containing the important file) is spared
    # whole — never partially deleted around an important file.
    skipped = {path: reason for path, reason in result.skipped}
    assert skipped[".dadaia/reports/ctx/agent"] is RetentionSkipReason.IMPORTANT
    assert ".dadaia/reports/ctx/agent" not in set(result.reclaimed_paths)


# --- canonical / outside / symlink-escape refusal -----------------------------------


def test_canonical_top_level_dir_is_never_touched(tmp_path: Path) -> None:
    # A canonical durable zone like states/ is not a swept zone; even a long-stale file
    # there must never be a sweep candidate.
    states_file = _write(
        tmp_path / ".dadaia" / "states" / "spec_contexts.json",
        size=10,
        age=dt.timedelta(days=999),
    )

    result = _sweep(tmp_path).sweep(apply=True)

    assert states_file.exists()
    assert all(not p.startswith(".dadaia/states") for p in result.reclaimed_paths)


def test_symlink_escaping_dadaia_is_refused(tmp_path: Path) -> None:
    # A symlink planted inside a swept zone that resolves OUTSIDE .dadaia must be refused:
    # following it would delete an arbitrary external tree.
    outside = tmp_path / "outside_target"
    outside.mkdir()
    (outside / "precious.txt").write_bytes(b"do-not-delete")

    link = tmp_path / ".dadaia" / "tmp" / "escape"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    old = (NOW - dt.timedelta(seconds=_TMP_TTL + 99)).timestamp()
    os.utime(link, (old, old), follow_symlinks=False)

    result = _sweep(tmp_path).sweep(apply=True)

    assert outside.exists()
    assert (outside / "precious.txt").exists(), "symlink-escape must never delete outside .dadaia"
    skipped = {path: reason for path, reason in result.skipped}
    assert ".dadaia/tmp/escape" in skipped
    assert skipped[".dadaia/tmp/escape"] is RetentionSkipReason.ESCAPE


# --- idempotency --------------------------------------------------------------------


def test_second_apply_reclaims_nothing_and_survivors_are_byte_identical(tmp_path: Path) -> None:
    stale_tree = tmp_path / ".dadaia" / "tmp" / "agent" / "stale"
    _write(stale_tree / "a.bin", size=80, age=dt.timedelta(seconds=_TMP_TTL + 10))
    fresh = _write(
        tmp_path / ".dadaia" / "tmp" / "fresh.bin",
        size=33,
        age=dt.timedelta(seconds=_TMP_TTL - 60),
    )
    fresh_bytes = fresh.read_bytes()

    sweep = _sweep(tmp_path)
    first = sweep.sweep(apply=True)
    assert first.reclaimed_bytes == 80
    assert not stale_tree.exists()

    second = sweep.sweep(apply=True)
    assert second.reclaimed_paths == ()
    assert second.reclaimed_bytes == 0
    assert fresh.exists()
    assert fresh.read_bytes() == fresh_bytes, "surviving file must be byte-identical"


def test_empty_workspace_yields_empty_result(tmp_path: Path) -> None:
    (tmp_path / ".dadaia").mkdir()

    result = _sweep(tmp_path).sweep(apply=True)

    assert result.reclaimed_paths == ()
    assert result.reclaimed_bytes == 0
    assert result.skipped == ()


def test_result_to_dict_round_trips(tmp_path: Path) -> None:
    _write(
        tmp_path / ".dadaia" / "tmp" / "stale.bin",
        size=11,
        age=dt.timedelta(seconds=_TMP_TTL + 10),
    )

    result = _sweep(tmp_path).sweep()
    data = result.to_dict()

    assert data["applied"] is False
    assert data["reclaimed_bytes"] == 11
    assert ".dadaia/tmp/stale.bin" in data["reclaimed_paths"]
    assert isinstance(data["skipped"], list)
