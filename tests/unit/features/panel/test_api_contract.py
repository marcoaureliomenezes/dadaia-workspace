"""Intent: CONTRACT — AC10 (FR9, T-046-27): the panel carries no reports surface.

The ``.dadaia/reports/`` zone is retired: HTML reports live in the repo
(``repos/<slug>/reports/<agent>/``) and the panel neither lists, serves, marks nor
deletes them. This file pins the absence at the panel's interfaces — the route table,
the static asset map and the ``PanelService`` constructor — so neither a route nor the
retention seam can quietly grow back.
"""

from __future__ import annotations

import inspect

import pytest

from dadaia_workspace.features.panel import handler as handler_module
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.static import render_static

pytestmark = pytest.mark.unit


def test_route_table_has_no_reports_route() -> None:
    offenders = [
        (route.method, route.pattern.pattern, route.view_name)
        for route in handler_module._ROUTES
        if "reports" in route.pattern.pattern or "report" in route.view_name
    ]
    assert offenders == [], f"reports routes survive in the panel route table: {offenders}"


@pytest.mark.parametrize("name", ["reports.css", "reports-doc.css", "reports.js"])
def test_reports_static_assets_are_not_served(name: str) -> None:
    status, _content_type, _body = render_static()(name=name)
    assert status == 404


def test_panel_service_has_no_report_retention_seam() -> None:
    assert "report_retention" not in inspect.signature(PanelService.__init__).parameters
    assert not hasattr(PanelService, "get_report_retention")
