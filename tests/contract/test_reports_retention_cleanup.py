"""Intent: CONTRACT — features/reports/retention cleanup (symlink safety, malformed sidecar, important preservation); reports-cleanup-skips-handoffs-without-artifact-path"""

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


def _handoff(tmp_path: Path, slug: str, doc: dict[str, object]) -> Path:
    handoff = tmp_path / ".dadaia" / "handoff" / "ctx" / f"{slug}.handoff.json"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(json.dumps(doc), encoding="utf-8")
    return handoff


def test_cleanup_contract_every_handoff_is_a_retention_node_paired_or_not(
    tmp_path: Path,
) -> None:
    """Intent: CONTRACT — reports-cleanup-skips-handoffs-without-artifact-path.

    One index over every handoff: a handoff without ``artifact.path`` and a handoff whose
    artifact lives outside ``.dadaia/reports/`` age, count and expire exactly like an
    artifact-bearing one; ``mark_important`` on either keys the protection by the
    handoff's own ref; a younger handoff is counted and survives.
    """
    old = "2026-06-01T00:00:00Z"
    audit = {"path": "repos/ctx/specs/audits/20260601-x/AUDIT.md"}
    expired = _handoff(tmp_path, "expired", {"produced_at": old})
    audited = _handoff(tmp_path, "audited", {"produced_at": old, "artifact": audit})
    kept = _handoff(tmp_path, "kept", {"produced_at": old, "artifact": audit})
    fresh = _handoff(tmp_path, "fresh", {"produced_at": "2026-06-04T11:00:00Z"})
    service = _service(tmp_path)

    kept_ref = service.mark_important(".dadaia/handoff/ctx/kept.handoff.json")

    assert kept_ref == ".dadaia/handoff/ctx/kept.handoff.json"
    candidates = service.cleanup_candidates()
    assert sorted(p for c in candidates for p in c.paths) == sorted([expired, audited])
    status = service.status()
    assert status["report_count"] == 0
    assert status["stale_handoff_count"] == 2
    assert status["orphan_handoff_count"] == 4

    result = service.cleanup()

    assert sorted(result.deleted_paths) == sorted([expired, audited])
    assert kept.exists()
    assert fresh.exists()
