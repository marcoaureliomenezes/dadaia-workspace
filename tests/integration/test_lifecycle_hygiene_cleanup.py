"""Integration tests for lifecycle hygiene cleanup boundaries."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from dadaia_workspace.core.models.hygiene import HygieneProtectionKind
from dadaia_workspace.features.lifecycle.hygiene import LifecycleHygieneService

NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.UTC)


def _write(path: Path, *, age: dt.timedelta, content: str = "content") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    timestamp = (NOW - age).timestamp()
    os.utime(path, (timestamp, timestamp))
    return path


def _old(path: Path, content: str = "content") -> Path:
    return _write(path, age=dt.timedelta(hours=72), content=content)


def test_cleanup_dry_run_default_then_apply_deletes_only_safe_zone_expired_files(
    tmp_path: Path,
) -> None:
    """Default is dry-run (no deletion, candidates reported); --apply-equivalent
    (dry_run=False) deletes only expired files under the safe zones (reports/handoff/
    tmp) — states/locks/repos/runs are untouched even when stale, and a fresh tmp file
    survives."""
    stale = _old(tmp_path / ".dadaia" / "tmp" / "agent" / "old.txt")

    dry_result = LifecycleHygieneService(tmp_path, now=NOW).cleanup()

    assert dry_result.dry_run is True
    assert dry_result.deleted_paths == ()
    assert stale.exists()
    assert {c.path for c in dry_result.candidates} == {".dadaia/tmp/agent/old.txt"}

    stale_report = _old(tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "old.html")
    stale_handoff = _old(tmp_path / ".dadaia" / "handoff" / "ctx" / "old.handoff.json")
    fresh_tmp = _write(
        tmp_path / ".dadaia" / "tmp" / "agent" / "fresh.txt",
        age=dt.timedelta(minutes=5),
    )
    state_file = _old(tmp_path / ".dadaia" / "states" / "old-state.json")
    lock_file = _old(tmp_path / ".dadaia" / "locks" / "old.lock")
    repo_file = _old(tmp_path / "repos" / "dadaia-workspace" / "old.txt")
    run_file = _old(tmp_path / ".dadaia" / "runs" / "lifecycle" / "active.json")

    result = LifecycleHygieneService(tmp_path, now=NOW).cleanup(dry_run=False)

    assert result.dry_run is False
    assert {path.relative_to(tmp_path).as_posix() for path in result.deleted_paths} == {
        ".dadaia/reports/ctx/agent/old.html",
        ".dadaia/handoff/ctx/old.handoff.json",
        ".dadaia/tmp/agent/old.txt",
    }
    assert not stale_report.exists()
    assert not stale_handoff.exists()
    assert not stale.exists()
    assert fresh_tmp.exists()
    assert state_file.exists()
    assert lock_file.exists()
    assert repo_file.exists()
    assert run_file.exists()


def test_cleanup_protection_classes_important_operator_referenced_and_malformed(
    tmp_path: Path,
) -> None:
    """Every protection class survives cleanup: important-report (report_retention.json),
    operator root_exceptions (*.png), referenced review evidence (report path in an
    APPROVED handoff's artifact), and malformed review/audit handoffs (kept even
    unparseable — never silently deleted, always investigable)."""
    # Important-report + operator-protected.
    important = _old(tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "keep.html")
    screenshot = _old(tmp_path / ".dadaia" / "tmp" / "agent" / "operator.png")
    state_dir = tmp_path / ".dadaia" / "states"
    state_dir.mkdir(parents=True)
    (state_dir / "report_retention.json").write_text(
        json.dumps(
            {"important": {".dadaia/reports/ctx/agent/keep.html": {"reason": "manual evidence"}}}
        ),
        encoding="utf-8",
    )
    (state_dir / "root_exceptions.txt").write_text("*.png\n", encoding="utf-8")

    result1 = LifecycleHygieneService(tmp_path, now=NOW).cleanup(dry_run=False)

    assert important.exists()
    assert screenshot.exists()
    assert result1.deleted_paths == ()
    protected1 = {c.path: c.protection_kind for c in result1.candidates}
    assert protected1[".dadaia/reports/ctx/agent/keep.html"] is (
        HygieneProtectionKind.IMPORTANT_REPORT
    )
    assert protected1[".dadaia/tmp/agent/operator.png"] is (
        HygieneProtectionKind.OPERATOR_PROTECTED
    )

    # Valid referenced artifact + review evidence — own workspace to avoid state overlap.
    referenced_ws = tmp_path / "referenced-case"
    report = _old(referenced_ws / ".dadaia" / "reports" / "ctx" / "review" / "old.html")
    referenced_report = ".dadaia/reports/ctx/review/old.html"
    handoff = _old(
        referenced_ws / ".dadaia" / "handoff" / "ctx" / "review.handoff.json",
        content=json.dumps(
            {
                "release_id": "v0.1.15",
                "agent": "qa-engineer",
                "verdict": "APPROVED",
                "artifact": {"path": referenced_report},
            }
        ),
    )

    result2 = LifecycleHygieneService(
        referenced_ws,
        now=NOW,
        active_release_id="v0.1.15",
    ).cleanup(dry_run=False)

    assert report.exists()
    assert handoff.exists()
    assert result2.deleted_paths == ()
    protected2 = {c.path for c in result2.candidates if c.protected}
    assert protected2 == {
        ".dadaia/reports/ctx/review/old.html",
        ".dadaia/handoff/ctx/review.handoff.json",
    }

    # Malformed review/audit handoffs — own workspace.
    malformed_ws = tmp_path / "malformed-case"
    review = _old(
        malformed_ws / ".dadaia" / "handoff" / "ctx" / "2026-06-01T000000Z-qa-review.handoff.json",
        content="{not json",
    )
    audit = _old(
        malformed_ws
        / ".dadaia"
        / "handoff"
        / "ctx"
        / "2026-06-01T000000Z-security-audit.handoff.json",
        content="{not json",
    )

    result3 = LifecycleHygieneService(malformed_ws, now=NOW).cleanup(dry_run=False)

    assert review.exists()
    assert audit.exists()
    assert result3.deleted_paths == ()
    protected3 = {c.path for c in result3.candidates if c.protected}
    assert protected3 == {
        ".dadaia/handoff/ctx/2026-06-01T000000Z-qa-review.handoff.json",
        ".dadaia/handoff/ctx/2026-06-01T000000Z-security-audit.handoff.json",
    }


def test_cleanup_rejects_escaping_symlink_and_prunes_empty_safe_dirs(tmp_path: Path) -> None:
    external = _old(tmp_path / "external.html")
    link = tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "old.html"
    link.parent.mkdir(parents=True)
    os.symlink(external, link)
    stale = _old(tmp_path / ".dadaia" / "tmp" / "agent" / "day" / "old.txt")
    empty_dir = stale.parent

    result = LifecycleHygieneService(tmp_path, now=NOW).cleanup(dry_run=False)

    assert external.exists()
    assert link.exists()
    assert not stale.exists()
    assert not empty_dir.exists()
    assert link not in result.deleted_paths
    assert empty_dir in result.pruned_dirs
