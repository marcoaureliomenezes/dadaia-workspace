"""Contract tests for the panel reports domain — real decisions only.

/api/panel-status and /api/contexts response shapes are pinned byte-identical
by ``test_api_golden.py``; the per-key shape/content-type facets that used to
live here are DELETED in its favor. This file keeps only the reports-domain
behavior that flips a real decision:

1. Handoff enrichment: canonical-root + legacy-adjacent + dedup when both exist.
2. Discovery skips self-referential/source-file handoffs; sidecar-less HTML lists.
3. Mark/unmark important + the derived retention state.
4. Delete removes the report AND its handoff, from canonical root or legacy-adjacent.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from dadaia_workspace.core.models.spec_context import SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_reports import (
    delete_report_file,
    mark_report_important,
    render_api_reports,
    unmark_report_important,
)
from dadaia_workspace.features.reports.retention import ReportRetentionService

pytestmark = pytest.mark.unit


class FakeServerRegistryService:
    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[object, object]]:
        return []


class FakeSpecContextService:
    def __init__(self, contexts: list[SpecContextProject] | None = None) -> None:
        self._contexts = contexts or []

    def list_all(self) -> list[SpecContextProject]:
        return list(self._contexts)


def _build_service(workspace_root: Path) -> PanelService:
    return PanelService(
        registry=FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=workspace_root,
        report_retention=ReportRetentionService(workspace_root),
    )


def _now_iso() -> str:
    return (
        datetime.datetime.now(tz=datetime.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _write_report(tmp_path: Path, rel: str = "ctx/qa-engineer/qa.html") -> Path:
    report_path = tmp_path / ".dadaia" / "reports" / rel
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# 1. Handoff enrichment: canonical-root + legacy-adjacent + dedup
# ---------------------------------------------------------------------------


def test_reports_enrichment_canonical_legacy_and_dedup(tmp_path: Path) -> None:
    # (a) canonical-root handoff enriches the report.
    report_path = _write_report(tmp_path)
    now_iso = _now_iso()
    handoff_path = (
        tmp_path / ".dadaia" / "handoff" / "ctx" / "2026-06-04T000000Z-qa-engineer-qa.handoff.json"
    )
    handoff_path.parent.mkdir(parents=True)
    handoff_path.write_text(
        json.dumps(
            {
                "schema_version": "handoff-v1.1",
                "agent": "qa-engineer",
                "context": "ctx",
                "produced_at": now_iso,
                "artifact": {
                    "type": "report",
                    "path": ".dadaia/reports/ctx/qa-engineer/qa.html",
                    "content_hash": "a" * 64,
                },
                "findings": [{"severity": "HIGH", "message": "issue"}],
            }
        ),
        encoding="utf-8",
    )
    service = _build_service(tmp_path)
    status, content_type, body = render_api_reports(service)()
    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert data["reports"][0]["agent"] == "qa-engineer"
    assert data["reports"][0]["path"] == "ctx/qa-engineer/qa.html"
    assert data["reports"][0]["findings_summary"]["HIGH"] == 1
    report_path.unlink()
    handoff_path.unlink()

    # (b) legacy-adjacent handoff (report.with_suffix('.handoff.json')) also enriches.
    report_path = _write_report(tmp_path)
    legacy_handoff = report_path.with_suffix(".handoff.json")
    legacy_handoff.write_text(
        json.dumps(
            {
                "schema_version": "handoff-v1.1",
                "agent": "qa-engineer",
                "context": "ctx",
                "produced_at": "2026-06-04T02:00:00Z",
                "artifact": {"type": "report", "path": ".dadaia/reports/ctx/qa-engineer/qa.html"},
                "findings": [
                    {"severity": "CRITICAL", "message": "critical issue"},
                    {"severity": "LOW", "message": "minor issue"},
                ],
            }
        ),
        encoding="utf-8",
    )
    _, _, body_legacy = render_api_reports(service)()
    data_legacy = json.loads(body_legacy)
    assert len(data_legacy["reports"]) == 1
    assert data_legacy["reports"][0]["created_at"] == "2026-06-04T02:00:00Z"
    assert data_legacy["reports"][0]["findings_summary"]["CRITICAL"] == 1
    assert data_legacy["reports"][0]["findings_summary"]["LOW"] == 1

    # (c) same report with BOTH a legacy-adjacent AND a canonical-root handoff dedups to 1.
    now_iso2 = _now_iso()
    handoff_payload = {
        "agent": "qa-engineer",
        "context": "ctx",
        "produced_at": now_iso2,
        "artifact": {"path": ".dadaia/reports/ctx/qa-engineer/qa.html"},
        "findings": [{"severity": "HIGH", "message": "issue"}],
    }
    legacy_handoff.write_text(json.dumps(handoff_payload), encoding="utf-8")
    canonical_handoff = tmp_path / ".dadaia" / "handoff" / "ctx" / "qa.handoff.json"
    canonical_handoff.parent.mkdir(parents=True, exist_ok=True)
    canonical_handoff.write_text(json.dumps(handoff_payload), encoding="utf-8")
    _, _, body_dedup = render_api_reports(service)()
    data_dedup = json.loads(body_dedup)
    assert len(data_dedup["reports"]) == 1
    assert data_dedup["reports"][0]["title"] == "qa"
    assert data_dedup["reports"][0]["findings_summary"]["HIGH"] == 1


# ---------------------------------------------------------------------------
# 2. Discovery skips self-referential/source-file handoffs; sidecar-less listing
# ---------------------------------------------------------------------------


def test_discovery_skips_bogus_handoffs_and_lists_sidecar_less_reports(tmp_path: Path) -> None:
    # Self-referential and source-file handoffs never fabricate a report entry.
    handoff_root = tmp_path / ".dadaia" / "handoff" / "ctx"
    handoff_root.mkdir(parents=True)
    (handoff_root / "self.handoff.json").write_text(
        json.dumps(
            {
                "agent": "qa-engineer",
                "context": "ctx",
                "artifact": {"path": ".dadaia/reports/ctx/qa-engineer/self.handoff.json"},
            }
        ),
        encoding="utf-8",
    )
    (handoff_root / "source.handoff.json").write_text(
        json.dumps(
            {
                "agent": "security-reviewer",
                "context": "ctx",
                "artifact": {"path": "dadaia_workspace/public/scripts/sdd-spec-gate.sh"},
            }
        ),
        encoding="utf-8",
    )
    service = _build_service(tmp_path)
    _, _, body = render_api_reports(service)()
    assert json.loads(body)["reports"] == []

    # HTML-first indexing: a report with NO handoff sidecar is still listed (rglob discovery).
    created = datetime.datetime.now(tz=datetime.UTC).replace(microsecond=0) - datetime.timedelta(
        hours=1
    )
    expires = created + datetime.timedelta(hours=48)
    stamp = created.strftime("%Y-%m-%dT%H%M%SZ")
    title = f"{stamp}-workflow-audit"
    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "project-auditor" / f"{title}.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>audit</html>", encoding="utf-8")

    _, _, body2 = render_api_reports(service)()
    data2 = json.loads(body2)
    assert data2["reports"] == [
        {
            "title": title,
            "agent": "project-auditor",
            "context": "ctx",
            "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "path": f"ctx/project-auditor/{title}.html",
            "findings_summary": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "important": False,
            "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "is_expired": False,
            "retention_reason": "Expires after 48h",
            "retention_status": "expires",
        }
    ]


# ---------------------------------------------------------------------------
# 3. Mark/unmark important + derived retention state
# ---------------------------------------------------------------------------


def test_mark_unmark_important_and_retention_state(tmp_path: Path) -> None:
    _write_report(tmp_path)
    service = _build_service(tmp_path)

    mark_status, _, mark_body = mark_report_important(service)(path="ctx/qa-engineer/qa.html")
    assert mark_status == 200
    assert json.loads(mark_body)["important"] is True

    _, _, body = render_api_reports(service)()
    row = json.loads(body)["reports"][0]
    assert row["important"] is True
    assert row["is_expired"] is False
    assert row["retention_reason"] == "Marked important"
    assert row["retention_status"] == "important"

    unmark_status, _, unmark_body = unmark_report_important(service)(path="ctx/qa-engineer/qa.html")
    assert unmark_status == 200
    assert json.loads(unmark_body)["important"] is False


# ---------------------------------------------------------------------------
# 4. Delete removes report + handoff (canonical-root AND legacy-adjacent)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "handoff_kind",
    [
        pytest.param("canonical-root", id="delete-removes-canonical-root-handoff"),
        pytest.param("legacy-adjacent", id="delete-removes-legacy-adjacent-handoff"),
    ],
)
def test_delete_removes_report_and_handoff(tmp_path: Path, handoff_kind: str) -> None:
    report_path = _write_report(tmp_path)
    if handoff_kind == "canonical-root":
        handoff_path = (
            tmp_path
            / ".dadaia"
            / "handoff"
            / "ctx"
            / "2026-06-04T000000Z-qa-engineer-qa.handoff.json"
        )
        handoff_path.parent.mkdir(parents=True)
    else:
        handoff_path = report_path.with_suffix(".handoff.json")
    handoff_path.write_text(
        json.dumps({"artifact": {"path": ".dadaia/reports/ctx/qa-engineer/qa.html"}}),
        encoding="utf-8",
    )

    service = _build_service(tmp_path)
    status, _, _ = delete_report_file(service)(path="ctx/qa-engineer/qa.html")

    assert status == 200
    assert not report_path.exists()
    assert not handoff_path.exists()
