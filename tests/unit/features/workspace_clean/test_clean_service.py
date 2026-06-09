"""Unit tests for WorkspaceCleanService (T-016-Z03).

Coverage:
  - dry-run lists stale files without deleting
  - real delete removes stale files
  - TTL is respected per zone
  - operator-created files (in .dadaia/states/root_exceptions.txt) are never deleted
  - never deletes files outside .dadaia/
  - zones: .dadaia/tmp/, .dadaia/reports/, .dadaia/dev-report/
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from dadaia_workspace.features.workspace_clean.service import (
    CleanCandidate,
    CleanResult,
    WorkspaceCleanService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(tmp_path: Path) -> Path:
    """Scaffold a minimal .dadaia/ layout."""
    dadaia = tmp_path / ".dadaia"
    (dadaia / "states").mkdir(parents=True)
    (dadaia / "states" / "spec_contexts.json").write_text('{"schema_version":"2","contexts":[]}')
    for zone in ("tmp", "reports", "dev-report"):
        (dadaia / zone).mkdir(parents=True)
    return tmp_path


def _write_file(path: Path, *, mtime_offset: dt.timedelta) -> Path:
    """Write an empty file with a synthetic mtime = now - mtime_offset."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("content")
    target_mtime = (dt.datetime.now(tz=dt.UTC) - mtime_offset).timestamp()
    import os

    os.utime(path, (target_mtime, target_mtime))
    return path


# ---------------------------------------------------------------------------
# T-016-Z03: dry-run lists stale files
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_returns_candidates_without_deleting(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        stale = _write_file(
            ws / ".dadaia" / "tmp" / "agent1" / "20260101" / "old.txt",
            mtime_offset=dt.timedelta(days=3),
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=True)

        assert result.dry_run is True
        assert any(stale == c.path for c in result.candidates)
        assert stale.exists(), "dry-run must NOT delete files"

    def test_dry_run_is_default(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        _write_file(
            ws / ".dadaia" / "tmp" / "agent1" / "20260101" / "old.txt",
            mtime_offset=dt.timedelta(days=3),
        )
        svc = WorkspaceCleanService(ws)

        # Call clean() without any args — must be dry_run=True by default
        result = svc.clean()

        assert result.dry_run is True

    def test_dry_run_shows_no_candidates_for_fresh_files(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        _write_file(
            ws / ".dadaia" / "tmp" / "agent1" / "20260101" / "fresh.txt",
            mtime_offset=dt.timedelta(minutes=5),
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=True)

        # Fresh file should NOT be a candidate
        fresh_files = [c.path.name for c in result.candidates if c.path.name == "fresh.txt"]
        assert fresh_files == []


# ---------------------------------------------------------------------------
# T-016-Z03: real delete removes stale files
# ---------------------------------------------------------------------------


class TestRealDelete:
    def test_real_delete_removes_stale_tmp_file(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        stale = _write_file(
            ws / ".dadaia" / "tmp" / "agent1" / "20260101" / "old.json",
            mtime_offset=dt.timedelta(days=3),
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=False)

        assert result.dry_run is False
        assert not stale.exists(), "stale file should have been deleted"
        assert stale in result.deleted

    def test_real_delete_removes_stale_reports_file(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        stale = _write_file(
            ws / ".dadaia" / "reports" / "ctx" / "agent" / "old.html",
            mtime_offset=dt.timedelta(days=10),
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=False)

        assert not stale.exists()
        assert stale in result.deleted

    def test_real_delete_removes_stale_dev_report_file(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        stale = _write_file(
            ws / ".dadaia" / "dev-report" / "2026-01-01T000000Z-test.html",
            mtime_offset=dt.timedelta(days=5),
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=False)

        assert not stale.exists()
        assert stale in result.deleted

    def test_logs_every_reclaim(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        stale = _write_file(
            ws / ".dadaia" / "tmp" / "agent1" / "20260101" / "todelete.txt",
            mtime_offset=dt.timedelta(days=3),
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=False)

        # Every deleted path must appear in result.deleted
        assert stale in result.deleted


# ---------------------------------------------------------------------------
# T-016-Z03: per-zone TTL is respected
# ---------------------------------------------------------------------------


class TestTTL:
    def test_tmp_zone_ttl_default_2_days(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        old = _write_file(
            ws / ".dadaia" / "tmp" / "ag" / "20260101" / "old.txt",
            mtime_offset=dt.timedelta(days=3),  # older than default 2d TTL
        )
        fresh = _write_file(
            ws / ".dadaia" / "tmp" / "ag" / "20260101" / "fresh.txt",
            mtime_offset=dt.timedelta(hours=1),  # within TTL
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=True)

        candidate_paths = {c.path for c in result.candidates}
        assert old in candidate_paths
        assert fresh not in candidate_paths

    def test_reports_zone_ttl_default_7_days(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        old = _write_file(
            ws / ".dadaia" / "reports" / "ctx" / "ag" / "old.html",
            mtime_offset=dt.timedelta(days=10),  # older than default 7d TTL
        )
        recent = _write_file(
            ws / ".dadaia" / "reports" / "ctx" / "ag" / "recent.html",
            mtime_offset=dt.timedelta(days=3),  # within 7d TTL
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=True)

        candidate_paths = {c.path for c in result.candidates}
        assert old in candidate_paths
        assert recent not in candidate_paths

    def test_dev_report_zone_ttl_default_3_days(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        old = _write_file(
            ws / ".dadaia" / "dev-report" / "2026-01-01T000000Z-old.html",
            mtime_offset=dt.timedelta(days=5),  # older than default 3d TTL
        )
        fresh = _write_file(
            ws / ".dadaia" / "dev-report" / "2026-06-07T000000Z-fresh.html",
            mtime_offset=dt.timedelta(hours=12),  # within TTL
        )
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=True)

        candidate_paths = {c.path for c in result.candidates}
        assert old in candidate_paths
        assert fresh not in candidate_paths


# ---------------------------------------------------------------------------
# T-016-Z03: operator files (root_exceptions.txt) are NEVER deleted
# ---------------------------------------------------------------------------


class TestOperatorFiles:
    def test_operator_file_in_exception_list_not_deleted(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        # Operator-created file in a clean zone, listed in root_exceptions.txt
        protected = _write_file(
            ws / ".dadaia" / "tmp" / "operator-notes.txt",
            mtime_offset=dt.timedelta(days=10),
        )
        exc_file = ws / ".dadaia" / "states" / "root_exceptions.txt"
        exc_file.write_text("operator-notes.txt\n")

        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=False)

        assert protected.exists(), "operator-protected file must never be deleted"
        assert protected not in result.deleted

    def test_operator_file_via_glob_not_deleted(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        protected = _write_file(
            ws / ".dadaia" / "tmp" / "operator-screenshot.png",
            mtime_offset=dt.timedelta(days=10),
        )
        exc_file = ws / ".dadaia" / "states" / "root_exceptions.txt"
        exc_file.write_text("*.png\n")

        svc = WorkspaceCleanService(ws)
        result = svc.clean(dry_run=False)

        assert protected.exists()
        assert protected not in result.deleted


# ---------------------------------------------------------------------------
# T-016-Z03: never deletes files outside .dadaia/
# ---------------------------------------------------------------------------


class TestBoundary:
    def test_never_deletes_outside_dadaia(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        outside = _write_file(
            ws / "repos" / "myrepo" / "important.py",
            mtime_offset=dt.timedelta(days=100),
        )
        (ws / "repos").mkdir(parents=True, exist_ok=True)

        svc = WorkspaceCleanService(ws)
        result = svc.clean(dry_run=False)

        assert outside.exists()
        assert outside not in result.deleted

    def test_candidate_zone_must_be_under_dadaia(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        svc = WorkspaceCleanService(ws)

        result = svc.clean(dry_run=True)

        # All candidates must be under .dadaia/
        dadaia_dir = ws / ".dadaia"
        for c in result.candidates:
            assert dadaia_dir in c.path.parents or c.path.parent == dadaia_dir, (
                f"candidate path {c.path} is outside .dadaia/"
            )


# ---------------------------------------------------------------------------
# T-016-Z03: CleanCandidate and CleanResult data classes
# ---------------------------------------------------------------------------


class TestDataClasses:
    def test_clean_result_has_expected_fields(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        svc = WorkspaceCleanService(ws)
        result = svc.clean(dry_run=True)

        assert isinstance(result, CleanResult)
        assert isinstance(result.dry_run, bool)
        assert isinstance(result.candidates, list)
        assert isinstance(result.deleted, list)

    def test_clean_candidate_has_expected_fields(self, tmp_path: Path) -> None:
        ws = _make_workspace(tmp_path)
        _write_file(
            ws / ".dadaia" / "tmp" / "ag" / "20260101" / "file.txt",
            mtime_offset=dt.timedelta(days=5),
        )
        svc = WorkspaceCleanService(ws)
        result = svc.clean(dry_run=True)

        assert result.candidates
        c = result.candidates[0]
        assert isinstance(c, CleanCandidate)
        assert isinstance(c.path, Path)
        assert isinstance(c.zone, str)
        assert isinstance(c.reason, str)
