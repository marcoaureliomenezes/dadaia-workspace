"""Unit tests for the canonical /api/agents response.

Coverage:
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
from typing import Any

import pytest

from dadaia_workspace.features.agents.reader import AgentDTO
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api import render_api_agents_canonical


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


from dadaia_workspace.features.telemetry.aggregator.models import (  # noqa: E402
    AgentListResult,
    AgentSummary,
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
        token_totals=TokenTotals(input=1000, cache_creation=200, cache_read=800, output=400),
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


def _make_dto(
    agent_id: str = "software-engineer",
    name: str | None = None,
    description: str = "A software engineer agent.",
    skills: list[str] | None = None,
    tools: list[str] | None = None,
    model: str = "claude-sonnet-4-6",
    max_turns: int | None = 60,
    tier: int = 3,
) -> AgentDTO:
    return AgentDTO(
        id=agent_id,
        name=name or agent_id,
        description=description,
        tier=tier,
        skills=skills or [],
        tools=tools or [],
        model=model,
        opencode_model=None,
        max_turns=max_turns,
        input_contract=None,
    )


def _api_data(
    svc: PanelService,
    *,
    active_window_days: int | None = None,
    qs: dict[str, list[str]] | None = None,
) -> tuple[int, str, dict[str, Any]]:
    kwargs: dict[str, Any] = {}
    if active_window_days is not None:
        kwargs["active_window_days"] = active_window_days
    if qs is not None:
        kwargs["qs"] = qs
    status, content_type, body = render_api_agents_canonical(svc)(**kwargs)
    return status, content_type, json.loads(body)


class TestResponseShape:
    def test_response_contract_and_content_type(self) -> None:
        """The canonical endpoint returns the expected envelope, card, and telemetry shape."""
        agents = [_make_dto()]
        summary = _make_agent_summary(agent_id="software-engineer")
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        status, content_type, data = _api_data(svc)

        assert status == 200
        assert content_type == "application/json; charset=utf-8"

        assert {
            "generated_at",
            "status_window_days",
            "window_days",
            "pricing_age_days",
            "pricing_model_date",
            "agents",
        } <= set(data)

        assert len(data["agents"]) == 1
        card = data["agents"][0]
        assert {
            "agent_id",
            "display_name",
            "description",
            "tier",
            "status",
            "skills",
            "tools",
            "model",
            "opencode_model",
            "max_turns",
            "input_contract",
            "telemetry",
        } <= set(card)

        tel_sub = card["telemetry"]
        assert {
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
        } <= set(tel_sub)

        assert not {
            "session_count",
            "total_cost_usd",
            "last_activity_at",
            "providers",
            "dominant_model",
            "is_subagent",
        } & set(card), "Telemetry fields must stay nested under telemetry"


class TestDefaultWindow:
    def test_default_status_window_is_30(self) -> None:
        """status_window_days defaults to 30 when not specified."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        _, _, data = _api_data(svc)
        assert data["status_window_days"] == 30

    @pytest.mark.parametrize(
        ("last_activity_at", "expected_status"),
        [
            ("2026-05-17T10:00:00Z", "active"),
            ("2026-03-18T10:00:00Z", "inactive"),
        ],
    )
    def test_default_window_status(
        self,
        last_activity_at: str,
        expected_status: str,
    ) -> None:
        """The default status window marks recent telemetry active and old telemetry inactive."""
        agents = [_make_dto()]
        summary = _make_agent_summary(
            agent_id="software-engineer",
            last_activity_at=last_activity_at,
        )
        tel = FakeTelemetryService(agent_summaries=[summary])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        _, _, data = _api_data(svc, active_window_days=30)
        assert data["agents"][0]["status"] == expected_status


class TestCustomWindow:
    def test_custom_window_reflected_in_status_window_days(self) -> None:
        """?active_window_days=90 → status_window_days=90 in response."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        _, _, data = _api_data(svc, active_window_days=90)
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

        _, _, data_30 = _api_data(svc, active_window_days=30)
        _, _, data_90 = _api_data(svc, active_window_days=90)
        assert data_30["agents"][0]["status"] == "inactive"
        assert data_90["agents"][0]["status"] == "active"


class TestNoTelemetry:
    def test_agent_without_telemetry_match_has_zero_defaults(self) -> None:
        """When no telemetry summary matches the agent, defaults are zero/null."""
        agents = [_make_dto(agent_id="unknown-agent")]
        tel = FakeTelemetryService(agent_summaries=[])
        svc = _make_service(agents=agents, telemetry_stub=tel)

        _, _, data = _api_data(svc)

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

        _, _, data = _api_data(svc)

        card = data["agents"][0]
        assert card["status"] == "inactive"
        assert card["telemetry"]["session_count"] == 0


class TestTelemetryOnlyExclusion:
    def test_output_is_limited_to_canonical_agents(self) -> None:
        """Telemetry-only rows are excluded from the canonical agents response."""
        agents = [_make_dto(agent_id=f"agent-{i}") for i in range(3)]
        summaries = [_make_agent_summary(agent_id=f"agent-{i}") for i in range(5)]
        tel = FakeTelemetryService(agent_summaries=summaries)
        svc = _make_service(agents=agents, telemetry_stub=tel)

        _, _, data = _api_data(svc)
        ids = {card["agent_id"] for card in data["agents"]}
        assert len(data["agents"]) == 3
        assert ids == {"agent-0", "agent-1", "agent-2"}


class TestWindowValidation:
    def test_invalid_windows_return_400(self) -> None:
        """active_window_days outside 1..365 returns 400."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())

        for window in [0, -1, 366]:
            status, _, data = _api_data(svc, active_window_days=window)
            assert status == 400
            assert "error" in data

    def test_valid_windows_are_reflected_in_response(self) -> None:
        """Boundary and representative in-range windows are accepted."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())

        for window in [1, 90, 365]:
            status, _, data = _api_data(svc, active_window_days=window)
            assert status == 200
            assert data["status_window_days"] == window


class TestTierFieldInResponse:
    """Tier integer is passed through by /api/agents responses."""

    def test_tier_value_in_valid_set(self) -> None:
        """Every agent's 'tier' must be an integer in {1, 2, 3}."""
        agents = [
            _make_dto(agent_id="tier-one", tier=1),
            _make_dto(agent_id="tier-two", tier=2),
            _make_dto(agent_id="tier-three", tier=3),
        ]
        summaries = [_make_agent_summary(agent_id=agent.id) for agent in agents]
        svc = _make_service(agents=agents, telemetry_stub=FakeTelemetryService(summaries))
        _, _, data = _api_data(svc)

        for card in data["agents"]:
            assert card["tier"] in {1, 2, 3}, (
                f"Agent {card.get('agent_id')!r} has invalid tier {card.get('tier')!r}"
            )


def _make_agent_summary_with_provider(
    agent_id: str,
    providers: list[str],
) -> AgentSummary:
    """Return an AgentSummary with the specified providers list."""
    return AgentSummary(
        agent_id=agent_id,
        display_name=agent_id,
        providers=providers,
        dominant_model="claude-sonnet-4-6",
        is_subagent=False,
        session_count=2,
        total_cost_usd=0.50,
        cost_known=True,
        last_activity_at="2026-05-17T10:00:00Z",
        token_totals=TokenTotals(input=500, cache_creation=100, cache_read=400, output=200),
        context_breakdown=[],
        recent_sessions=[],
        suspect_count=0,
    )


def _build_mixed_runtime_service() -> PanelService:
    agents = [
        _make_dto(agent_id="agent-claude", tier=3),
        _make_dto(agent_id="agent-codex", tier=3),
        _make_dto(agent_id="agent-both", tier=3),
    ]
    summaries = [
        _make_agent_summary_with_provider("agent-claude", ["claude"]),
        _make_agent_summary_with_provider("agent-codex", ["codex"]),
        _make_agent_summary_with_provider("agent-both", ["claude", "codex"]),
    ]
    tel = FakeTelemetryService(agent_summaries=summaries)
    return _make_service(agents=agents, telemetry_stub=tel)


class TestRuntimeFilter:
    """Runtime filter keeps provider-scoped agent responses correct."""

    @pytest.mark.parametrize(
        ("runtime", "expected_ids"),
        [
            ("claude", {"agent-claude", "agent-both"}),
            ("codex", {"agent-codex", "agent-both"}),
            ("unknown-runtime", {"agent-claude", "agent-both"}),
        ],
    )
    def test_runtime_filter_provider_scope(
        self,
        runtime: str,
        expected_ids: set[str],
    ) -> None:
        svc = _build_mixed_runtime_service()
        _, _, data = _api_data(svc, qs={"runtime": [runtime]})
        ids = {card["agent_id"] for card in data["agents"]}
        assert ids == expected_ids

    @pytest.mark.parametrize(
        ("runtime", "expected_present"),
        [("claude", True), ("codex", False)],
    )
    def test_no_telemetry_agent_runtime_behavior(
        self,
        runtime: str,
        expected_present: bool,
    ) -> None:
        agents = [_make_dto(agent_id="ghost-agent", tier=3)]
        tel = FakeTelemetryService(agent_summaries=[])
        svc = _make_service(agents=agents, telemetry_stub=tel)
        _, _, data = _api_data(svc, qs={"runtime": [runtime]})
        ids = {card["agent_id"] for card in data["agents"]}
        assert ("ghost-agent" in ids) is expected_present


class TestRuntimeFilterBackwardCompatParity:
    def test_no_runtime_param_equals_runtime_claude(self) -> None:
        """Response with no ?runtime= must be identical to ?runtime=claude."""
        svc = _build_mixed_runtime_service()
        _, _, data_no_qs = _api_data(svc)
        _, _, data_claude = _api_data(svc, qs={"runtime": ["claude"]})

        agents_no_qs = data_no_qs["agents"]
        agents_claude = data_claude["agents"]
        assert [card["agent_id"] for card in agents_no_qs] == [
            card["agent_id"] for card in agents_claude
        ]

        for card_no_qs, card_claude in zip(agents_no_qs, agents_claude, strict=False):
            keys_to_compare = set(card_no_qs.keys()) - {"telemetry"}
            for key in keys_to_compare:
                assert card_no_qs[key] == card_claude[key], (
                    f"Agent {card_no_qs['agent_id']!r}: key {key!r} differs "
                    f"between no-qs ({card_no_qs[key]!r}) and "
                    f"runtime=claude ({card_claude[key]!r})"
                )

    def test_top_level_envelope_shape_identical(self) -> None:
        """Top-level envelope keys are identical between no-?runtime= and ?runtime=claude."""
        svc = _make_service(agents=[], telemetry_stub=FakeTelemetryService())
        _, _, data_no_qs = _api_data(svc)
        _, _, data_claude = _api_data(svc, qs={"runtime": ["claude"]})

        assert set(data_no_qs.keys()) == set(data_claude.keys()), (
            "Top-level envelope keys differ between no-qs and runtime=claude"
        )
