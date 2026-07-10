"""Container-sanity test for container.build_panel_views (v0.1.52 T-52-13).

Every per-view smoke test that used to live here (index/api_panel_status/
api_contexts/memory/memory_view/static callables) duplicated coverage already
owned by the per-view test suites — deleted. What remains is the ONE thing no
other test proves: the REAL container wires the views dict without the
removed kanban view. Importing container exercises the module-level imports
(a dangling render_api_kanban import -> ImportError), and calling
build_panel_views exercises the views-dict construction (a dangling
render_api_kanban(...) reference -> NameError). Both must be clean.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


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
