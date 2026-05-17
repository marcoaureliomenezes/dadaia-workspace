"""Snapshot tests for the panel's Unregistered listeners section (v0.1.1 / T-DSR-09)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dadaia_workspace.core.models.server_registry import (
    PortEntry,
    UnregisteredListener,
)
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views._assets import PANEL_CSS, PANEL_JS
from dadaia_workspace.features.panel.views.api import render_api_servers

# --- helpers ---------------------------------------------------------------


class _StubRegistry:
    def __init__(self, entries: list[PortEntry]) -> None:
        from dadaia_workspace.core.models.server_registry import PortStatus

        self._items = [(e, PortStatus.ACTIVE) for e in entries]

    def list_entries(self, include_stale: bool = True) -> list[tuple]:  # noqa: ARG002
        return list(self._items)


class _StubContextService:
    def list_all(self) -> list:
        return []


def _make_service() -> PanelService:
    from pathlib import Path

    return PanelService(
        registry=_StubRegistry([]),  # type: ignore[arg-type]
        spec_context=_StubContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/tmp"),
    )


# --- CSS / static assertions ----------------------------------------------


def test_panel_css_has_alert_color_token() -> None:
    """brand-identity-v1 alert token must still be defined in CSS
    (used by agent-suspect-badge and other elements), even though
    lan-warning-badge was removed in panel-defects hotfix."""
    assert "var(--color-alert" in PANEL_CSS
    # The CSS custom property must carry the brand-identity-v1 hex.
    assert "#f7af63" in PANEL_CSS
    # lan-warning-badge itself is removed.
    assert ".lan-warning-badge" not in PANEL_CSS


def test_panel_css_no_unregistered_section_styles() -> None:
    """panel-defects hotfix: unregistered section removed from UI — CSS must
    no longer carry its selectors."""
    assert ".unregistered-section" not in PANEL_CSS
    assert ".cmdline-cell" not in PANEL_CSS
    assert ".cwd-cell" not in PANEL_CSS


def test_panel_js_no_unregistered_renderer() -> None:
    """panel-defects hotfix: unregistered section removed — JS must not
    contain buildUnregisteredHTML or the unregistered-content container ref."""
    assert "buildUnregisteredHTML" not in PANEL_JS
    assert "unregistered-content" not in PANEL_JS
    assert "lan-warning-badge" not in PANEL_JS


# --- API payload shape ----------------------------------------------------


def test_api_servers_includes_unregistered_key_in_payload() -> None:
    """The /api/servers endpoint MUST emit the new `unregistered` key,
    backward-compat is preserved by clients ignoring unknown keys."""
    svc = _make_service()
    with patch.object(svc, "list_unregistered_listeners", return_value=[]):
        view = render_api_servers(svc)
        status, content_type, body = view()
    assert status == 200
    assert content_type.startswith("application/json")
    import json

    data = json.loads(body)
    assert "groups" in data
    assert "unregistered" in data
    assert data["unregistered"] == []


def test_api_servers_unregistered_always_empty_after_hotfix() -> None:
    """panel-defects hotfix: the UI section was removed so the endpoint
    always returns unregistered=[] — the service scan is no longer invoked."""
    svc = _make_service()
    view = render_api_servers(svc)
    _, _, body = view()
    import json

    data = json.loads(body)
    # Back-compat key must still exist but is always empty.
    assert "unregistered" in data
    assert data["unregistered"] == []


def test_api_servers_degrades_gracefully_when_scan_fails() -> None:
    """If list_unregistered_listeners raises (e.g. ss missing), the endpoint
    must still return 200 with unregistered=[]."""
    svc = _make_service()
    with patch.object(svc, "list_unregistered_listeners", side_effect=RuntimeError("ss missing")):
        view = render_api_servers(svc)
        status, _, body = view()
    assert status == 200
    import json

    data = json.loads(body)
    assert data["unregistered"] == []


# --- Service-layer integration --------------------------------------------


def test_service_list_unregistered_listeners_filters_registered_ports() -> None:
    """PanelService.list_unregistered_listeners must call scan with the current
    registry entries so registered ports are filtered out."""
    svc = _make_service()
    fake_finding = UnregisteredListener(
        port=9999,
        bind="127.0.0.1",
        pid=999,
        cmdline="x",
        cwd="/tmp",
        lan_exposed=False,
    )
    with patch(
        "dadaia_workspace.features.server_registry.scan.scan_unregistered_listeners",
        return_value=[fake_finding],
    ) as scan_mock:
        result = svc.list_unregistered_listeners()
    assert len(result) == 1
    assert result[0]["port"] == 9999
    assert result[0]["lan_exposed"] is False
    # Verify the scan was called with the registry's entries
    scan_mock.assert_called_once()


def test_service_list_unregistered_listeners_is_a11y_friendly_dict_shape() -> None:
    """The dict must contain primitives only (so the panel JS can render
    without escaping bugs)."""
    svc = _make_service()
    fake_finding = UnregisteredListener(
        port=4000,
        bind="0.0.0.0",
        pid=42,
        cmdline="cmd",
        cwd="/cwd",
        lan_exposed=True,
    )
    with patch(
        "dadaia_workspace.features.server_registry.scan.scan_unregistered_listeners",
        return_value=[fake_finding],
    ):
        result = svc.list_unregistered_listeners()
    item = result[0]
    assert isinstance(item["port"], int)
    assert isinstance(item["bind"], str)
    assert isinstance(item["pid"], int)
    assert isinstance(item["cmdline"], str)
    assert isinstance(item["cwd"], str)
    assert isinstance(item["lan_exposed"], bool)


# --- HTML structure -------------------------------------------------------


def test_index_html_has_no_unregistered_section() -> None:
    """panel-defects hotfix: the Servers tab must NOT contain the Unregistered
    section anymore — it was removed from the UI."""
    import inspect

    from dadaia_workspace.features.panel.views import index as index_module

    src = inspect.getsource(index_module)
    assert 'id="unregistered-section"' not in src
    assert 'id="unregistered-content"' not in src


@pytest.mark.parametrize(
    ("hex_value", "should_appear"),
    [
        ("#f7af63", True),  # alert hex (brand-identity-v1) must be in CSS fallback
    ],
)
def test_brand_alert_hex_is_present_in_lan_badge(hex_value: str, should_appear: bool) -> None:
    """Direct hex assertion — the LAN warning badge fallback hex must equal
    the brand-identity-v1 alert token #f7af63 to stay consistent."""
    assert (hex_value in PANEL_CSS) is should_appear
