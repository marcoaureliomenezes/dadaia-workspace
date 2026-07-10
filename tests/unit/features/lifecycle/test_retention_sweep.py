"""Unit tests for the directory-aware retention SWEEP (D5 — the deleter).

These pin the destructive-safety contract. ``RetentionSweep`` is the deleter layered
on the WS-6 ``slop_scan`` metric: it reclaims past-TTL / non-canonical entries from the
recognised swept ``.dadaia/`` zones via ``rmtree``/``unlink``, but ONLY when ``apply=True``,
and NEVER when an entry is (a) claimed by a live lifecycle run, (b) operator-marked
important, (c) a canonical workspace-root manifest entry, (d) outside the workspace
``.dadaia/``, or (e) a symlink whose resolved target escapes ``.dadaia/``.

CRITICAL: the deleter. Escape/important/live/canonical refusals are the
incident-prevention set — all survive.

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


# --- ① reclaim mechanics param: dry-run-default / rmtree-tree / unlink-file / -----------
#     fresh-spared / idempotent-second-apply


def test_reclaim_mechanics_matrix(tmp_path: Path) -> None:
    """dry-run is the default (deletes nothing, still reports bytes); apply=True reclaims a
    whole directory tree via rmtree AND a lone file via unlink; a fresh within-TTL entry is
    never reclaimed; a second apply reclaims nothing and survivors are byte-identical."""
    dry_run_root = tmp_path / "dry-run"
    tree = dry_run_root / ".dadaia" / "tmp" / "agent" / "20260101" / "venv"
    _write(tree / "bin" / "python", size=100, age=dt.timedelta(seconds=_TMP_TTL + 10))
    _write(tree / "pyvenv.cfg", size=50, age=dt.timedelta(seconds=_TMP_TTL + 10))
    dry_result = _sweep(dry_run_root).sweep()  # no apply kw — must preview only
    assert isinstance(dry_result, RetentionResult)
    assert dry_result.applied is False
    assert tree.exists(), "dry-run must never delete"
    assert dry_result.reclaimed_bytes == 150
    assert ".dadaia/tmp/agent/20260101/venv" in set(dry_result.reclaimed_paths)

    rmtree_root = tmp_path / "rmtree"
    rmtree_tree = rmtree_root / ".dadaia" / "tmp" / "agent" / "20260101" / "venv"
    _write(rmtree_tree / "bin" / "python", size=100, age=dt.timedelta(seconds=_TMP_TTL + 10))
    _write(
        rmtree_tree / "lib" / "site" / "mod.py", size=250, age=dt.timedelta(seconds=_TMP_TTL + 10)
    )
    _write(rmtree_tree / "pyvenv.cfg", size=50, age=dt.timedelta(seconds=_TMP_TTL + 10))
    rmtree_result = _sweep(rmtree_root).sweep(apply=True)
    assert rmtree_result.applied is True
    assert not rmtree_tree.exists(), "whole directory tree must be removed via rmtree"
    assert rmtree_result.reclaimed_bytes == 400
    assert ".dadaia/tmp/agent/20260101/venv" in set(rmtree_result.reclaimed_paths)

    unlink_root = tmp_path / "unlink"
    stale = _write(
        unlink_root / ".dadaia" / "tmp" / "stale.bin",
        size=99,
        age=dt.timedelta(seconds=_TMP_TTL + 10),
    )
    unlink_result = _sweep(unlink_root).sweep(apply=True)
    assert not stale.exists()
    assert unlink_result.reclaimed_bytes == 99
    assert ".dadaia/tmp/stale.bin" in set(unlink_result.reclaimed_paths)

    fresh_root = tmp_path / "fresh"
    fresh = _write(
        fresh_root / ".dadaia" / "tmp" / "fresh.bin",
        size=10,
        age=dt.timedelta(seconds=_TMP_TTL - 60),
    )
    fresh_result = _sweep(fresh_root).sweep(apply=True)
    assert fresh.exists()
    assert fresh_result.reclaimed_paths == ()
    assert fresh_result.reclaimed_bytes == 0

    idempotent_root = tmp_path / "idempotent"
    stale_tree = idempotent_root / ".dadaia" / "tmp" / "agent" / "stale"
    _write(stale_tree / "a.bin", size=80, age=dt.timedelta(seconds=_TMP_TTL + 10))
    survivor = _write(
        idempotent_root / ".dadaia" / "tmp" / "fresh.bin",
        size=33,
        age=dt.timedelta(seconds=_TMP_TTL - 60),
    )
    survivor_bytes = survivor.read_bytes()
    idempotent_sweep = _sweep(idempotent_root)
    first = idempotent_sweep.sweep(apply=True)
    assert first.reclaimed_bytes == 80
    assert not stale_tree.exists()
    second = idempotent_sweep.sweep(apply=True)
    assert second.reclaimed_paths == ()
    assert second.reclaimed_bytes == 0
    assert survivor.exists()
    assert survivor.read_bytes() == survivor_bytes, "surviving file must be byte-identical"


# --- ② liveness: live-claim + nested-child spared, terminal/absent reclaimed -----------


def test_liveness_gate_matrix(tmp_path: Path) -> None:
    """A live-claimed run's tmp dir (and any nested child under it) is NEVER reclaimed even
    past TTL; a terminal/absent run's tmp dir IS reclaimed next sweep (HARD, EPIC D6)."""
    live_root = tmp_path / "live"
    claimed_rel = ".dadaia/tmp/run-live"
    tree = live_root / ".dadaia" / "tmp" / "run-live"
    _write(tree / "work.tmp", size=500, age=dt.timedelta(seconds=_TMP_TTL + 99))
    result = _sweep(live_root, live_claims=frozenset({claimed_rel})).sweep(apply=True)
    assert tree.exists(), "a live run's tmp dir must NEVER be reclaimed mid-flight"
    assert claimed_rel not in set(result.reclaimed_paths)
    skipped = dict(result.skipped)
    assert skipped[claimed_rel] is RetentionSkipReason.LIVE

    nested_root = tmp_path / "nested"
    leaf = nested_root / ".dadaia" / "tmp" / "run-live" / "nested" / "old.tmp"
    _write(leaf, size=20, age=dt.timedelta(seconds=_TMP_TTL + 99))
    nested_result = _sweep(nested_root, live_claims=frozenset({claimed_rel})).sweep(apply=True)
    assert leaf.exists()
    assert all(not p.startswith(claimed_rel) for p in nested_result.reclaimed_paths)

    terminal_root = tmp_path / "terminal"
    dead_tree = terminal_root / ".dadaia" / "tmp" / "run-dead"
    _write(dead_tree / "work.tmp", size=42, age=dt.timedelta(seconds=_TMP_TTL + 99))
    terminal_result = _sweep(terminal_root, live_claims=frozenset()).sweep(apply=True)
    assert not dead_tree.exists(), "a terminal/absent run's tmp dir is reclaimed next sweep"
    assert ".dadaia/tmp/run-dead" in set(terminal_result.reclaimed_paths)


# --- important protection -----------------------------------------------------------


def test_important_marked_report_spared_and_canonical_top_level_dir_never_touched(
    tmp_path: Path,
) -> None:
    important_root = tmp_path / "important"
    important_rel = ".dadaia/reports/ctx/agent/keep.html"
    report = _write(
        important_root / ".dadaia" / "reports" / "ctx" / "agent" / "keep.html",
        size=123,
        age=dt.timedelta(seconds=SlopPolicy().reports_ttl_seconds + 999),
    )

    result = _sweep(important_root, important=frozenset({important_rel})).sweep(apply=True)

    assert report.exists(), "operator-marked important reports are never reclaimed"
    # The directory-aware candidate (the leaf dir containing the important file) is spared
    # whole — never partially deleted around an important file.
    skipped = dict(result.skipped)
    assert skipped[".dadaia/reports/ctx/agent"] is RetentionSkipReason.IMPORTANT
    assert ".dadaia/reports/ctx/agent" not in set(result.reclaimed_paths)

    # A canonical durable zone like states/ is not a swept zone; even a long-stale file
    # there must never be a sweep candidate.
    canonical_root = tmp_path / "canonical"
    states_file = _write(
        canonical_root / ".dadaia" / "states" / "spec_contexts.json",
        size=10,
        age=dt.timedelta(days=999),
    )

    canonical_result = _sweep(canonical_root).sweep(apply=True)

    assert states_file.exists()
    assert all(not p.startswith(".dadaia/states") for p in canonical_result.reclaimed_paths)


# --- symlink-escape refusal -----------------------------------


def test_symlink_escaping_dadaia_is_refused(tmp_path: Path) -> None:
    # A symlink planted inside a swept zone that resolves OUTSIDE .dadaia must be refused:
    # following it would delete an arbitrary external tree.
    outside = tmp_path / "outside_target"
    outside.mkdir()
    (outside / "precious.txt").write_bytes(b"do-not-delete")

    link = tmp_path / ".dadaia" / "tmp" / "escape"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    # A symlink is collected as a candidate unconditionally (the deleter treats it as a
    # leaf regardless of TTL — see RetentionSweep._collect_unit), so it does not need to be
    # aged past TTL to reach the escape guard. We deliberately do NOT call
    # os.utime(link, follow_symlinks=False) here: that is unavailable on Windows
    # (NotImplementedError) and is unnecessary for this assertion.

    result = _sweep(tmp_path).sweep(apply=True)

    assert outside.exists()
    assert (outside / "precious.txt").exists(), "symlink-escape must never delete outside .dadaia"
    skipped = dict(result.skipped)
    assert ".dadaia/tmp/escape" in skipped
    assert skipped[".dadaia/tmp/escape"] is RetentionSkipReason.ESCAPE
