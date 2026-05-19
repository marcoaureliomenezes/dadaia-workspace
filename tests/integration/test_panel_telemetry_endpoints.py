"""Integration tests for the panel's telemetry API endpoints (T-AM-15).

Spins up ThreadingHTTPServer on port 0 (random free port) with a stub
TelemetryService that returns canned fixtures.  Uses urllib.request only
(stdlib; no requests).

Tests are sequenced around the three endpoints:
    GET /api/agents           — 401 without token, 200 with token
    GET /api/workflows        — same
    GET /api/agents/{id}/sessions — same
    Privacy T1: no forbidden fields in any payload
    Query string forwarding: ?window_days=N
    Security headers: CSP on HTML, nosniff on JSON
    404 body: lists known endpoints
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Canned fixtures (minimal, shape-correct)
# ---------------------------------------------------------------------------
from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    AgentSummary,
    ContextBreakdown,
    RecentSession,
    TokenTotals,
    WorkflowListResult,
    WorkflowSummary,
)

_CANNED_AGENT = AgentSummary(
    agent_id="test-agent",
    display_name="test-agent",
    providers=["claude"],
    dominant_model="claude-sonnet-4-6",
    is_subagent=False,
    session_count=3,
    total_cost_usd=0.42,
    cost_known=True,
    last_activity_at="2026-05-17T10:00:00Z",
    token_totals=TokenTotals(input=1000, cache_creation=200, cache_read=800, output=400),
    context_breakdown=[
        ContextBreakdown(
            context_slug="dadaia-workspace",
            context_name="dadaia-workspace",
            session_count=2,
            cost_usd=0.30,
            cost_fraction=0.714,
        )
    ],
    recent_sessions=[
        RecentSession(
            session_id_prefix="a1b2c3d4",
            date="2026-05-17",
            cost_usd=0.14,
            entrypoint="cli",
            git_branch="main",
            context_slug="dadaia-workspace",
            token_counts=TokenTotals(input=500, cache_creation=0, cache_read=300, output=200),
        )
    ],
    suspect_count=0,
)

_CANNED_AGENTS_RESULT = AgentListResult(
    generated_at="2026-05-17T10:00:00Z",
    window_days=180,
    pricing_age_days=94,
    pricing_model_date="2026-02-12",
    agents=[_CANNED_AGENT],
)

_CANNED_WORKFLOWS_RESULT = WorkflowListResult(
    generated_at="2026-05-17T10:00:00Z",
    source_hint=".claude/skills/, .agents/skills/",
    workflows=[
        WorkflowSummary(
            workflow_id="test-skill",
            display_name="test-skill",
            description="A test skill",
            source=".claude/skills/",
            agent_ids=["test-agent"],
        )
    ],
)

_CANNED_SESSIONS: list[RecentSession] = [
    RecentSession(
        session_id_prefix="s1s2s3s4",
        date="2026-05-17",
        cost_usd=0.07,
        entrypoint="cli",
        git_branch="feat/x",
        context_slug=None,
        token_counts=TokenTotals(input=200, cache_creation=0, cache_read=100, output=50),
    )
]


# ---------------------------------------------------------------------------
# Stub TelemetryService
# ---------------------------------------------------------------------------


class StubTelemetryService:
    """Minimal TelemetryService stub returning canned fixtures.

    Records calls so tests can assert on forwarded query params.
    """

    def __init__(self) -> None:
        self.last_list_agents_kwargs: dict[str, Any] = {}

    def list_agents(
        self,
        window_days: int = 180,
        context_slug: str | None = None,
        limit: int = 50,
    ) -> AgentListResult:
        self.last_list_agents_kwargs = {
            "window_days": window_days,
            "context_slug": context_slug,
            "limit": limit,
        }
        return _CANNED_AGENTS_RESULT

    def list_workflows(self) -> WorkflowListResult:
        return _CANNED_WORKFLOWS_RESULT

    def list_sessions_by_agent(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RecentSession]:
        return _CANNED_SESSIONS


# ---------------------------------------------------------------------------
# Server fixture
# ---------------------------------------------------------------------------


def _build_server(token: str, stub_telemetry: StubTelemetryService):
    """Build a ThreadingHTTPServer on port 0 with the panel handler."""
    from dadaia_workspace.features.panel.handler import make_handler_class

    # Minimal stub views for existing routes.

    # We only need stub callables for the existing routes; the new telemetry
    # routes are added by make_handler_class receiving telemetry view keys.

    def _stub_view(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    def _stub_json(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "application/json", b"{}")

    # PR3-14: /api/workflows is now a bearer-only canonical-source view
    # (no longer uses telemetry).  The integration test injects a stub that
    # returns a minimal conforming payload so existing 200+shape assertions pass.
    def _stub_workflows_list(**kw: Any) -> tuple[int, str, bytes]:
        import datetime as _dt
        import json as _json

        payload = {
            "generated_at": _dt.datetime.now(tz=_dt.UTC).isoformat(),
            "source_hint": ".dadaia/agentic/workflows/",
            "workflows": [],
        }
        return (200, "application/json; charset=utf-8", _json.dumps(payload).encode("utf-8"))

    stub_views = {
        "index": _stub_view,
        "api_servers": _stub_json,
        "api_contexts": _stub_json,
        "api_workflows": _stub_workflows_list,
        "memory": _stub_view,
        "memory_view": _stub_view,
        "static": lambda **kw: (200, "text/plain; charset=utf-8", b"ok"),
        # New telemetry views are injected via telemetry_service arg.
    }

    HandlerClass = make_handler_class(stub_views, token=token, telemetry=stub_telemetry)
    server = ThreadingHTTPServer(("127.0.0.1", 0), HandlerClass)
    return server


@pytest.fixture(scope="module")
def panel_server():
    """Start panel in a background thread; yield (base_url, token, stub_telemetry)."""
    stub_tel = StubTelemetryService()
    # Use a fixed token for tests.
    test_token = "test-token-abc123"

    server = _build_server(test_token, stub_tel)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield base_url, test_token, stub_tel

    server.shutdown()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(url: str, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
    """GET url, return (status, lowercase-keyed headers, body).

    Headers are normalised to lowercase keys so callers can look up with e.g.
    ``headers.get("x-content-type-options")`` regardless of server casing.
    Handles 401 without raising.
    """
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
# T-AM-15 tests
# ---------------------------------------------------------------------------


class TestAgentsEndpoint:
    def test_agents_endpoint_401_without_token(self, panel_server) -> None:
        """GET /api/agents without Authorization header → 401."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents")
        assert status == 401

    def test_agents_endpoint_200_with_token(self, panel_server) -> None:
        """GET /api/agents with Bearer token → 200, valid JSON."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents", token=token)
        assert status == 200
        data = json.loads(body)
        assert "agents" in data
        assert "generated_at" in data

    def test_agents_nosniff_header(self, panel_server) -> None:
        """GET /api/agents response has X-Content-Type-Options: nosniff."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents", token=token)
        assert status == 200
        assert headers.get("x-content-type-options", "").lower() == "nosniff"

    def test_query_string_parsing_window_days(self, panel_server) -> None:
        """GET /api/agents?window_days=30 passes window_days=30 to telemetry service."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents?window_days=30", token=token)
        assert status == 200
        assert stub.last_list_agents_kwargs.get("window_days") == 30


class TestWorkflowsEndpoint:
    def test_workflows_endpoint_401_without_token(self, panel_server) -> None:
        """GET /api/workflows without Authorization header → 401."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/workflows")
        assert status == 401

    def test_workflows_endpoint_200_with_token(self, panel_server) -> None:
        """GET /api/workflows with Bearer token → 200, valid JSON."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/workflows", token=token)
        assert status == 200
        data = json.loads(body)
        assert "workflows" in data
        assert "generated_at" in data


class TestAgentSessionsEndpoint:
    def test_agent_sessions_endpoint(self, panel_server) -> None:
        """GET /api/agents/foo/sessions with token → 200, body has 'sessions' key."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents/foo/sessions", token=token)
        assert status == 200
        data = json.loads(body)
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_agent_sessions_401_without_token(self, panel_server) -> None:
        """GET /api/agents/foo/sessions without token → 401."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents/foo/sessions")
        assert status == 401


class TestPrivacyAndSecurity:
    _FORBIDDEN_FIELDS = {
        "content",
        "text",
        "messages",
        "snapshot",
        "thinking",
        "prompt",
        "response",
    }

    def _check_no_forbidden_fields(self, data: Any, path: str = "") -> None:
        """Recursively assert no forbidden field names appear in the payload."""
        if isinstance(data, dict):
            for key in data:
                assert key not in self._FORBIDDEN_FIELDS, (
                    f"CRITICAL T1: forbidden field '{key}' found in API response at {path}"
                )
                self._check_no_forbidden_fields(data[key], f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._check_no_forbidden_fields(item, f"{path}[{i}]")

    def test_no_forbidden_fields_in_agents_payload(self, panel_server) -> None:
        """T1: /api/agents response must not contain content/prompt/thinking/etc."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents", token=token)
        assert status == 200
        data = json.loads(body)
        self._check_no_forbidden_fields(data, "/api/agents")

    def test_no_forbidden_fields_in_workflows_payload(self, panel_server) -> None:
        """T1: /api/workflows response must not contain forbidden fields."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/workflows", token=token)
        assert status == 200
        data = json.loads(body)
        self._check_no_forbidden_fields(data, "/api/workflows")

    def test_no_forbidden_fields_in_sessions_payload(self, panel_server) -> None:
        """T1: /api/agents/{id}/sessions must not contain forbidden fields."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents/foo/sessions", token=token)
        assert status == 200
        data = json.loads(body)
        self._check_no_forbidden_fields(data, "/api/agents/foo/sessions")

    def test_csp_header_on_html(self, panel_server) -> None:
        """GET / → response has Content-Security-Policy header."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/")
        assert status == 200
        assert "content-security-policy" in {k.lower() for k in headers}

    def test_nosniff_on_json(self, panel_server) -> None:
        """GET /api/agents → response has X-Content-Type-Options: nosniff."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/agents", token=token)
        assert status == 200
        assert headers.get("x-content-type-options", "").lower() == "nosniff"


class Test404:
    def test_404_body_mentions_endpoints(self, panel_server) -> None:
        """GET /api/unknown → 404, body mentions /api/agents and /api/workflows."""
        base, token, stub = panel_server
        status, headers, body = _get(f"{base}/api/unknown")
        assert status == 404
        body_text = body.decode("utf-8", errors="replace")
        assert "/api/agents" in body_text, (
            "404 body must list /api/agents so callers know endpoint exists"
        )
        assert "/api/workflows" in body_text, "404 body must list /api/workflows"
