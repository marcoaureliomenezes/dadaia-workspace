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


def test_cleanup_contract_symlink_safety_and_malformed_sidecar_deletion(
    tmp_path: Path,
) -> None:
    external = tmp_path / "external.html"
    external.write_text("<html>external</html>", encoding="utf-8")
    link = tmp_path / ".dadaia" / "reports" / "ctx" / "qa" / "old.html"
    link.parent.mkdir(parents=True)
    os.symlink(external, link)

    symlink_result = _service(tmp_path).cleanup()

    assert symlink_result.candidates == ()
    assert symlink_result.deleted_paths == ()
    assert external.exists()

    sidecar_ws = tmp_path.parent / (tmp_path.name + "-sidecar")
    report = _old_report(sidecar_ws)
    sidecar = report.with_name("old.handoff.json")
    sidecar.write_text("{not json", encoding="utf-8")

    result = _service(sidecar_ws).cleanup()

    assert report in result.deleted_paths
    assert sidecar in result.deleted_paths
    assert not report.exists()
    assert not sidecar.exists()


def test_cleanup_contract_preserves_important_orphan_and_malformed_handoffs(
    tmp_path: Path,
) -> None:
    orphan = tmp_path / ".dadaia" / "handoff" / "ctx" / "orphan.handoff.json"
    orphan.parent.mkdir(parents=True)
    orphan.write_text(
        json.dumps(
            {
                "produced_at": "2026-06-01T00:00:00Z",
                "artifact": {"path": ".dadaia/reports/ctx/qa/missing.html"},
            }
        ),
        encoding="utf-8",
    )
    malformed = tmp_path / ".dadaia" / "handoff" / "ctx" / "2026-06-01T000000Z-bad.handoff.json"
    malformed.write_text("{not json", encoding="utf-8")

    service = _service(tmp_path)
    service.mark_important(".dadaia/handoff/ctx/orphan.handoff.json")
    service.mark_important(".dadaia/handoff/ctx/2026-06-01T000000Z-bad.handoff.json")

    result = service.cleanup()

    assert result.candidates == ()
    assert result.deleted_paths == ()
    assert orphan.exists()
    assert malformed.exists()
