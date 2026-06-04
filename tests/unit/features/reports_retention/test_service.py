from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pytest

from dadaia_workspace.features.reports_retention import ReportRetentionService


NOW = dt.datetime(2026, 6, 4, 12, 0, tzinfo=dt.UTC)


def _service(tmp_path: Path) -> ReportRetentionService:
    return ReportRetentionService(tmp_path, now=NOW)


def _write_report(tmp_path: Path, rel: str, *, mtime: dt.datetime | None = None) -> Path:
    path = tmp_path / ".dadaia" / "reports" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("<html>report</html>", encoding="utf-8")
    if mtime is not None:
        ts = mtime.timestamp()
        os.utime(path, (ts, ts))
    return path


def _write_handoff(
    tmp_path: Path,
    rel: str,
    *,
    produced_at: str = "2026-06-04T00:00:00Z",
    canonical: bool = True,
) -> Path:
    root = tmp_path / ".dadaia" / ("handoff" if canonical else "reports") / "ctx"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "2026-06-04T000000Z-qa-report.handoff.json"
    path.write_text(
        json.dumps(
            {
                "agent": "qa-engineer",
                "context": "ctx",
                "produced_at": produced_at,
                "artifact": {"path": f".dadaia/reports/{rel}"},
                "findings": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_list_reports_discovers_html_and_matching_handoffs(tmp_path: Path) -> None:
    _write_report(tmp_path, "ctx/qa/report.html")
    handoff = _write_handoff(tmp_path, "ctx/qa/report.html")

    reports = _service(tmp_path).list_reports()

    assert len(reports) == 1
    assert reports[0].artifact_path == ".dadaia/reports/ctx/qa/report.html"
    assert reports[0].handoff_paths == (handoff,)
    assert reports[0].effective_timestamp == dt.datetime(2026, 6, 4, tzinfo=dt.UTC)


def test_cleanup_candidates_use_48_hour_ttl(tmp_path: Path) -> None:
    old = NOW - dt.timedelta(hours=49)
    _write_report(tmp_path, "ctx/qa/old.html", mtime=old)
    _write_report(tmp_path, "ctx/qa/new.html", mtime=NOW - dt.timedelta(hours=2))

    candidates = _service(tmp_path).cleanup_candidates()

    assert [c.artifact_path for c in candidates] == [".dadaia/reports/ctx/qa/old.html"]


def test_important_report_is_not_cleanup_candidate(tmp_path: Path) -> None:
    _write_report(tmp_path, "ctx/qa/old.html", mtime=NOW - dt.timedelta(days=3))
    service = _service(tmp_path)
    artifact = service.mark_important("ctx/qa/old.html", reason="keep evidence")

    assert artifact == ".dadaia/reports/ctx/qa/old.html"
    assert service.cleanup_candidates() == []
    assert service.important_reports()[artifact]["reason"] == "keep evidence"


def test_unmark_important_restores_cleanup_candidate(tmp_path: Path) -> None:
    _write_report(tmp_path, "ctx/qa/old.html", mtime=NOW - dt.timedelta(days=3))
    service = _service(tmp_path)
    service.mark_important("ctx/qa/old.html")
    service.unmark_important("ctx/qa/old.html")

    assert [c.artifact_path for c in service.cleanup_candidates()] == [
        ".dadaia/reports/ctx/qa/old.html"
    ]


def test_path_normalization_rejects_absolute_and_parent_traversal(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="absolute"):
        service.mark_important("/tmp/report.html")
    with pytest.raises(ValueError, match="parent traversal"):
        service.mark_important("ctx/../report.html")


def test_cleanup_dry_run_does_not_delete(tmp_path: Path) -> None:
    report = _write_report(tmp_path, "ctx/qa/old.html", mtime=NOW - dt.timedelta(days=3))
    handoff = _write_handoff(
        tmp_path,
        "ctx/qa/old.html",
        produced_at="2026-06-01T00:00:00Z",
        canonical=False,
    )

    result = _service(tmp_path).cleanup(dry_run=True)

    assert len(result.candidates) == 1
    assert report.exists()
    assert handoff.exists()


def test_cleanup_deletes_report_and_handoffs(tmp_path: Path) -> None:
    report = _write_report(tmp_path, "ctx/qa/old.html", mtime=NOW - dt.timedelta(days=3))
    handoff = _write_handoff(tmp_path, "ctx/qa/old.html", produced_at="2026-06-01T00:00:00Z")

    result = _service(tmp_path).cleanup()

    assert report in result.deleted_paths
    assert handoff in result.deleted_paths
    assert not report.exists()
    assert not handoff.exists()


def test_old_orphan_handoff_is_cleanup_candidate(tmp_path: Path) -> None:
    handoff = _write_handoff(
        tmp_path,
        "ctx/qa/missing.html",
        produced_at="2026-06-01T00:00:00Z",
    )

    candidates = _service(tmp_path).cleanup_candidates()

    assert candidates[0].artifact_path == ".dadaia/reports/ctx/qa/missing.html"
    assert candidates[0].paths == (handoff,)


def test_malformed_state_is_reported(tmp_path: Path) -> None:
    state = tmp_path / ".dadaia" / "states" / "report_retention.json"
    state.parent.mkdir(parents=True)
    state.write_text("{not json", encoding="utf-8")

    assert _service(tmp_path).status()["malformed_state"] is True
