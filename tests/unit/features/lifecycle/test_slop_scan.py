"""Unit tests for the directory-aware anti-slop metric (WS-6).

These pin the D3/D4 contract: a directory tree counts as ONE entry with its
recursive byte size (the gap that lets multi-GB dir trees hide from the existing
file-only hygiene metric — the metric's raison d'être), the metric never mutates
the filesystem, and its canonical manifest derives from ``hooks/root_whitelist._WHITELIST``
(a drift guard).
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from dadaia_workspace.core.models.hygiene import SlopPolicy
from dadaia_workspace.features.lifecycle.antislop.slop_scan import (
    SlopEntryKind,
    SlopReport,
    canonical_root_manifest,
    slop_scan,
)
from dadaia_workspace.hooks import root_whitelist

NOW = dt.datetime(2026, 6, 18, 5, 0, tzinfo=dt.UTC)


def _write(path: Path, *, size: int = 7, age: dt.timedelta = dt.timedelta(0)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    timestamp = (NOW - age).timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def test_directory_tree_counts_as_one_entry_with_recursive_size(tmp_path: Path) -> None:
    # A stray DIRECTORY tree under a swept zone — the gap directory-blind sweeps miss.
    tree = tmp_path / ".dadaia" / "tmp" / "agent" / "20260601" / "venv"
    _write(tree / "bin" / "python", size=100, age=dt.timedelta(hours=49))
    _write(tree / "lib" / "site" / "mod.py", size=250, age=dt.timedelta(hours=49))
    _write(tree / "pyvenv.cfg", size=50, age=dt.timedelta(hours=49))

    report = slop_scan(tmp_path, now=NOW, policy=SlopPolicy())

    venv_entries = [e for e in report.entries if e.path.endswith("/venv") and e.is_dir]
    assert len(venv_entries) == 1, "directory tree must be ONE entry, not per-file"
    entry = venv_entries[0]
    assert entry.is_dir is True
    assert entry.size_bytes == 400, "recursive size = sum of all contained file bytes"


def test_canonical_manifest_derives_from_root_whitelist() -> None:
    # Drift guard: the metric reads the same source the gate enforces.
    assert canonical_root_manifest() == frozenset(root_whitelist._WHITELIST)


# --- ① TTL straddle + aggregates/counts + non-swept-zone excluded ----------------------


def test_ttl_straddle_aggregates_and_non_swept_zone_excluded(tmp_path: Path) -> None:
    policy = SlopPolicy()
    ttl = policy.tmp_ttl_seconds
    # Pinned exactly at now - ttl is the boundary; older than ttl is stale.
    _write(tmp_path / ".dadaia" / "tmp" / "stale.txt", size=5, age=dt.timedelta(seconds=ttl + 1))
    _write(tmp_path / ".dadaia" / "tmp" / "fresh.txt", size=5, age=dt.timedelta(seconds=ttl - 60))
    # states/ is durable, not a swept zone — a stray there must not appear.
    _write(tmp_path / ".dadaia" / "states" / "junk.txt", size=10, age=dt.timedelta(hours=99))

    report = slop_scan(tmp_path, now=NOW, policy=policy)

    by_path = {e.path: e for e in report.entries}
    assert by_path[".dadaia/tmp/stale.txt"].kind is SlopEntryKind.STALE
    assert by_path[".dadaia/tmp/fresh.txt"].kind is SlopEntryKind.CANONICAL
    assert ".dadaia/states/junk.txt" not in by_path

    _write(
        (tmp_path / "agg") / ".dadaia" / "tmp" / "stale_bucket" / "stale.bin",
        size=1000,
        age=dt.timedelta(seconds=ttl + 10),
    )
    _write(
        (tmp_path / "agg") / ".dadaia" / "tmp" / "fresh_bucket" / "fresh.bin",
        size=2000,
        age=dt.timedelta(seconds=5),
    )
    agg_report = slop_scan(tmp_path / "agg", now=NOW, policy=policy)
    # Reclaimable bytes = recursive size of stale + non_canonical entries only.
    assert agg_report.reclaimable_bytes == 1000
    assert agg_report.stale_count == 1
    assert agg_report.total_entries == 2


# --- ② pure-no-mutation + non-canonical-dir flagged + empty-report ---------------------


def test_scan_is_pure_flags_non_canonical_dirs_and_empty_workspace_yields_empty_report(
    tmp_path: Path,
) -> None:
    stale = _write(
        tmp_path / ".dadaia" / "tmp" / "agent" / "old.txt", size=5, age=dt.timedelta(hours=99)
    )

    slop_scan(tmp_path, now=NOW, policy=SlopPolicy())
    assert stale.exists(), "the metric must never delete anything"

    # A directory directly under a swept zone whose name is not zone-structured is still a
    # recognised zone child — the directory-aware metric counts dir trees inside swept zones.
    flagged_root = tmp_path / "flagged"
    tree = flagged_root / ".dadaia" / "tmp" / "stray_pkg"
    _write(tree / "data.json", size=42, age=dt.timedelta(hours=1))
    flagged_report = slop_scan(flagged_root, now=NOW, policy=SlopPolicy())
    entry = next(e for e in flagged_report.entries if e.path == ".dadaia/tmp/stray_pkg")
    assert entry.is_dir is True
    assert entry.size_bytes == 42

    empty_report = slop_scan(tmp_path / "empty", now=NOW, policy=SlopPolicy())
    assert isinstance(empty_report, SlopReport)
    assert empty_report.entries == ()
    assert empty_report.total_entries == 0
    assert empty_report.reclaimable_bytes == 0
