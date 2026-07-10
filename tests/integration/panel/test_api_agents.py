"""Integration tests for GET /api/agents — end-to-end HTTP (no browser).

Coverage areas (merged per plan-integration.md, 21 -> 3):
  1. response shape + real-agents + telemetry overlay + active/inactive status
  2. ?active_window_days query parameter table (default/custom/min/max/out-of-range)
  3. /api/agents/<id>/prompt table (valid 200, unknown 404, traversal/uppercase 400)

Pattern: real PanelService + real canonical agents + stub telemetry, over the shared
``panel_server_factory``. No mocks — fakes/stubs only. Bearer trio deleted (no-auth
contract pinned in tests/unit/features/panel/test_no_auth_contract.py); one
credential-less GET is folded into fn 1.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from dadaia_workspace.features.agents.reader import FileSystemAgentsProvider
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_agents import (
    render_api_agent_prompt,
    render_api_agents_canonical,
)
from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    AgentSummary,
    ContextBreakdown,
    RecentSession,
    TokenTotals,
)
from dadaia_workspace.infrastructure.markdown_agent_store import MarkdownAgentStore
from tests.integration.panel.conftest import get


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


def _make_agent_summary(agent_id: str, last_activity_at: str) -> AgentSummary:
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

    The two summaries target real agent IDs present in the staged catalog:
      - "software-engineer" -> recent activity (active)
      - "qa-engineer"       -> activity 400 days ago (inactive with default window)
    """

    def list_agents(
        self,
        window_days: int = 180,
        context_slug: str | None = None,
        limit: int = 50,
    ) -> AgentListResult:
        now = datetime.datetime.now(tz=datetime.UTC)
        active_ts = (now - datetime.timedelta(days=1)).isoformat()
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

    is_degraded: bool = False


class _StubRegistry:
    def list_entries(self, include_stale: bool = True) -> list:
        return []


class _StubSpecContextService:
    def list_all(self) -> list:
        return []


@pytest.fixture(scope="module")
def agents_server(panel_server_factory, staged_root: Path) -> str:
    stub_telemetry = StubTelemetryService()
    panel_service = PanelService(
        registry=_StubRegistry(),  # type: ignore[arg-type]
        spec_context=_StubSpecContextService(),  # type: ignore[arg-type]
        workspace_root=staged_root,
        telemetry=stub_telemetry,
        agents_provider=FileSystemAgentsProvider(store_factory=MarkdownAgentStore),
    )
    return panel_server_factory(
        {
            "api_agents": render_api_agents_canonical(panel_service),
            "api_agent_prompt": render_api_agent_prompt(panel_service),
        },
        telemetry=stub_telemetry,
    )


class TestAgentsResponseShapeAndOverlay:
    def test_response_shape_real_agents_overlay_and_status(
        self, agents_server: str, staged_root: Path
    ) -> None:
        """Shape + real agents + telemetry overlay + active/inactive status; no auth needed."""
        status, _, body = get(f"{agents_server}/api/agents")
        assert status == 200
        data = json.loads(body)
        for key in ("generated_at", "status_window_days", "window_days", "agents"):
            assert key in data, f"missing top-level key: {key}"

        agent_ids = {a["agent_id"] for a in data["agents"]}
        assert "software-engineer" in agent_ids
        assert "qa-engineer" in agent_ids

        # Every returned agent has a real on-disk file in the staged catalog.
        agents_dir = staged_root / ".dadaia" / "agentic" / "agents"
        disk_ids = {p.stem for p in agents_dir.glob("*.md")}
        assert agent_ids.issubset(disk_ids), (
            f"Response contains agents not on disk: {agent_ids - disk_ids}"
        )

        by_id = {a["agent_id"]: a for a in data["agents"]}
        se = by_id.get("software-engineer")
        assert se is not None
        assert "telemetry" in se
        assert se["telemetry"]["session_count"] == 5
        assert se["status"] == "active"

        qa = by_id.get("qa-engineer")
        assert qa is not None
        assert qa["status"] == "inactive"


class TestActiveWindowDaysTable:
    @pytest.mark.parametrize(
        ("query", "expected_status", "expected_window"),
        [
            ("", 200, 30),  # default
            ("?active_window_days=365", 200, 365),  # custom / max boundary
            ("?active_window_days=1", 200, None),  # min boundary
            ("?active_window_days=366", 400, None),  # out of range
            ("?active_window_days=0", 400, None),  # out of range
        ],
    )
    def test_active_window_days(
        self,
        agents_server: str,
        query: str,
        expected_status: int,
        expected_window: int | None,
    ) -> None:
        status, _, body = get(f"{agents_server}/api/agents{query}")
        assert status == expected_status
        data = json.loads(body)
        if expected_status == 200:
            if expected_window is not None:
                assert data["status_window_days"] == expected_window
        else:
            assert data.get("error") == "invalid_parameter"

    def test_large_in_range_window_keeps_old_agent_inactive(self, agents_server: str) -> None:
        status, _, body = get(f"{agents_server}/api/agents?active_window_days=365")
        assert status == 200
        data = json.loads(body)
        by_id = {a["agent_id"]: a for a in data["agents"]}
        assert by_id["qa-engineer"]["status"] == "inactive"


class TestAgentPromptTable:
    @pytest.mark.parametrize(
        ("path", "expected_status", "error_code"),
        [
            ("/api/agents/..%2Fetc%2Fpasswd/prompt", None, None),  # 400 or 404
            ("/api/agents/INVALID_UPPER/prompt", 400, "invalid_agent_id"),
            ("/api/agents/software-engineer/prompt", 200, None),
            ("/api/agents/does-not-exist/prompt", 404, None),
        ],
    )
    def test_prompt_endpoint_table(
        self,
        agents_server: str,
        path: str,
        expected_status: int | None,
        error_code: str | None,
    ) -> None:
        status, _, body = get(f"{agents_server}{path}")
        if expected_status is None:
            assert status in (400, 404)
            return
        assert status == expected_status
        data = json.loads(body)
        if error_code:
            assert data.get("error") == error_code
        if expected_status == 200:
            assert "system_prompt" in data
            assert data["agent_id"] == "software-engineer"

    def test_prompt_no_credential_required(self, agents_server: str) -> None:
        status, _, _ = get(f"{agents_server}/api/agents/software-engineer/prompt")
        assert status == 200
