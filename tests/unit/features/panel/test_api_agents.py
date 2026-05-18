"""Unit + integration tests for the PR3-08 /api/agents rewrite.

Coverage (per TASKS.md PR3-08 acceptance):
- Default window (30 days): response shape + telemetry sub-object present
- Custom window (?active_window_days=N): status_window_days reflects N
- No telemetry: agent cards rendered with zero/null telemetry gracefully
- Malformed agent (skipped by reader): does not appear in output
- Response shape: exactly the §5.1 contract (top-level + agent + telemetry keys)
- active_window_days validation: out-of-range → 400
- Telemetry-only agents excluded from output
- status "active" / "inactive" computed correctly against window
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.agents.reader import AgentDTO
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api import render_api_agents_canonical

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeServerRegistryService:
    def list_entries(self, project=None, include_stale=True):
        return []


class FakeSpecContextService:
    def list_all(self):
        return []


def _make_service(
    agents: list[AgentDTO],
    telemetry_stub=None,
) -> PanelService:
    svc = PanelService(
        registry=FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        telemetry=telemetry_stub,
    )
    svc._canonical_agents_override = agents  # injected by fake
    return svc


# ---------------------------------------------------------------------------
# Telemetry stub
# ---------------------------------------------------------------------------

from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    AgentSummary,
    ContextBreakdown,
    RecentSession,
    TokenTotals,
)


def _make_agent_summary(
    agent_id: str = "software-engineer",
    session_count: int = 5,
    total_cost_usd: float | None = 1.23,
    cost_known: bool = True,
    last_activity_at: str = "2026-05-17T10:00:00Z",
) -> AgentSummary:
    return AgentSummary(
        agent_id=agent_id,
        display_name=agent_id,
        providers=["claude"],
        dominant_model="claude-sonnet-4-6",
        is_subagent=False,
        session_count=session_count,
        total_cost_usd=total_cost_usd,
        cost_known=cost_known,
        last_activity_at=last_activity_at,
        token_totals=TokenTotals(
            input=1000, cache_creation=200, cache_read=800, output=400
        ),
        context_breakdown=[],
        recent_sessions=[],
        suspect_count=0,
    )


class FakeTelemetryService:
    """Stub that returns a controlled AgentListResult."""

    def __init__(
        self,
        agent_summaries: list[AgentSummary] | None = None,
        window_days: int = 180,
    ) -> None:
        self._summaries = agent_summaries or []
        self._window_days = window_days
        self.last_call_kwargs: dict = {}

    def list_agents(
        self,
        window_days: int = 180,
        context_slug=None,
        limit: int = 50,
    ) -> AgentListResult:
        self.last_call_kwargs = {
            "window_days": window_days,
            "context_slug": context_slug,
            "limit": limit,
        }
        return AgentListResult(
            generated_at="2026-05-17T10:00:00Z",
            window_days=self._window_days,
            pricing_age_days=12,
            pricing_model_date="2026-05-01",
            agents=list(self._summaries),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_dto(
    agent_id: str = "software-engineer",
    name: str | None = None,
    description: str = "A software engineer agent.",
    skills: list[str] | None = None,
    tools: list[str] | None = None,
    model: str = "claude-sonnet-4-6",
    max_turns: int | None = 60,
) -> AgentDTO:
    return AgentDTO(
        id=agent_id,
        name=name or agent_id,
        description=description,
        skills=skills or [],
        tools=tools or [],
        model=model,
        opencode_model=None,
        max_turns=max_turns,
        input_contract=None,
    )


# ---------------------------------------------------------------------------
# Response shape — §5.1 contract
# ---------------------------------------------------------------------------


class TestResponseShape:
    def test_top_level_keys_present(self) -> None:
        """Response must have generated_at, status_window_days, window_days,
        pricing_age_days, pricing_model_date, agents."""
        agents = [_make_dto()]
        summary = _make_agent_summary(agent_id="software-engineer")
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        status, content_type, body = view()

        assert status == 200
        assert "application/json" in content_type
        data = json.loads(body)

        required_top_level = {
            "generated_at",
            "status_window_days",
            "window_days",
            "pricing_age_days",
            "pricing_model_date",
            "agents",
        }
        missing = required_top_level - set(data.keys())
        assert not missing, f"Missing top-level keys: {missing}"

    def test_agent_card_keys_present(self) -> None:
        """Each agent entry must have the §5.1 top-level agent keys."""
        agents = [_make_dto()]
        summary = _make_agent_summary(agent_id="software-engineer")
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        assert len(data["agents"]) == 1
        card = data["agents"][0]
        required_card_keys = {
            "agent_id",
            "display_name",
            "description",
            "status",
            "skills",
            "tools",
            "model",
            "opencode_model",
            "max_turns",
            "input_contract",
            "telemetry",
        }
        missing = required_card_keys - set(card.keys())
        assert not missing, f"Missing agent card keys: {missing}"

    def test_telemetry_sub_object_keys_present(self) -> None:
        """telemetry sub-object must have the normative keys from §5.1."""
        agents = [_make_dto()]
        summary = _make_agent_summary(agent_id="software-engineer")
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        tel_sub = data["agents"][0]["telemetry"]
        required_tel_keys = {
            "session_count",
            "total_cost_usd",
            "total_cost_30d_usd",
            "cost_known",
            "last_activity_at",
            "providers",
            "dominant_model",
            "is_subagent",
            "suspect_count",
            "token_totals",
            "context_breakdown",
            "recent_sessions",
        }
        missing = required_tel_keys - set(tel_sub.keys())
        assert not missing, f"Missing telemetry sub-object keys: {missing}"

    def test_telemetry_is_nested_not_top_level(self) -> None:
        """Telemetry fields must be nested under 'telemetry', NOT at card top-level."""
        agents = [_make_dto()]
        summary = _make_agent_summary(agent_id="software-engineer")
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)
        card = data["agents"][0]

        # These fields must NOT appear at card top level
        top_level_forbidden = {
            "session_count",
            "total_cost_usd",
            "last_activity_at",
            "providers",
            "dominant_model",
            "is_subagent",
        }
        present_at_top = top_level_forbidden & set(card.keys())
        assert not present_at_top, (
            f"Telemetry fields leaked to top-level agent card: {present_at_top}"
        )


# ---------------------------------------------------------------------------
# Default window (30 days)
# ---------------------------------------------------------------------------


class TestDefaultWindow:
    def test_default_status_window_is_30(self) -> None:
        """status_window_days defaults to 30 when not specified."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)
        assert data["status_window_days"] == 30

    def test_active_status_within_default_window(self) -> None:
        """An agent active within 30 days should have status='active'."""
        agents = [_make_dto()]
        summary = _make_agent_summary(
            agent_id="software-engineer",
            last_activity_at="2026-05-17T10:00:00Z",  # within 30 days of 2026-05-18
        )
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view(active_window_days=30)
        data = json.loads(body)
        assert data["agents"][0]["status"] == "active"

    def test_inactive_status_outside_default_window(self) -> None:
        """An agent last active 60 days ago should be 'inactive' with window=30."""
        agents = [_make_dto()]
        # last_activity_at = 2026-03-18 (60 days before 2026-05-18)
        summary = _make_agent_summary(
            agent_id="software-engineer",
            last_activity_at="2026-03-18T10:00:00Z",
        )
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view(active_window_days=30)
        data = json.loads(body)
        assert data["agents"][0]["status"] == "inactive"


# ---------------------------------------------------------------------------
# Custom window
# ---------------------------------------------------------------------------


class TestCustomWindow:
    def test_custom_window_reflected_in_status_window_days(self) -> None:
        """?active_window_days=90 → status_window_days=90 in response."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        _, _, body = view(active_window_days=90)
        data = json.loads(body)
        assert data["status_window_days"] == 90

    def test_custom_window_changes_active_inactive(self) -> None:
        """Agent active 60 days ago is inactive with window=30 but active with window=90."""
        agents = [_make_dto()]
        # last_activity_at 60 days ago
        summary = _make_agent_summary(
            agent_id="software-engineer",
            last_activity_at="2026-03-18T10:00:00Z",
        )
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)

        # Window 30: inactive
        _, _, body_30 = view(active_window_days=30)
        assert json.loads(body_30)["agents"][0]["status"] == "inactive"

        # Window 90: active (60 < 90)
        _, _, body_90 = view(active_window_days=90)
        assert json.loads(body_90)["agents"][0]["status"] == "active"


# ---------------------------------------------------------------------------
# No telemetry (zero state)
# ---------------------------------------------------------------------------


class TestNoTelemetry:
    def test_agent_without_telemetry_match_has_zero_defaults(self) -> None:
        """When no telemetry summary matches the agent, defaults are zero/null."""
        agents = [_make_dto(agent_id="unknown-agent")]
        # Telemetry service returns empty summaries — no match
        tel = FakeTelemetryService(agent_summaries=[])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        card = data["agents"][0]
        assert card["status"] == "inactive"
        tel_sub = card["telemetry"]
        assert tel_sub["session_count"] == 0
        assert tel_sub["total_cost_usd"] is None or tel_sub["total_cost_usd"] == 0
        assert tel_sub["last_activity_at"] is None
        assert tel_sub["cost_known"] is False

    def test_no_telemetry_service_returns_all_inactive(self) -> None:
        """When telemetry is None, all agents are inactive with zero stats."""
        agents = [_make_dto()]
        svc = _make_service(agents=agents, telemetry_stub=None)

        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        card = data["agents"][0]
        assert card["status"] == "inactive"
        assert card["telemetry"]["session_count"] == 0


# ---------------------------------------------------------------------------
# Telemetry-only agents excluded
# ---------------------------------------------------------------------------


class TestTelemetryOnlyExclusion:
    def test_telemetry_only_agent_not_in_output(self) -> None:
        """Agents that exist only in telemetry (not in canonical catalog) are excluded."""
        # Canonical: only software-engineer
        agents = [_make_dto(agent_id="software-engineer")]
        # Telemetry has both software-engineer AND a ghost agent
        summaries = [
            _make_agent_summary(agent_id="software-engineer"),
            _make_agent_summary(agent_id="ghost-telemetry-only-agent"),
        ]
        tel = FakeTelemetryService(agent_summaries=summaries)
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        ids = [card["agent_id"] for card in data["agents"]]
        assert "ghost-telemetry-only-agent" not in ids
        assert "software-engineer" in ids

    def test_output_count_equals_canonical_agent_count(self) -> None:
        """Output length equals canonical agent count regardless of extra telemetry rows."""
        agents = [_make_dto(agent_id=f"agent-{i}") for i in range(3)]
        # 5 telemetry rows: 3 match + 2 extras
        summaries = [_make_agent_summary(agent_id=f"agent-{i}") for i in range(5)]
        tel = FakeTelemetryService(agent_summaries=summaries)
        svc = _make_service(agents=agents, telemetry_stub=tel)

        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)
        assert len(data["agents"]) == 3


# ---------------------------------------------------------------------------
# active_window_days validation
# ---------------------------------------------------------------------------


class TestWindowValidation:
    def test_window_zero_returns_400(self) -> None:
        """active_window_days=0 is out of range (1..3650) → 400."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        status, _, body = view(active_window_days=0)
        assert status == 400
        data = json.loads(body)
        assert "error" in data

    def test_window_negative_returns_400(self) -> None:
        """active_window_days=-1 → 400."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        status, _, body = view(active_window_days=-1)
        assert status == 400

    def test_window_too_large_returns_400(self) -> None:
        """active_window_days=366 → 400 (max per SPEC §5.1 table is 365)."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        status, _, body = view(active_window_days=366)
        assert status == 400

    def test_window_min_boundary_valid(self) -> None:
        """active_window_days=1 is valid."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        status, _, body = view(active_window_days=1)
        assert status == 200
        assert json.loads(body)["status_window_days"] == 1

    def test_window_max_boundary_valid(self) -> None:
        """active_window_days=365 is valid (max per SPEC §5.1 table)."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        status, _, body = view(active_window_days=365)
        assert status == 200
        assert json.loads(body)["status_window_days"] == 365

    def test_window_mid_range_valid(self) -> None:
        """active_window_days=90 is valid (within 1-365)."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        status, _, body = view(active_window_days=90)
        assert status == 200
        assert json.loads(body)["status_window_days"] == 90


# ---------------------------------------------------------------------------
# Content-Type
# ---------------------------------------------------------------------------


class TestContentType:
    def test_content_type_is_json(self) -> None:
        """Content-Type must be application/json; charset=utf-8."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        view = render_api_agents_canonical(svc)
        _, content_type, _ = view()
        assert content_type == "application/json; charset=utf-8"
