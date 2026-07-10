"""Integration tests for the panel's telemetry API endpoints (T-AM-15).

Spins up ThreadingHTTPServer on port 0 (random free port) with a stub
TelemetryService that returns canned fixtures. Uses urllib.request only
(stdlib; no requests).

Merged per plan-integration.md (14 -> 2 kept CRITICAL): (1) endpoints-200 (no-auth
contract) + window_days forwarding + 404-body-lists-endpoints; (2) CSP-on-HTML +
nosniff-on-JSON. The T1 recursive forbidden-field privacy scan walking all three
payloads is kept as its own CRITICAL fn (no content/prompt/thinking leak).
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any

import pytest

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


def _build_server(token: str, stub_telemetry: StubTelemetryService):
    """Build a ThreadingHTTPServer on port 0 with the panel handler."""
    from dadaia_workspace.features.panel.handler import make_handler_class

    def _stub_view(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "text/html; charset=utf-8", b"<html>ok</html>")

    def _stub_json(**kw: Any) -> tuple[int, str, bytes]:
        return (200, "application/json", b"{}")

    def _stub_workflows_list(**kw: Any) -> tuple[int, str, bytes]:
        import datetime as _dt

        payload = {
            "generated_at": _dt.datetime.now(tz=_dt.UTC).isoformat(),
            "source_hint": ".dadaia/agentic/workflows/",
            "workflows": [],
        }
        return (200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

    stub_views = {
        "index": _stub_view,
        "api_panel_status": _stub_json,
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
    test_token = "test-token-abc123"

    server = _build_server(test_token, stub_tel)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()

    yield base_url, test_token, stub_tel

    server.shutdown()


def _get(url: str, token: str | None = None) -> tuple[int, dict[str, str], bytes]:
    """GET url, return (status, lowercase-keyed headers, body)."""
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


def test_endpoints_no_auth_window_days_forwarding_and_404_body(panel_server) -> None:
    """No-auth contract (credential-less 200) + window_days forwarding + 404 body lists endpoints."""
    base, token, stub = panel_server

    # No-auth: every telemetry endpoint serves credential-less.
    status, _, body = _get(f"{base}/api/agents")
    assert status == 200
    data = json.loads(body)
    assert "agents" in data
    assert "generated_at" in data

    status, _, _ = _get(f"{base}/api/workflows")
    assert status == 200

    status, _, body = _get(f"{base}/api/workflows", token=token)
    assert status == 200
    data = json.loads(body)
    assert "workflows" in data
    assert "generated_at" in data

    status, _, body = _get(f"{base}/api/agents/foo/sessions")
    assert status == 200
    data = json.loads(body)
    assert "sessions" in data
    assert isinstance(data["sessions"], list)

    # ?window_days=N forwarded to the telemetry service.
    status, _, _ = _get(f"{base}/api/agents?window_days=30", token=token)
    assert status == 200
    assert stub.last_list_agents_kwargs.get("window_days") == 30

    # 404 body lists known endpoints.
    status, _, body = _get(f"{base}/api/unknown")
    assert status == 404
    body_text = body.decode("utf-8", errors="replace")
    assert "/api/agents" in body_text
    assert "/api/workflows" in body_text


def test_security_headers_csp_on_html_and_nosniff_on_json(panel_server) -> None:
    base, token, stub = panel_server

    status, headers, _ = _get(f"{base}/")
    assert status == 200
    assert "content-security-policy" in {k.lower() for k in headers}

    status, headers, _ = _get(f"{base}/api/agents", token=token)
    assert status == 200
    assert headers.get("x-content-type-options", "").lower() == "nosniff"


class TestPrivacyT1ForbiddenFieldScan:
    """CRITICAL: recursive forbidden-field scan over all three telemetry payloads."""

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
        if isinstance(data, dict):
            for key in data:
                assert key not in self._FORBIDDEN_FIELDS, (
                    f"CRITICAL T1: forbidden field '{key}' found in API response at {path}"
                )
                self._check_no_forbidden_fields(data[key], f"{path}.{key}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._check_no_forbidden_fields(item, f"{path}[{i}]")

    def test_no_forbidden_fields_in_all_three_payloads(self, panel_server) -> None:
        base, token, stub = panel_server

        status, _, body = _get(f"{base}/api/agents", token=token)
        assert status == 200
        self._check_no_forbidden_fields(json.loads(body), "/api/agents")

        status, _, body = _get(f"{base}/api/workflows", token=token)
        assert status == 200
        self._check_no_forbidden_fields(json.loads(body), "/api/workflows")

        status, _, body = _get(f"{base}/api/agents/foo/sessions", token=token)
        assert status == 200
        self._check_no_forbidden_fields(json.loads(body), "/api/agents/foo/sessions")
