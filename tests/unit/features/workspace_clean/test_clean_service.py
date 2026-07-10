"""Unit tests for WorkspaceCleanService (T-016-Z03).

Coverage:
  - dry-run lists stale files without deleting
  - real delete removes stale files
  - TTL is respected per zone
  - operator-created files (in .dadaia/states/root_exceptions.txt) are never deleted
  - never deletes files outside .dadaia/
  - zones: .dadaia/tmp/, .dadaia/reports/, .dadaia/handoff/

Deletion-safety is the only thing standing between clean and operator files — the
never-deletes-outside-.dadaia test (with the zone-guard folded in) is the core kept
invariant.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import pytest

from dadaia_workspace.features.workspace_clean.service import WorkspaceCleanService


def _make_workspace(tmp_path: Path) -> Path:
    """Scaffold a minimal .dadaia/ layout."""
    dadaia = tmp_path / ".dadaia"
    (dadaia / "states").mkdir(parents=True)
    (dadaia / "states" / "spec_contexts.json").write_text('{"schema_version":"2","contexts":[]}')
    for zone in ("tmp", "reports", "handoff"):
        (dadaia / zone).mkdir(parents=True)
    return tmp_path


def _write_file(path: Path, *, mtime_offset: dt.timedelta) -> Path:
    """Write an empty file with a synthetic mtime = now - mtime_offset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("content")
    target_mtime = (dt.datetime.now(tz=dt.UTC) - mtime_offset).timestamp()
    os.utime(path, (target_mtime, target_mtime))
    return path


# ---------------------------------------------------------------------------
# dry-run trio: lists without deleting, is the default, no candidates for fresh files
# ---------------------------------------------------------------------------


def test_dry_run_lists_without_deleting_and_is_default(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    stale = _write_file(
        ws / ".dadaia" / "tmp" / "agent1" / "20260101" / "old.txt",
        mtime_offset=dt.timedelta(days=3),
    )
    fresh = _write_file(
        ws / ".dadaia" / "tmp" / "agent1" / "20260101" / "fresh.txt",
        mtime_offset=dt.timedelta(minutes=5),
    )
    svc = WorkspaceCleanService(ws)

    result = svc.clean(dry_run=True)
    assert result.dry_run is True
    assert any(stale == c.path for c in result.candidates)
    assert stale.exists(), "dry-run must NOT delete files"
    fresh_candidates = [c.path.name for c in result.candidates if c.path.name == "fresh.txt"]
    assert fresh_candidates == []

    default_result = svc.clean()  # no args — must default to dry_run=True
    assert default_result.dry_run is True
    assert fresh.exists()


# ---------------------------------------------------------------------------
# per-zone real-delete + TTL — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("zone_rel", "stale_offset", "fresh_offset"),
    [
        pytest.param(
            ".dadaia/tmp/ag/20260101",
            dt.timedelta(days=3),
            dt.timedelta(hours=1),
            id="tmp-zone-ttl-2-days",
        ),
        pytest.param(
            ".dadaia/reports/ctx/ag",
            dt.timedelta(hours=49),
            dt.timedelta(hours=47),
            id="reports-zone-ttl-48-hours",
        ),
        pytest.param(
            ".dadaia/handoff/ctx",
            dt.timedelta(hours=25),
            dt.timedelta(hours=23),
            id="handoff-zone-ttl-24-hours",
        ),
    ],
)
def test_per_zone_ttl_and_real_delete(
    tmp_path: Path, zone_rel: str, stale_offset: dt.timedelta, fresh_offset: dt.timedelta
) -> None:
    ws = _make_workspace(tmp_path)
    zone_dir = ws / zone_rel
    old = _write_file(zone_dir / "old.txt", mtime_offset=stale_offset)
    fresh = _write_file(zone_dir / "fresh.txt", mtime_offset=fresh_offset)
    svc = WorkspaceCleanService(ws)

    # dry-run: old is a candidate, fresh is not.
    dry_result = svc.clean(dry_run=True)
    candidate_paths = {c.path for c in dry_result.candidates}
    assert old in candidate_paths
    assert fresh not in candidate_paths

    # real delete: old is removed and logged in result.deleted; fresh survives.
    real_result = svc.clean(dry_run=False)
    assert real_result.dry_run is False
    assert not old.exists(), "stale file should have been deleted"
    assert old in real_result.deleted
    assert fresh.exists()


# ---------------------------------------------------------------------------
# operator-exception pair (exact filename + glob) — 1 test
# ---------------------------------------------------------------------------


def test_operator_exception_files_never_deleted(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)

    protected_exact = _write_file(
        ws / ".dadaia" / "tmp" / "operator-notes.txt",
        mtime_offset=dt.timedelta(days=10),
    )
    protected_glob = _write_file(
        ws / ".dadaia" / "tmp" / "operator-screenshot.png",
        mtime_offset=dt.timedelta(days=10),
    )
    exc_file = ws / ".dadaia" / "states" / "root_exceptions.txt"
    exc_file.write_text("operator-notes.txt\n*.png\n")

    svc = WorkspaceCleanService(ws)
    result = svc.clean(dry_run=False)

    assert protected_exact.exists(), "exact-name-exempted file must never be deleted"
    assert protected_exact not in result.deleted
    assert protected_glob.exists(), "glob-exempted file must never be deleted"
    assert protected_glob not in result.deleted


# ---------------------------------------------------------------------------
# CRITICAL: never deletes outside .dadaia/, and every candidate lives under it.
# ---------------------------------------------------------------------------


def test_never_deletes_outside_dadaia_and_candidate_zone_guard(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    outside = _write_file(
        ws / "repos" / "myrepo" / "important.py",
        mtime_offset=dt.timedelta(days=100),
    )

    svc = WorkspaceCleanService(ws)
    result = svc.clean(dry_run=False)

    assert outside.exists()
    assert outside not in result.deleted

    dry_result = svc.clean(dry_run=True)
    dadaia_dir = ws / ".dadaia"
    for c in dry_result.candidates:
        assert dadaia_dir in c.path.parents or c.path.parent == dadaia_dir, (
            f"candidate path {c.path} is outside .dadaia/"
        )
