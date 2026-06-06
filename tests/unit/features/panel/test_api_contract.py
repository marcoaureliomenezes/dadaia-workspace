"""Contract tests for /api/panel-status and /api/contexts — T-3.9 / T-3.9-bis.

If these tests fail, panel.js must be updated in lockstep because the JS reads
specific field names directly from the JSON response (data.groups, row.port,
row.status, etc.). mypy cannot catch JS breakage — this is the guard.

Contract shape (stable — do not rename fields without updating both this test
and PANEL_JS in _assets.py):

/api/panel-status:
  { "groups": [ { "group_label": str, "context_name": str|null,
                  "rows": [ { "port": int, "project": str, "url": str,
                              "status": str, "pid": int|null,
                              "expires_at": str, "description": str|null } ] } ] }

/api/contexts:
  { "contexts": [ { "slug": str, "name": str, "repo_path": str,
                     "branch": str|null, "is_primary": bool } ] }
"""

from __future__ import annotations

import json
from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api import (
    delete_report_file,
    mark_report_important,
    render_api_contexts,
    render_api_reports,
    render_api_servers,
    unmark_report_important,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeServerRegistryService:
    def __init__(self, entries: list[tuple[PortEntry, PortStatus]]) -> None:
        self._entries = entries

    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        if project is None:
            return list(self._entries)
        return [(e, s) for e, s in self._entries if e.project == project]


class FakeSpecContextService:
    def __init__(self, contexts: list[SpecContextProject]) -> None:
        self._contexts = contexts

    def list_all(self) -> list[SpecContextProject]:
        return list(self._contexts)


def _make_entry(
    port: int = 3000,
    project: str = "my-project",
    url: str = "http://localhost:3000",
    pid: int | None = 1234,
    status: PortStatus = PortStatus.ACTIVE,
) -> tuple[PortEntry, PortStatus]:
    return (
        PortEntry(
            port=port,
            project=project,
            reserved_at="2026-01-01T00:00:00+00:00",
            expires_at="2026-01-01T08:00:00+00:00",
            url=url,
            pid=pid,
            description="test server",
        ),
        status,
    )


def _make_context(
    slug: str = "my-project",
    name: str = "My Project",
    branch: str | None = "main",
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.ALIVE,
        repo_slug=slug,
        repo_url="https://github.com/org/repo",
        created_at="2026-01-01T00:00:00+00:00",
        alive_since="2026-01-01T00:00:00+00:00",
        dead_since=None,
        current_branch=branch,
    )


def _build_service(
    entries: list[tuple[PortEntry, PortStatus]] | None = None,
    contexts: list[SpecContextProject] | None = None,
    workspace_root: Path = Path("/workspace"),
) -> PanelService:
    return PanelService(
        registry=FakeServerRegistryService(entries or []),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(contexts or []),  # type: ignore[arg-type]
        workspace_root=workspace_root,
    )


# ---------------------------------------------------------------------------
# /api/panel-status contract tests (render_api_servers function)
# ---------------------------------------------------------------------------


def test_api_servers_shape_contract() -> None:
    """If this test fails, panel.js must be updated in lockstep.

    Asserts every required key exists with the correct type in the JSON response.
    """
    entry = _make_entry(port=3000, project="my-project", pid=1234)
    ctx = _make_context(slug="my-project")
    service = _build_service(entries=[entry], contexts=[ctx])

    view = render_api_servers(service)
    status, content_type, body = view()

    assert status == 200
    assert "application/json" in content_type

    data = json.loads(body)

    # Top-level shape
    assert "groups" in data, "Missing top-level key: 'groups'"
    assert isinstance(data["groups"], list)
    assert len(data["groups"]) >= 1

    group = data["groups"][0]
    assert "group_label" in group, "Missing key in group: 'group_label'"
    assert "context_name" in group, "Missing key in group: 'context_name'"
    assert "rows" in group, "Missing key in group: 'rows'"
    assert isinstance(group["group_label"], str)
    assert isinstance(group["rows"], list)
    assert len(group["rows"]) >= 1

    row = group["rows"][0]
    required_row_keys = {"port", "project", "url", "status", "pid", "expires_at", "description"}
    missing = required_row_keys - set(row.keys())
    assert not missing, f"Missing keys in row: {missing}"

    assert isinstance(row["port"], int), "row.port must be int"
    assert isinstance(row["project"], str), "row.project must be str"
    assert isinstance(row["url"], str), "row.url must be str"
    assert row["status"] in ("active", "stale"), (
        f"row.status must be 'active'|'stale', got {row['status']!r}"
    )
    assert row["pid"] is None or isinstance(row["pid"], int), "row.pid must be int or null"
    assert isinstance(row["expires_at"], str), "row.expires_at must be str"


def test_api_servers_empty_registry() -> None:
    """Empty registry returns groups: []. The `unregistered` key was removed in panel-r3."""
    service = _build_service(entries=[], contexts=[])
    view = render_api_servers(service)
    _, _, body = view()
    data = json.loads(body)
    assert data["groups"] == []
    assert "unregistered" not in data


def test_api_servers_content_type() -> None:
    """Content-Type must be application/json; charset=utf-8."""
    service = _build_service()
    view = render_api_servers(service)
    _, content_type, _ = view()
    assert content_type == "application/json; charset=utf-8"


def test_api_servers_stale_status_string() -> None:
    """Stale entries must have status='stale' (not the PortStatus enum value)."""
    entry = _make_entry(status=PortStatus.STALE)
    service = _build_service(entries=[entry])
    view = render_api_servers(service)
    _, _, body = view()
    data = json.loads(body)
    # Find any row
    rows = [r for g in data["groups"] for r in g["rows"]]
    assert any(r["status"] == "stale" for r in rows)


def test_api_reports_reads_handoffs_from_canonical_root(tmp_path: Path) -> None:
    """Panel discovery contract: canonical handoff under .dadaia/handoff/ enriches the report.

    The handoff's produced_at is stamped to "now" (within the 48 h retention
    window) so the test is deterministic regardless of the calendar date.
    """
    import datetime

    now_iso = (
        datetime.datetime.now(tz=datetime.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )

    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "qa.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
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

    service = _build_service(workspace_root=tmp_path)
    status, content_type, body = render_api_reports(service)()

    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert data["reports"][0]["agent"] == "qa-engineer"
    assert data["reports"][0]["path"] == "ctx/qa-engineer/qa.html"
    assert data["reports"][0]["findings_summary"]["HIGH"] == 1


def test_api_reports_lists_html_report_without_handoff(tmp_path: Path) -> None:
    report_path = (
        tmp_path
        / ".dadaia"
        / "reports"
        / "ctx"
        / "project-auditor"
        / "2026-06-04T153239Z-workflow-audit.html"
    )
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>audit</html>", encoding="utf-8")

    service = _build_service(workspace_root=tmp_path)
    status, _, body = render_api_reports(service)()

    assert status == 200
    data = json.loads(body)
    assert data["reports"] == [
        {
            "title": "2026-06-04T153239Z-workflow-audit",
            "agent": "project-auditor",
            "context": "ctx",
            "created_at": "2026-06-04T15:32:39Z",
            "path": "ctx/project-auditor/2026-06-04T153239Z-workflow-audit.html",
            "findings_summary": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "important": False,
            "expires_at": "2026-06-06T15:32:39Z",
            "is_expired": False,
            "retention_reason": "Expires after 48h",
            "retention_status": "expires",
        }
    ]


def test_api_reports_includes_important_retention_state(tmp_path: Path) -> None:
    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "qa.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
    service = _build_service(workspace_root=tmp_path)
    status, _, _ = mark_report_important(service)(path="ctx/qa-engineer/qa.html")
    assert status == 200

    _, _, body = render_api_reports(service)()

    row = json.loads(body)["reports"][0]
    assert row["important"] is True
    assert row["is_expired"] is False
    assert row["retention_reason"] == "Marked important"
    assert row["retention_status"] == "important"


def test_mark_and_unmark_report_important_views(tmp_path: Path) -> None:
    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "qa.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
    service = _build_service(workspace_root=tmp_path)

    mark_status, _, mark_body = mark_report_important(service)(path="ctx/qa-engineer/qa.html")
    unmark_status, _, unmark_body = unmark_report_important(service)(path="ctx/qa-engineer/qa.html")

    assert mark_status == 200
    assert json.loads(mark_body)["important"] is True
    assert unmark_status == 200
    assert json.loads(unmark_body)["important"] is False


def test_api_reports_enriches_html_report_from_legacy_adjacent_handoff(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "qa.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
    handoff_path = report_path.with_suffix(".handoff.json")
    handoff_path.write_text(
        json.dumps(
            {
                "schema_version": "handoff-v1.1",
                "agent": "qa-engineer",
                "context": "ctx",
                "produced_at": "2026-06-04T02:00:00Z",
                "artifact": {
                    "type": "report",
                    "path": ".dadaia/reports/ctx/qa-engineer/qa.html",
                },
                "findings": [
                    {"severity": "CRITICAL", "message": "critical issue"},
                    {"severity": "LOW", "message": "minor issue"},
                ],
            }
        ),
        encoding="utf-8",
    )

    service = _build_service(workspace_root=tmp_path)
    _, _, body = render_api_reports(service)()

    data = json.loads(body)
    assert len(data["reports"]) == 1
    assert data["reports"][0]["path"] == "ctx/qa-engineer/qa.html"
    assert data["reports"][0]["created_at"] == "2026-06-04T02:00:00Z"
    assert data["reports"][0]["findings_summary"]["CRITICAL"] == 1
    assert data["reports"][0]["findings_summary"]["LOW"] == 1


def test_api_reports_skips_self_referential_and_source_file_handoffs(
    tmp_path: Path,
) -> None:
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

    service = _build_service(workspace_root=tmp_path)
    _, _, body = render_api_reports(service)()

    assert json.loads(body)["reports"] == []


def test_api_reports_deduplicates_canonical_and_legacy_handoffs(tmp_path: Path) -> None:
    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "qa.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
    handoff_payload = {
        "agent": "qa-engineer",
        "context": "ctx",
        "produced_at": "2026-06-04T03:00:00Z",
        "artifact": {"path": ".dadaia/reports/ctx/qa-engineer/qa.html"},
        "findings": [{"severity": "HIGH", "message": "issue"}],
    }
    legacy_handoff = report_path.with_suffix(".handoff.json")
    legacy_handoff.write_text(json.dumps(handoff_payload), encoding="utf-8")
    canonical_handoff = tmp_path / ".dadaia" / "handoff" / "ctx" / "qa.handoff.json"
    canonical_handoff.parent.mkdir(parents=True)
    canonical_handoff.write_text(json.dumps(handoff_payload), encoding="utf-8")

    service = _build_service(workspace_root=tmp_path)
    _, _, body = render_api_reports(service)()

    data = json.loads(body)
    assert len(data["reports"]) == 1
    assert data["reports"][0]["title"] == "qa"
    assert data["reports"][0]["path"] == "ctx/qa-engineer/qa.html"
    assert data["reports"][0]["findings_summary"]["HIGH"] == 1


def test_delete_report_removes_handoff_from_canonical_root(tmp_path: Path) -> None:
    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "qa.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
    handoff_path = (
        tmp_path / ".dadaia" / "handoff" / "ctx" / "2026-06-04T000000Z-qa-engineer-qa.handoff.json"
    )
    handoff_path.parent.mkdir(parents=True)
    handoff_path.write_text(
        json.dumps(
            {
                "artifact": {
                    "path": ".dadaia/reports/ctx/qa-engineer/qa.html",
                }
            }
        ),
        encoding="utf-8",
    )

    service = _build_service(workspace_root=tmp_path)
    status, _, _ = delete_report_file(service)(path="ctx/qa-engineer/qa.html")

    assert status == 200
    assert not report_path.exists()
    assert not handoff_path.exists()


def test_delete_report_removes_legacy_adjacent_handoff(tmp_path: Path) -> None:
    report_path = tmp_path / ".dadaia" / "reports" / "ctx" / "qa-engineer" / "qa.html"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("<html>qa</html>", encoding="utf-8")
    handoff_path = report_path.with_suffix(".handoff.json")
    handoff_path.write_text(
        json.dumps({"artifact": {"path": ".dadaia/reports/ctx/qa-engineer/qa.html"}}),
        encoding="utf-8",
    )

    service = _build_service(workspace_root=tmp_path)
    status, _, _ = delete_report_file(service)(path="ctx/qa-engineer/qa.html")

    assert status == 200
    assert not report_path.exists()
    assert not handoff_path.exists()


# ---------------------------------------------------------------------------
# /api/contexts contract tests (T-3.9-bis)
# ---------------------------------------------------------------------------


def test_api_contexts_shape_contract() -> None:
    """If this test fails, panel.js must be updated in lockstep.

    Asserts every required key exists with the correct type in the JSON response.
    """
    ctx = _make_context(slug="dadaia-workspace", name="dadaia-workspace")
    service = _build_service(contexts=[ctx])

    view = render_api_contexts(service)
    status, content_type, body = view()

    assert status == 200
    assert "application/json" in content_type

    data = json.loads(body)

    # Top-level shape
    assert "contexts" in data, "Missing top-level key: 'contexts'"
    assert isinstance(data["contexts"], list)
    assert len(data["contexts"]) >= 1

    context = data["contexts"][0]
    required_keys = {"slug", "name", "repo_path", "branch", "status"}
    missing = required_keys - set(context.keys())
    assert not missing, f"Missing keys in context: {missing}"

    assert isinstance(context["slug"], str), "context.slug must be str"
    assert isinstance(context["name"], str), "context.name must be str"
    assert isinstance(context["repo_path"], str), "context.repo_path must be str"
    assert context["branch"] is None or isinstance(context["branch"], str), (
        "context.branch must be str or null"
    )
    assert context["status"] == "alive", "context.status must be 'alive'"


def test_api_contexts_empty_returns_empty_list() -> None:
    """No active contexts returns contexts: []."""
    service = _build_service(contexts=[])
    view = render_api_contexts(service)
    _, _, body = view()
    data = json.loads(body)
    assert data == {"contexts": []}


def test_api_contexts_content_type() -> None:
    """Content-Type must be application/json; charset=utf-8."""
    service = _build_service(contexts=[_make_context()])
    view = render_api_contexts(service)
    _, content_type, _ = view()
    assert content_type == "application/json; charset=utf-8"


def test_api_contexts_omits_retired_primary_flag() -> None:
    """The contexts API must not expose retired primary-context state."""
    ctx = _make_context()
    service = _build_service(contexts=[ctx])
    view = render_api_contexts(service)
    _, _, body = view()
    data = json.loads(body)
    assert "is_primary" not in data["contexts"][0]


def test_api_contexts_branch_none_serialised_as_null() -> None:
    """branch=None must serialise as JSON null."""
    ctx = _make_context(branch=None)
    service = _build_service(contexts=[ctx])
    view = render_api_contexts(service)
    _, _, body = view()
    data = json.loads(body)
    assert data["contexts"][0]["branch"] is None
