"""Smoke test for build_panel_views composition function.

Exercises every key in the views dict with the simplest valid inputs.
Uses fakes instead of the real container to avoid requiring an initialized workspace.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import ContextState, SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_contexts import render_api_contexts
from dadaia_workspace.features.panel.views.api_servers import render_api_servers
from dadaia_workspace.features.panel.views.index import render_index
from dadaia_workspace.features.panel.views.memory import render_memory
from dadaia_workspace.features.panel.views.static import render_static
from dadaia_workspace.features.panel.views.wrapper import render_memory_wrapper

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeServerRegistryService:
    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        return []


class FakeSpecContextService:
    def list_all(self) -> list[SpecContextProject]:
        return [
            SpecContextProject(
                name="dadaia-workspace",
                state=ContextState.ALIVE,
                repo_slug="dadaia-workspace",
                repo_url="https://github.com/org/dadaia-workspace",
                created_at="2026-01-01T00:00:00+00:00",
                alive_since="2026-01-01T00:00:00+00:00",
                dead_since=None,
                current_branch="main",
            )
        ]


def _build_views(tmp_path: Path) -> dict:  # type: ignore[type-arg]
    """Build a views dict the same way build_panel_views would, but using fakes."""
    service = PanelService(
        registry=FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=tmp_path,
    )
    return {
        "index": render_index(service),
        "api_panel_status": render_api_servers(service),
        "api_contexts": render_api_contexts(service),
        "memory": render_memory(tmp_path),
        "memory_view": render_memory_wrapper(tmp_path),
        "static": render_static(),
    }


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


def test_all_view_keys_present(tmp_path: Path) -> None:
    """All 6 required view keys must be present."""
    views = _build_views(tmp_path)
    expected_keys = {"index", "api_panel_status", "api_contexts", "memory", "memory_view", "static"}
    assert set(views.keys()) == expected_keys


def test_index_view_callable(tmp_path: Path) -> None:
    """index view must return (200, 'text/html; charset=utf-8', bytes)."""
    views = _build_views(tmp_path)
    status, ct, body = views["index"]()
    assert status == 200
    assert "text/html" in ct
    assert isinstance(body, bytes)
    assert len(body) > 0


def test_api_panel_status_view_callable(tmp_path: Path) -> None:
    """api_panel_status view must return (200, 'application/json; charset=utf-8', bytes)."""
    views = _build_views(tmp_path)
    status, ct, body = views["api_panel_status"]()
    assert status == 200
    assert "application/json" in ct
    assert isinstance(body, bytes)


def test_api_contexts_view_callable(tmp_path: Path) -> None:
    """api_contexts view must return (200, 'application/json; charset=utf-8', bytes)."""
    views = _build_views(tmp_path)
    status, ct, body = views["api_contexts"]()
    assert status == 200
    assert "application/json" in ct
    assert isinstance(body, bytes)


def test_memory_view_missing_file_returns_404(tmp_path: Path) -> None:
    """memory view returns 404 for a nonexistent file."""
    views = _build_views(tmp_path)
    status, _, _ = views["memory"](slug="dadaia-workspace", path="architecture.html")
    assert status == 404  # file doesn't exist in tmp_path


def test_memory_view_serves_file(tmp_path: Path) -> None:
    """memory view serves a file byte-identically."""
    data = b"<html>test</html>"
    specs_dir = tmp_path / "repos" / "dadaia-workspace" / "specs" / "memory"
    specs_dir.mkdir(parents=True)
    (specs_dir / "architecture.html").write_bytes(data)

    views = _build_views(tmp_path)
    status, ct, body = views["memory"](slug="dadaia-workspace", path="architecture.html")
    assert status == 200
    assert body == data


def test_memory_view_wrapper_callable(tmp_path: Path) -> None:
    """memory_view view must return (200, 'text/html; charset=utf-8', bytes) with iframe."""
    views = _build_views(tmp_path)
    status, ct, body = views["memory_view"](slug="dadaia-workspace", path="architecture.html")
    assert status == 200
    assert "text/html" in ct
    page = body.decode("utf-8")
    assert "iframe" in page
    assert "/memory/dadaia-workspace/architecture.html" in page


def test_memory_view_wrapper_links_memory_css(tmp_path: Path) -> None:
    """memory_view must link /static/memory.css for panel visual identity."""
    views = _build_views(tmp_path)
    status, _, body = views["memory_view"](slug="dadaia-workspace", path="architecture.html")
    assert status == 200
    assert "/static/memory.css" in body.decode("utf-8")


def test_static_css_callable(tmp_path: Path) -> None:
    """static view must serve tokens.css."""
    views = _build_views(tmp_path)
    status, ct, _ = views["static"](name="tokens.css")
    assert status == 200
    assert "text/css" in ct


def test_static_js_callable(tmp_path: Path) -> None:
    """static view must serve core.js."""
    views = _build_views(tmp_path)
    status, ct, _ = views["static"](name="core.js")
    assert status == 200
    assert "javascript" in ct


def test_static_unknown_returns_404(tmp_path: Path) -> None:
    """static view returns 404 for unknown asset names."""
    views = _build_views(tmp_path)
    status, _, _ = views["static"](name="robots.txt")
    assert status == 404


# ---------------------------------------------------------------------------
# Container-sanity: the REAL container.build_panel_views must wire without the
# removed kanban view (v0.1.52 T-52-13). Importing container exercises the
# module-level imports (a dangling render_api_kanban import → ImportError), and
# calling build_panel_views exercises the views-dict construction (a dangling
# render_api_kanban(...) reference → NameError). Both must be clean.
# ---------------------------------------------------------------------------


def test_container_build_panel_views_constructs_without_kanban(tmp_path: Path) -> None:
    """container.build_panel_views wires the panel dict; api_kanban is gone."""
    from dadaia_workspace import container

    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text('{"schema_version": "2", "contexts": []}')

    views = container.build_panel_views(tmp_path)

    assert isinstance(views, dict)
    assert "api_kanban" not in views
    assert "index" in views
    assert "api_contexts" in views
    assert all(callable(v) for v in views.values())
