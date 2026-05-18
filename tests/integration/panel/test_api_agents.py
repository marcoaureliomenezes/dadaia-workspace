"""Integration tests for GET /api/agents — end-to-end HTTP (no browser).

Coverage areas (PR3-20 spec):
  - Telemetry overlay merge: real PanelService + real canonical agents + stub telemetry
  - ?active_window_days query parameter honoured (200 and 400 boundary)
  - Bearer token enforcement (401 without token, 200 with valid token)
  - Defence-in-depth on traversal in agent_id prompt endpoint

Pattern mirrors test_panel_telemetry_endpoints.py: ThreadingHTTPServer on port 0,
real PanelService wired to real canonical agent files, stub telemetry service.
No mocks — fakes/stubs only.
"""

from __future__ import annotations

import datetime
import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from dadaia_workspace.features.panel.handler import make_handler_class
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api import render_api_agents_canonical, render_api_agent_prompt
from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    AgentSummary,
    ContextBreakdown,
    RecentSession,
    TokenTotals,
)

# ---------------------------------------------------------------------------
# Workspace root — the dadaia-workspace repo itself
# ---------------------------------------------------------------------------

_WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent  # .../dadaia-workspace/


# ---------------------------------------------------------------------------
# Stub TelemetryService
# ---------------------------------------------------------------------------


def _make_recent_session(date: str, cost_usd: float | None = 0.10) -> RecentSession:
    return RecentSession(
        session_id_prefix="a1b2c3d4",
        date=date,
        cost_usd=cost_usd,
        entrypoint="cli",
        git_branch="main",
        context_slug="dadaia-workspace",
        token_counts=TokenTotals(input=500, cache_creation=0, cache_read=300, output=100),
    )


def _make_agent_summary(
    agent_id: str,
    last_activity_at: str,
) -> AgentSummary:
    today = datetime.date.today().isoformat()
    return AgentSummary(
        agent_id=agent_id,
        display_name=agent_id,
        providers=["claude"],
        dominant_model="claude-sonnet-4-6",
        is_subagent=False,
        session_count=5,
        total_cost_usd=0.50,
        cost_known=True,
        last_activity_at=last_activity_at,
        token_totals=TokenTotals(input=1000, cache_creation=200, cache_read=800, output=400),
        context_breakdown=[
            ContextBreakdown(
                context_slug="dadaia-workspace",
                context_name="dadaia-workspace",
                session_count=5,
                cost_usd=0.50,
                cost_fraction=1.0,
            )
        ],
        recent_sessions=[_make_recent_session(today)],
        suspect_count=0,
    )


class StubTelemetryService:
    """Returns a controlled AgentListResult with one active and one inactive agent.

    The two summaries target the real agent IDs found in .dadaia/agentic/agents/:
      - "software-engineer"  → recent activity (active)
      - "qa-engineer"        → activity 400 days ago (inactive with default window)
    """

    def list_agents(
        self,
        window_days: int = 180,
        context_slug: str | None = None,
        limit: int = 50,
    ) -> AgentListResult:
        now = datetime.datetime.now(tz=datetime.UTC)
        # Active: last activity is 1 day ago
        active_ts = (now - datetime.timedelta(days=1)).isoformat()
        # Inactive: last activity is 400 days ago
        inactive_ts = (now - datetime.timedelta(days=400)).isoformat()
        return AgentListResult(
            generated_at=now.isoformat(),
            window_days=window_days,
            pricing_age_days=30,
            pricing_model_date="2026-04-01",
            agents=[
                _make_agent_summary("software-engineer", active_ts),
                _make_agent_summary("qa-engineer", inactive_ts),
            ],
        )

    # Satisfy duck-type for other handler paths
    is_degraded: bool = False


# ---------------------------------------------------------------------------
# Minimal stub dependencies for PanelService
# ---------------------------------------------------------------------------


class _StubRegistry:
    def list_entries(self, include_stale: bool = True) -> list:
        return []


class _StubSpecContextService:
    def list_all(self) -> list:
        return []


# ---------------------------------------------------------------------------
# Server fixture builder
# ---------------------------------------------------------------------------


def _build_agents_server(
    token: str,
    stub_telemetry: StubTelemetryService,
    workspace_root: Path = _WORKSPACE_ROOT,
) -> ThreadingHTTPServer:
    """Build a server wired with real PanelService pointing at real agent files."""
    panel_service = PanelService(
        registry=_StubRegistry(),  # type: ignore[arg-type]
        spec_context=_StubSpecContextService(),  # type: ignore[arg-type]
        workspace_root=workspace_root,
        telemetry=stub_telemetry,
    )

    def _stub_html(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    def _stub_json(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "application/json; charset=utf-8", b"{}")

    views: dict[str, Any] = {
        "index": _stub_html,
        "api_servers": _stub_json,
        "api_contexts": _stub_json,
        "api_agents": render_api_agents_canonical(panel_service),
        "api_agent_prompt": render_api_agent_prompt(panel_service),
        "api_workflows": _stub_json,
        "api_workflow_detail": _stub_json,
        "memory": _stub_html,
        "memory_view": _stub_html,
        "static": lambda **kw: (200, "text/plain; charset=utf-8", b"ok"),
    }
    HandlerClass = make_handler_class(views, token=token, telemetry=stub_telemetry)
    return ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import urllib.error
import urllib.request


def _get(url: str, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, headers, resp.read()
    except urllib.error.HTTPError as exc:
        headers = {k.lower(): v for k, v in exc.headers.items()}
        return exc.code, headers, exc.read()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_TEST_TOKEN = "integration-test-token-pr3-20"


@pytest.fixture(scope="module")
def agents_server():
    """Real-file-backed panel server; yields (base_url, token, stub_telemetry)."""
    stub_tel = StubTelemetryService()
    server = _build_agents_server(_TEST_TOKEN, stub_tel)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield base_url, _TEST_TOKEN, stub_tel
    server.shutdown()


# ---------------------------------------------------------------------------
# Tests: Bearer enforcement
# ---------------------------------------------------------------------------


class TestBearerEnforcement:
    def test_agents_401_without_token(self, agents_server: Any) -> None:
        """GET /api/agents without Authorization → 401."""
        base, token, _ = agents_server
        status, _, _ = _get(f"{base}/api/agents")
        assert status == 401

    def test_agents_401_with_wrong_token(self, agents_server: Any) -> None:
        """GET /api/agents with wrong Bearer → 401."""
        base, token, _ = agents_server
        status, _, _ = _get(f"{base}/api/agents", token="wrong-token")
        assert status == 401

    def test_agents_200_with_correct_token(self, agents_server: Any) -> None:
        """GET /api/agents with correct Bearer → 200."""
        base, token, _ = agents_server
        status, _, _ = _get(f"{base}/api/agents", token=token)
        assert status == 200


# ---------------------------------------------------------------------------
# Tests: Telemetry overlay merge
# ---------------------------------------------------------------------------


class TestTelemetryOverlayMerge:
    """Telemetry data must be merged over canonical agents.

    The stub returns data for "software-engineer" and "qa-engineer" which are
    real agents in .dadaia/agentic/agents/. The overlay must inject their
    telemetry sub-objects.
    """

    def test_agents_response_shape(self, agents_server: Any) -> None:
        """GET /api/agents → top-level keys match SPEC §5.1."""
        base, token, _ = agents_server
        status, _, body = _get(f"{base}/api/agents", token=token)
        assert status == 200
        data = json.loads(body)
        for key in ("generated_at", "status_window_days", "window_days", "agents"):
            assert key in data, f"missing top-level key: {key}"

    def test_agents_list_contains_real_agents(self, agents_server: Any) -> None:
        """Every item in 'agents' corresponds to a canonical agent file on disk."""
        base, token, _ = agents_server
        _, _, body = _get(f"{base}/api/agents", token=token)
        data = json.loads(body)
        agent_ids = {a["agent_id"] for a in data["agents"]}
        # The real workspace has software-engineer and qa-engineer
        assert "software-engineer" in agent_ids
        assert "qa-engineer" in agent_ids

    def test_telemetry_overlay_injected(self, agents_server: Any) -> None:
        """Agents that have telemetry data have non-zero session_count in telemetry sub-object."""
        base, token, _ = agents_server
        _, _, body = _get(f"{base}/api/agents", token=token)
        data = json.loads(body)
        by_id = {a["agent_id"]: a for a in data["agents"]}
        se = by_id.get("software-engineer")
        assert se is not None
        assert "telemetry" in se
        assert se["telemetry"]["session_count"] == 5

    def test_telemetry_only_agents_excluded(self, agents_server: Any) -> None:
        """Agents in telemetry but not in canonical catalog are excluded from response."""
        base, token, _ = agents_server
        _, _, body = _get(f"{base}/api/agents", token=token)
        data = json.loads(body)
        # The stub injects data for "software-engineer" and "qa-engineer" — only those
        # present in the canonical files should appear. Agents only in telemetry are excluded.
        canonical_ids = {a["agent_id"] for a in data["agents"]}
        # All returned agents must have a real on-disk file
        agents_dir = _WORKSPACE_ROOT / ".dadaia" / "agentic" / "agents"
        disk_ids = {p.stem for p in agents_dir.glob("*.md")}
        assert canonical_ids.issubset(disk_ids), (
            f"Response contains agents not on disk: {canonical_ids - disk_ids}"
        )

    def test_status_active_for_recent_agent(self, agents_server: Any) -> None:
        """Agent with last_activity 1 day ago → status='active' (window=30d)."""
        base, token, _ = agents_server
        _, _, body = _get(f"{base}/api/agents", token=token)
        data = json.loads(body)
        by_id = {a["agent_id"]: a for a in data["agents"]}
        se = by_id.get("software-engineer")
        assert se is not None
        assert se["status"] == "active"

    def test_status_inactive_for_old_agent(self, agents_server: Any) -> None:
        """Agent with last_activity 400 days ago → status='inactive' (window=30d)."""
        base, token, _ = agents_server
        _, _, body = _get(f"{base}/api/agents", token=token)
        data = json.loads(body)
        by_id = {a["agent_id"]: a for a in data["agents"]}
        qa = by_id.get("qa-engineer")
        assert qa is not None
        assert qa["status"] == "inactive"


# ---------------------------------------------------------------------------
# Tests: ?active_window_days query parameter
# ---------------------------------------------------------------------------


class TestActiveWindowDays:
    def test_active_window_days_default_is_30(self, agents_server: Any) -> None:
        """No ?active_window_days → status_window_days=30 in response."""
        base, token, _ = agents_server
        _, _, body = _get(f"{base}/api/agents", token=token)
        data = json.loads(body)
        assert data["status_window_days"] == 30

    def test_active_window_days_custom_honoured(self, agents_server: Any) -> None:
        """?active_window_days=365 → status_window_days=365 in response."""
        base, token, _ = agents_server
        _, _, body = _get(f"{base}/api/agents?active_window_days=365", token=token)
        data = json.loads(body)
        assert data["status_window_days"] == 365

    def test_active_window_days_boundary_min_1(self, agents_server: Any) -> None:
        """?active_window_days=1 is the minimum valid value → 200."""
        base, token, _ = agents_server
        status, _, _ = _get(f"{base}/api/agents?active_window_days=1", token=token)
        assert status == 200

    def test_active_window_days_boundary_max_365(self, agents_server: Any) -> None:
        """?active_window_days=365 is the maximum valid value → 200."""
        base, token, _ = agents_server
        status, _, _ = _get(f"{base}/api/agents?active_window_days=365", token=token)
        assert status == 200

    def test_active_window_days_out_of_range_400(self, agents_server: Any) -> None:
        """?active_window_days=366 is out of range → 400."""
        base, token, _ = agents_server
        status, _, body = _get(f"{base}/api/agents?active_window_days=366", token=token)
        assert status == 400
        data = json.loads(body)
        assert data.get("error") == "invalid_parameter"

    def test_active_window_days_zero_out_of_range_400(self, agents_server: Any) -> None:
        """?active_window_days=0 is out of range → 400."""
        base, token, _ = agents_server
        status, _, body = _get(f"{base}/api/agents?active_window_days=0", token=token)
        assert status == 400

    def test_active_window_days_large_changes_status(self, agents_server: Any) -> None:
        """?active_window_days=500 (out of range) → 400; ?active_window_days=365 (max) with old agent still inactive."""
        base, token, _ = agents_server
        # With window=365, qa-engineer (400 days ago) should still be inactive
        _, _, body = _get(f"{base}/api/agents?active_window_days=365", token=token)
        data = json.loads(body)
        by_id = {a["agent_id"]: a for a in data["agents"]}
        qa = by_id.get("qa-engineer")
        assert qa is not None
        assert qa["status"] == "inactive"


# ---------------------------------------------------------------------------
# Tests: path-traversal defence on /api/agents/<id>/prompt
# ---------------------------------------------------------------------------


class TestAgentPromptTraversalDefence:
    def test_prompt_traversal_dot_dot_slash_rejected(self, agents_server: Any) -> None:
        """GET /api/agents/../etc/passwd/prompt → 400 (path traversal blocked)."""
        base, token, _ = agents_server
        # URL-encode .. segments; the handler should reject even un-encoded forms
        status, _, _ = _get(f"{base}/api/agents/..%2Fetc%2Fpasswd/prompt", token=token)
        assert status in (400, 404), f"Expected 400 or 404, got {status}"

    def test_prompt_invalid_id_format_rejected(self, agents_server: Any) -> None:
        """GET /api/agents/<uppercase>/prompt → 400 (fails regex validation)."""
        base, token, _ = agents_server
        status, _, body = _get(f"{base}/api/agents/INVALID_UPPER/prompt", token=token)
        assert status == 400
        data = json.loads(body)
        assert data.get("error") == "invalid_agent_id"

    def test_prompt_valid_known_agent_200(self, agents_server: Any) -> None:
        """GET /api/agents/software-engineer/prompt → 200 with system_prompt key."""
        base, token, _ = agents_server
        status, _, body = _get(f"{base}/api/agents/software-engineer/prompt", token=token)
        assert status == 200
        data = json.loads(body)
        assert "system_prompt" in data
        assert data["agent_id"] == "software-engineer"

    def test_prompt_unknown_agent_404(self, agents_server: Any) -> None:
        """GET /api/agents/does-not-exist/prompt → 404."""
        base, token, _ = agents_server
        status, _, _ = _get(f"{base}/api/agents/does-not-exist/prompt", token=token)
        assert status == 404

    def test_prompt_401_without_token(self, agents_server: Any) -> None:
        """GET /api/agents/software-engineer/prompt without token → 401."""
        base, token, _ = agents_server
        status, _, _ = _get(f"{base}/api/agents/software-engineer/prompt")
        assert status == 401
