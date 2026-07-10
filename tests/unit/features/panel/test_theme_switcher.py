"""FOUC pre-paint contract for the panel theme switcher (single merged golden).

All other theme_switcher.py source-grep coverage (IIFE wrapping, Escape/arrow-key
handling, localStorage key/setItem usage, aria-* attribute presence, dropdown
menuitemradio count) is owned by the Playwright E2E suite (E2E-THM-01..10,
including the in-browser FOUC proof at THM-06) and by
``test_index_dom_contract.py`` (aria/button/dropdown selector presence).

This unit test keeps ONE fast detector: the inline pre-paint script lives in
``<head>`` before the first stylesheet, reads ``localStorage['dadaia-panel-theme']``,
and sets ``dataset.theme`` on the document element — the mechanism that avoids
Flash Of Unstyled Content on first paint.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.core.models.server_registry import PortEntry, PortStatus
from dadaia_workspace.core.models.spec_context import SpecContextProject
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.index import render_index

pytestmark = pytest.mark.unit


class FakeServerRegistryService:
    def list_entries(
        self, project: str | None = None, include_stale: bool = True
    ) -> list[tuple[PortEntry, PortStatus]]:
        return []


class FakeSpecContextService:
    def list_all(self) -> list[SpecContextProject]:
        return []


def _render() -> str:
    service = PanelService(
        registry=FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
    )
    view = render_index(service)
    status, content_type, body = view()
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    return body.decode("utf-8")


def test_fouc_prepaint_script_precedes_stylesheets_and_sets_theme() -> None:
    """The inline pre-paint <script> in <head> reads localStorage and sets
    data-theme before the first stylesheet <link> — the FOUC-prevention mechanism.
    E2E-THM-06 proves the effect in-browser; this is the fast unit detector."""
    html = _render()

    head_end = html.find("</head>")
    assert head_end > 0, "No </head> found"
    head_section = html[:head_end]

    first_script_pos = html.find("<script>")
    first_stylesheet_pos = html.find('<link rel="stylesheet"')
    assert first_script_pos > 0, "No inline <script> found"
    assert first_stylesheet_pos > 0, "No stylesheet link found"
    assert first_script_pos < first_stylesheet_pos, (
        "Pre-paint <script> must come before the first stylesheet <link> in <head>"
    )
    assert "<script>" in head_section, "No inline <script> in <head>"
    assert "dadaia-panel-theme" in head_section, (
        "Pre-paint script must reference localStorage key 'dadaia-panel-theme'"
    )
    assert "dataset.theme" in head_section or "data-theme" in head_section, (
        "Pre-paint script must set data-theme on <html> element"
    )
