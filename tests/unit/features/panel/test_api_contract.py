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
from dadaia_workspace.features.panel.views.api import render_api_contexts, render_api_servers

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
    is_primary: bool = False,
) -> SpecContextProject:
    return SpecContextProject(
        name=name,
        state=ContextState.ATIVO,
        repo_slug=slug,
        repo_url="https://github.com/org/repo",
        is_primary=is_primary,
        created_at="2026-01-01T00:00:00+00:00",
        activated_at="2026-01-01T00:00:00+00:00",
        current_branch=branch,
    )


def _build_service(
    entries: list[tuple[PortEntry, PortStatus]] | None = None,
    contexts: list[SpecContextProject] | None = None,
) -> PanelService:
    return PanelService(
        registry=FakeServerRegistryService(entries or []),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(contexts or []),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
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


# ---------------------------------------------------------------------------
# /api/contexts contract tests (T-3.9-bis)
# ---------------------------------------------------------------------------


def test_api_contexts_shape_contract() -> None:
    """If this test fails, panel.js must be updated in lockstep.

    Asserts every required key exists with the correct type in the JSON response.
    """
    ctx = _make_context(slug="dadaia-workspace", name="dadaia-workspace", is_primary=True)
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
    required_keys = {"slug", "name", "repo_path", "branch", "is_primary", "status"}
    missing = required_keys - set(context.keys())
    assert not missing, f"Missing keys in context: {missing}"

    assert isinstance(context["slug"], str), "context.slug must be str"
    assert isinstance(context["name"], str), "context.name must be str"
    assert isinstance(context["repo_path"], str), "context.repo_path must be str"
    assert context["branch"] is None or isinstance(context["branch"], str), (
        "context.branch must be str or null"
    )
    assert isinstance(context["is_primary"], bool), "context.is_primary must be bool"
    assert context["status"] in ("local", "remote"), "context.status must be 'local' or 'remote'"


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


def test_api_contexts_is_primary_true() -> None:
    """is_primary must be Python bool true for the primary context."""
    ctx = _make_context(is_primary=True)
    service = _build_service(contexts=[ctx])
    view = render_api_contexts(service)
    _, _, body = view()
    data = json.loads(body)
    assert data["contexts"][0]["is_primary"] is True


def test_api_contexts_branch_none_serialised_as_null() -> None:
    """branch=None must serialise as JSON null."""
    ctx = _make_context(branch=None)
    service = _build_service(contexts=[ctx])
    view = render_api_contexts(service)
    _, _, body = view()
    data = json.loads(body)
    assert data["contexts"][0]["branch"] is None
