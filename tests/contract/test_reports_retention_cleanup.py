from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

from dadaia_workspace.features.reports.retention import ReportRetentionService

NOW = dt.datetime(2026, 6, 4, 12, 0, tzinfo=dt.UTC)


def _service(tmp_path: Path) -> ReportRetentionService:
    return ReportRetentionService(tmp_path, now=NOW)


def _old_report(tmp_path: Path, rel: str = "ctx/qa/old.html") -> Path:
    report = tmp_path / ".dadaia" / "reports" / rel
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("<html>old</html>", encoding="utf-8")
    ts = (NOW - dt.timedelta(days=3)).timestamp()
    os.utime(report, (ts, ts))
    return report


def test_cleanup_dry_run_contract_is_non_mutating(tmp_path: Path) -> None:
    report = _old_report(tmp_path)
    handoff = tmp_path / ".dadaia" / "handoff" / "ctx" / "old.handoff.json"
    handoff.parent.mkdir(parents=True)
    handoff.write_text(
        json.dumps(
            {
                "produced_at": "2026-06-01T00:00:00Z",
                "artifact": {"path": ".dadaia/reports/ctx/qa/old.html"},
            }
        ),
        encoding="utf-8",
    )

    result = _service(tmp_path).cleanup(dry_run=True)

    assert len(result.candidates) == 1
    assert result.deleted_paths == ()
    assert report.exists()
    assert handoff.exists()


def test_cleanup_contract_does_not_delete_external_symlink_target(tmp_path: Path) -> None:
    external = tmp_path / "external.html"
    external.write_text("<html>external</html>", encoding="utf-8")
    link = tmp_path / ".dadaia" / "reports" / "ctx" / "qa" / "old.html"
    link.parent.mkdir(parents=True)
    os.symlink(external, link)

    result = _service(tmp_path).cleanup()

    assert result.candidates == ()
    assert result.deleted_paths == ()
    assert external.exists()


def test_cleanup_contract_preserves_important_orphan_handoff(tmp_path: Path) -> None:
    handoff = tmp_path / ".dadaia" / "handoff" / "ctx" / "orphan.handoff.json"
    handoff.parent.mkdir(parents=True)
    handoff.write_text(
        json.dumps(
            {
                "produced_at": "2026-06-01T00:00:00Z",
                "artifact": {"path": ".dadaia/reports/ctx/qa/missing.html"},
            }
        ),
        encoding="utf-8",
    )
    service = _service(tmp_path)
    service.mark_important(".dadaia/handoff/ctx/orphan.handoff.json")

    result = service.cleanup()

    assert result.candidates == ()
    assert result.deleted_paths == ()
    assert handoff.exists()


def test_cleanup_contract_deletes_malformed_adjacent_sidecar_with_report(
    tmp_path: Path,
) -> None:
    report = _old_report(tmp_path)
    sidecar = report.with_name("old.handoff.json")
    sidecar.write_text("{not json", encoding="utf-8")

    result = _service(tmp_path).cleanup()

    assert report in result.deleted_paths
    assert sidecar in result.deleted_paths
    assert not report.exists()
    assert not sidecar.exists()


def test_cleanup_contract_preserves_important_malformed_handoff(tmp_path: Path) -> None:
    handoff = tmp_path / ".dadaia" / "handoff" / "ctx" / "2026-06-01T000000Z-bad.handoff.json"
    handoff.parent.mkdir(parents=True)
    handoff.write_text("{not json", encoding="utf-8")
    service = _service(tmp_path)
    service.mark_important(".dadaia/handoff/ctx/2026-06-01T000000Z-bad.handoff.json")

    result = service.cleanup()

    assert result.candidates == ()
    assert result.deleted_paths == ()
    assert handoff.exists()
