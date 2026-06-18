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


def test_cleanup_defaults_to_dry_run_and_does_not_delete(tmp_path: Path) -> None:
    stale = _old(tmp_path / ".dadaia" / "tmp" / "agent" / "old.txt")

    result = LifecycleHygieneService(tmp_path, now=NOW).cleanup()

    assert result.dry_run is True
    assert result.deleted_paths == ()
    assert stale.exists()
    assert {candidate.path for candidate in result.candidates} == {".dadaia/tmp/agent/old.txt"}


def test_cleanup_apply_deletes_only_expired_files_under_safe_zones(tmp_path: Path) -> None:
    stale_report = _old(tmp_path / ".dadaia" / "reports" / "ctx" / "agent" / "old.html")
    stale_handoff = _old(tmp_path / ".dadaia" / "handoff" / "ctx" / "old.handoff.json")
    stale_tmp = _old(tmp_path / ".dadaia" / "tmp" / "agent" / "old.txt")
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
    assert not stale_tmp.exists()
    assert fresh_tmp.exists()
    assert state_file.exists()
    assert lock_file.exists()
    assert repo_file.exists()
    assert run_file.exists()


def test_cleanup_preserves_important_records_and_operator_protected_paths(
    tmp_path: Path,
) -> None:
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

    result = LifecycleHygieneService(tmp_path, now=NOW).cleanup(dry_run=False)

    assert important.exists()
    assert screenshot.exists()
    assert result.deleted_paths == ()
    protected = {candidate.path: candidate.protection_kind for candidate in result.candidates}
    assert protected[".dadaia/reports/ctx/agent/keep.html"] is (
        HygieneProtectionKind.IMPORTANT_REPORT
    )
    assert protected[".dadaia/tmp/agent/operator.png"] is (HygieneProtectionKind.OPERATOR_PROTECTED)


def test_cleanup_preserves_valid_referenced_artifacts_and_review_evidence(
    tmp_path: Path,
) -> None:
    report = _old(tmp_path / ".dadaia" / "reports" / "ctx" / "review" / "old.html")
    referenced_report = ".dadaia/reports/ctx/review/old.html"
    handoff = _old(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "review.handoff.json",
        content=json.dumps(
            {
                "release_id": "v0.1.15",
                "agent": "qa-engineer",
                "verdict": "APPROVED",
                "artifact": {"path": referenced_report},
            }
        ),
    )

    result = LifecycleHygieneService(
        tmp_path,
        now=NOW,
        active_release_id="v0.1.15",
    ).cleanup(dry_run=False)

    assert report.exists()
    assert handoff.exists()
    assert result.deleted_paths == ()
    protected = {candidate.path for candidate in result.candidates if candidate.protected}
    assert protected == {
        ".dadaia/reports/ctx/review/old.html",
        ".dadaia/handoff/ctx/review.handoff.json",
    }


def test_cleanup_preserves_malformed_review_and_audit_handoffs(tmp_path: Path) -> None:
    review = _old(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "2026-06-01T000000Z-qa-review.handoff.json",
        content="{not json",
    )
    audit = _old(
        tmp_path / ".dadaia" / "handoff" / "ctx" / "2026-06-01T000000Z-security-audit.handoff.json",
        content="{not json",
    )

    result = LifecycleHygieneService(tmp_path, now=NOW).cleanup(dry_run=False)

    assert review.exists()
    assert audit.exists()
    assert result.deleted_paths == ()
    protected = {candidate.path for candidate in result.candidates if candidate.protected}
    assert protected == {
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
