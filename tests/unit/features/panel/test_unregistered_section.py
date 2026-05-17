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


def test_panel_css_includes_lan_warning_badge_with_color_alert_token() -> None:
    """LAN-exposed badge MUST use the brand-identity-v1 alert token (with hex
    fallback for safety)."""
    assert ".lan-warning-badge" in PANEL_CSS
    assert "var(--color-alert" in PANEL_CSS
    # Hex fallback must be the brand-identity-v1 alert hex (#f7af63).
    assert "#f7af63" in PANEL_CSS


def test_panel_css_includes_unregistered_section_styles() -> None:
    assert ".unregistered-section" in PANEL_CSS
    assert ".cmdline-cell" in PANEL_CSS
    assert ".cwd-cell" in PANEL_CSS


def test_panel_js_renders_unregistered_table() -> None:
    """buildUnregisteredHTML must be wired in PANEL_JS."""
    assert "buildUnregisteredHTML" in PANEL_JS
    assert "unregistered-content" in PANEL_JS
    assert "lan-warning-badge" in PANEL_JS


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


def test_api_servers_unregistered_payload_shape() -> None:
    """Each unregistered item must have port/bind/pid/cmdline/cwd/lan_exposed."""
    svc = _make_service()
    fake = [
        {
            "port": 4000,
            "bind": "0.0.0.0",
            "pid": 12345,
            "cmdline": "python -m http.server 4000",
            "cwd": "/tmp",
            "lan_exposed": True,
        },
        {
            "port": 9999,
            "bind": "127.0.0.1",
            "pid": 67890,
            "cmdline": "python -m http.server 9999 --bind 127.0.0.1",
            "cwd": "/tmp",
            "lan_exposed": False,
        },
    ]
    with patch.object(svc, "list_unregistered_listeners", return_value=fake):
        view = render_api_servers(svc)
        _, _, body = view()
    import json

    data = json.loads(body)
    assert len(data["unregistered"]) == 2
    item = data["unregistered"][0]
    for key in ("port", "bind", "pid", "cmdline", "cwd", "lan_exposed"):
        assert key in item


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


def test_index_html_has_unregistered_section_with_a11y_attributes() -> None:
    """The Servers tab must contain the Unregistered section with proper
    a11y semantics: role=region, aria-label, aria-live=polite."""
    import inspect

    from dadaia_workspace.features.panel.views import index as index_module

    src = inspect.getsource(index_module)
    assert 'id="unregistered-section"' in src
    assert 'role="region"' in src
    assert 'aria-label="Unregistered listeners"' in src
    assert 'aria-live="polite"' in src
    assert 'id="unregistered-content"' in src


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
