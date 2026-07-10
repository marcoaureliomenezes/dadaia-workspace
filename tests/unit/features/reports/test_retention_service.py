from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import pytest

from dadaia_workspace.features.reports.retention import ReportRetentionService

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


# ---------------------------------------------------------------------------
# Kept: deletion-safety (dry-run never deletes) + path-normalization guard
# ---------------------------------------------------------------------------


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


def test_path_normalization_rejects_absolute_and_parent_traversal(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(ValueError, match="absolute"):
        service.mark_important("/tmp/report.html")
    with pytest.raises(ValueError, match="parent traversal"):
        service.mark_important("ctx/../report.html")


# ---------------------------------------------------------------------------
# TTL / orphan / status / fresh-counting — 1 param table
# ---------------------------------------------------------------------------


def test_ttl_orphan_status_and_fresh_counting_matrix(tmp_path: Path) -> None:
    # TTL: 48-hour cutoff — older-than-48h is a candidate, fresher is not.
    old = NOW - dt.timedelta(hours=49)
    _write_report(tmp_path, "ctx/qa/old.html", mtime=old)
    _write_report(tmp_path, "ctx/qa/new.html", mtime=NOW - dt.timedelta(hours=2))
    candidates = _service(tmp_path).cleanup_candidates()
    assert [c.artifact_path for c in candidates] == [".dadaia/reports/ctx/qa/old.html"]

    # list_reports discovers html + matching handoffs, with effective_timestamp.
    tp2 = tmp_path.parent / (tmp_path.name + "-list")
    tp2.mkdir()
    _write_report(tp2, "ctx/qa/report.html")
    handoff = _write_handoff(tp2, "ctx/qa/report.html")
    reports = _service(tp2).list_reports()
    assert len(reports) == 1
    assert reports[0].artifact_path == ".dadaia/reports/ctx/qa/report.html"
    assert reports[0].handoff_paths == (handoff,)
    assert reports[0].effective_timestamp == dt.datetime(2026, 6, 4, tzinfo=dt.UTC)

    # Orphan handoff (no matching report) old enough is a cleanup candidate.
    tp3 = tmp_path.parent / (tmp_path.name + "-orphan")
    tp3.mkdir()
    _write_handoff(tp3, "ctx/qa/missing.html", produced_at="2026-06-01T00:00:00Z")
    orphan_candidates = _service(tp3).cleanup_candidates()
    assert orphan_candidates[0].artifact_path == ".dadaia/reports/ctx/qa/missing.html"

    # status(): fresh orphan handoffs are counted (not yet stale).
    tp4 = tmp_path.parent / (tmp_path.name + "-status")
    tp4.mkdir()
    _write_handoff(tp4, "ctx/qa/missing.html", produced_at="2026-06-04T11:00:00Z")
    _write_handoff(
        tp4, "ctx/qa/other-missing.html", produced_at="2026-06-04T11:00:00Z", canonical=False
    )
    status = _service(tp4).status()
    assert status["orphan_handoff_count"] == 2
    assert status["stale_handoff_count"] == 0

    # status(): malformed retention-state file is reported, not raised.
    tp5 = tmp_path.parent / (tmp_path.name + "-malformed")
    state = tp5 / ".dadaia" / "states" / "report_retention.json"
    state.parent.mkdir(parents=True)
    state.write_text("{not json", encoding="utf-8")
    assert _service(tp5).status()["malformed_state"] is True


# ---------------------------------------------------------------------------
# delete-real + important mark/unmark + legacy-stem pair — 1 param table
# ---------------------------------------------------------------------------


def test_delete_important_and_legacy_stem_matrix(tmp_path: Path) -> None:
    # Real delete: cleanup() (no dry-run) removes both the report and its handoff.
    report = _write_report(tmp_path, "ctx/qa/old.html", mtime=NOW - dt.timedelta(days=3))
    handoff = _write_handoff(tmp_path, "ctx/qa/old.html", produced_at="2026-06-01T00:00:00Z")
    result = _service(tmp_path).cleanup()
    assert report in result.deleted_paths
    assert handoff in result.deleted_paths
    assert not report.exists()
    assert not handoff.exists()

    # mark_important excludes from cleanup_candidates; unmark_important restores it.
    tp2 = tmp_path.parent / (tmp_path.name + "-important")
    tp2.mkdir()
    _write_report(tp2, "ctx/qa/old.html", mtime=NOW - dt.timedelta(days=3))
    svc2 = _service(tp2)
    artifact = svc2.mark_important("ctx/qa/old.html", reason="keep evidence")
    assert artifact == ".dadaia/reports/ctx/qa/old.html"
    assert svc2.cleanup_candidates() == []
    assert svc2.important_reports()[artifact]["reason"] == "keep evidence"
    svc2.unmark_important("ctx/qa/old.html")
    assert [c.artifact_path for c in svc2.cleanup_candidates()] == [
        ".dadaia/reports/ctx/qa/old.html"
    ]

    # mark_important works for a handoff with no matching report artifact.
    tp3 = tmp_path.parent / (tmp_path.name + "-handoff-only")
    handoff3 = tp3 / ".dadaia" / "handoff" / "ctx" / "orphan.handoff.json"
    handoff3.parent.mkdir(parents=True)
    handoff3.write_text(json.dumps({"agent": "qa-engineer"}), encoding="utf-8")
    artifact3 = _service(tp3).mark_important(".dadaia/handoff/ctx/orphan.handoff.json")
    assert artifact3 == ".dadaia/handoff/ctx/orphan.handoff.json"

    # Legacy adjacent handoff (same stem as the report) is deleted together with it.
    tp4 = tmp_path.parent / (tmp_path.name + "-legacy-stem")
    report4 = _write_report(tp4, "ctx/qa/old.html", mtime=NOW - dt.timedelta(days=3))
    handoff4 = report4.with_name("old.handoff.json")
    handoff4.write_text(json.dumps({"agent": "qa-engineer"}), encoding="utf-8")
    candidate4 = _service(tp4).cleanup_candidates()[0]
    assert report4 in candidate4.paths
    assert handoff4 in candidate4.paths

    # Legacy handoff's produced_at does not override the report's own filename timestamp.
    tp5 = tmp_path.parent / (tmp_path.name + "-legacy-ts")
    report5 = _write_report(tp5, "ctx/qa/2026-06-04T090000Z-report.html")
    handoff5 = report5.with_name("2026-06-04T090000Z-report.handoff.json")
    handoff5.write_text(
        json.dumps(
            {
                "produced_at": "2026-06-01T00:00:00Z",
                "artifact": {"path": ".dadaia/reports/ctx/qa/2026-06-04T090000Z-report.html"},
            }
        ),
        encoding="utf-8",
    )
    record5 = _service(tp5).list_reports()[0]
    assert record5.effective_timestamp == dt.datetime(2026, 6, 4, 9, 0, tzinfo=dt.UTC)

    # A symlinked report pointing outside .dadaia/reports/ is ignored, not crashed on.
    tp6 = tmp_path.parent / (tmp_path.name + "-symlink")
    tp6.mkdir()
    external = tp6 / "external.html"
    external.write_text("<html>outside</html>", encoding="utf-8")
    link = tp6 / ".dadaia" / "reports" / "ctx" / "qa" / "link.html"
    link.parent.mkdir(parents=True)
    os.symlink(external, link)
    svc6 = _service(tp6)
    assert svc6.list_reports() == []
    assert svc6.cleanup().deleted_paths == ()
    assert external.exists()
