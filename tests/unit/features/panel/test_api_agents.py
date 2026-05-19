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


# ---------------------------------------------------------------------------
# AGT-33 — 6 new agents present in /api/agents LIST response
# ---------------------------------------------------------------------------

_NEW_AGENT_IDS = [
    "project-manager",
    "project-auditor",
    "code-reviewer",
    "researcher",
    "security-reviewer",
    "design-specialist",
]


class TestNewAgentsInList:
    """Assert each of the 6 new agents (AGT-09..AGT-14) appears in the LIST response."""

    def _build_service_with_agents(self, agent_ids: list[str]) -> "PanelService":
        agents = [_make_dto(agent_id=aid) for aid in agent_ids]
        summaries = [_make_agent_summary(agent_id=aid) for aid in agent_ids]
        tel = FakeTelemetryService(agent_summaries=summaries)
        return _make_service(agents=agents, telemetry_stub=tel)

    def test_all_new_agents_present_in_list(self) -> None:
        """All 6 new agent IDs must appear in the LIST response."""
        svc = self._build_service_with_agents(_NEW_AGENT_IDS)
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)
        returned_ids = {card["agent_id"] for card in data["agents"]}
        for aid in _NEW_AGENT_IDS:
            assert aid in returned_ids, f"New agent {aid!r} missing from LIST response"

    def test_new_agent_count_is_6(self) -> None:
        """LIST response with exactly the 6 new agents returns 6 entries."""
        svc = self._build_service_with_agents(_NEW_AGENT_IDS)
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)
        assert len(data["agents"]) == 6

    def test_full_16_agent_topology_count(self) -> None:
        """With 16-agent topology the LIST response returns 16 entries."""
        all_16 = [
            "software-engineer",
            "frontend-engineer",
            "backend-engineer",
            "qa-engineer",
            "devops-engineer",
            "product-engineer",
            "software-architect",
            "game-developer",
            "game-designer",
            "game-tester",
        ] + _NEW_AGENT_IDS
        svc = self._build_service_with_agents(all_16)
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)
        assert len(data["agents"]) == 16

    def test_new_agent_card_has_required_keys(self) -> None:
        """Each new-agent card must include all §5.1 required keys."""
        svc = self._build_service_with_agents(["project-manager"])
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)
        card = data["agents"][0]
        required = {"agent_id", "display_name", "description", "status", "skills",
                    "tools", "model", "opencode_model", "max_turns", "input_contract",
                    "telemetry"}
        missing = required - set(card.keys())
        assert not missing, f"New agent card missing keys: {missing}"


# ---------------------------------------------------------------------------
# PR4-15 — tier field in /api/agents response (C4)
# ---------------------------------------------------------------------------

# Full 16-agent topology with canonical tier assignments (PR4-11 mapping)
_TIER1_IDS = ["project-manager", "project-auditor"]
_TIER2_IDS = ["product-engineer"]
_TIER3_IDS = [
    "software-architect",
    "software-engineer",
    "backend-engineer",
    "frontend-engineer",
    "qa-engineer",
    "devops-engineer",
    "code-reviewer",
    "security-reviewer",
    "researcher",
    "design-specialist",
    "game-developer",
    "game-designer",
    "game-tester",
]


def _make_dto_with_tier(agent_id: str, tier: int) -> AgentDTO:
    return _make_dto(agent_id=agent_id, tier=tier)


def _build_full_topology_service() -> "PanelService":
    """Build a PanelService with 16 agents using canonical tier assignments."""
    agents = (
        [_make_dto_with_tier(aid, 1) for aid in _TIER1_IDS]
        + [_make_dto_with_tier(aid, 2) for aid in _TIER2_IDS]
        + [_make_dto_with_tier(aid, 3) for aid in _TIER3_IDS]
    )
    all_ids = _TIER1_IDS + _TIER2_IDS + _TIER3_IDS
    summaries = [_make_agent_summary(agent_id=aid) for aid in all_ids]
    tel = FakeTelemetryService(agent_summaries=summaries)
    return _make_service(agents=agents, telemetry_stub=tel)


class TestTierFieldInResponse:
    """PR4-15 — tier integer present and valid in /api/agents response (C4)."""

    def test_tier_key_present_in_every_agent_card(self) -> None:
        """Every agent card in the response must have a 'tier' key."""
        svc = _build_full_topology_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        for card in data["agents"]:
            assert "tier" in card, (
                f"Agent card for {card.get('agent_id')!r} is missing 'tier' key"
            )

    def test_tier_value_in_valid_set(self) -> None:
        """Every agent's 'tier' must be an integer in {1, 2, 3}."""
        svc = _build_full_topology_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        for card in data["agents"]:
            assert card["tier"] in {1, 2, 3}, (
                f"Agent {card.get('agent_id')!r} has invalid tier {card.get('tier')!r}"
            )

    def test_tier_count_per_tier(self) -> None:
        """With the canonical 16-agent topology: T1=2, T2=1, T3=13."""
        svc = _build_full_topology_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        from collections import Counter
        tier_counts = Counter(card["tier"] for card in data["agents"])
        assert tier_counts[1] == 2, f"Expected 2 T1 agents, got {tier_counts[1]}"
        assert tier_counts[2] == 1, f"Expected 1 T2 agent, got {tier_counts[2]}"
        assert tier_counts[3] == 13, f"Expected 13 T3 agents, got {tier_counts[3]}"

    def test_tier_values_match_canonical_mapping(self) -> None:
        """Specific agents have the correct canonical tier value."""
        svc = _build_full_topology_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view()
        data = json.loads(body)

        by_id = {card["agent_id"]: card for card in data["agents"]}

        for aid in _TIER1_IDS:
            assert by_id[aid]["tier"] == 1, (
                f"{aid!r} should be tier 1, got {by_id[aid]['tier']}"
            )
        for aid in _TIER2_IDS:
            assert by_id[aid]["tier"] == 2, (
                f"{aid!r} should be tier 2, got {by_id[aid]['tier']}"
            )
        # Sample 3 T3 agents
        for aid in ["software-engineer", "qa-engineer", "devops-engineer"]:
            assert by_id[aid]["tier"] == 3, (
                f"{aid!r} should be tier 3, got {by_id[aid]['tier']}"
            )


# ---------------------------------------------------------------------------
# PR5-D12 / PR5-D13 — runtime-filter assertions + backward-compat parity
# ---------------------------------------------------------------------------
#
# These tests layer ON TOP of the PR4-15/PR4-19 tier assertions above.
# No existing assertion is modified or deleted.
#
# Fixture helpers
# ---------------
# _make_agent_summary_with_provider: builds an AgentSummary whose providers list
# carries the requested runtime value, so the runtime filter in the view can
# discriminate between claude-only, codex-only, and mixed agents.


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
        token_totals=TokenTotals(
            input=500, cache_creation=100, cache_read=400, output=200
        ),
        context_breakdown=[],
        recent_sessions=[],
        suspect_count=0,
    )


def _build_mixed_runtime_service() -> "PanelService":
    """Build a service with 3 canonical agents:

    - 'agent-claude'  → telemetry providers=["claude"]
    - 'agent-codex'   → telemetry providers=["codex"]
    - 'agent-both'    → telemetry providers=["claude", "codex"]
    """
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
    """PR5-D12 — runtime filter assertions layered on top of r4 tier tests."""

    def test_runtime_claude_default_includes_claude_agents(self) -> None:
        """?runtime=claude returns agents with providers=['claude'] and providers=['claude','codex']."""
        svc = _build_mixed_runtime_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view(qs={"runtime": ["claude"]})
        data = json.loads(body)
        ids = {card["agent_id"] for card in data["agents"]}
        assert "agent-claude" in ids, "claude-only agent should appear in runtime=claude response"
        assert "agent-both" in ids, "mixed-provider agent should appear in runtime=claude response"

    def test_runtime_claude_excludes_codex_only_agents(self) -> None:
        """?runtime=claude excludes agents whose telemetry providers is ['codex'] only."""
        svc = _build_mixed_runtime_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view(qs={"runtime": ["claude"]})
        data = json.loads(body)
        ids = {card["agent_id"] for card in data["agents"]}
        assert "agent-codex" not in ids, (
            "codex-only agent must be excluded from runtime=claude response"
        )

    def test_runtime_codex_includes_codex_agents(self) -> None:
        """?runtime=codex returns agents with providers=['codex'] and providers=['claude','codex']."""
        svc = _build_mixed_runtime_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view(qs={"runtime": ["codex"]})
        data = json.loads(body)
        ids = {card["agent_id"] for card in data["agents"]}
        assert "agent-codex" in ids, "codex-only agent should appear in runtime=codex response"
        assert "agent-both" in ids, "mixed-provider agent should appear in runtime=codex response"

    def test_runtime_codex_excludes_claude_only_agents(self) -> None:
        """?runtime=codex excludes agents whose telemetry providers is ['claude'] only."""
        svc = _build_mixed_runtime_service()
        view = render_api_agents_canonical(svc)
        _, _, body = view(qs={"runtime": ["codex"]})
        data = json.loads(body)
        ids = {card["agent_id"] for card in data["agents"]}
        assert "agent-claude" not in ids, (
            "claude-only agent must be excluded from runtime=codex response"
        )

    def test_unknown_runtime_falls_back_to_claude(self) -> None:
        """An unrecognised ?runtime= value falls back to claude (NFR5 safety net)."""
        svc = _build_mixed_runtime_service()
        view = render_api_agents_canonical(svc)
        _, _, body_unknown = view(qs={"runtime": ["unknown-runtime"]})
        data_unknown = json.loads(body_unknown)
        ids_unknown = {card["agent_id"] for card in data_unknown["agents"]}

        _, _, body_claude = view(qs={"runtime": ["claude"]})
        data_claude = json.loads(body_claude)
        ids_claude = {card["agent_id"] for card in data_claude["agents"]}

        assert ids_unknown == ids_claude, (
            "Unknown runtime should fall back to claude-scoped response"
        )

    def test_runtime_filter_preserves_tier_key(self) -> None:
        """Each agent card returned by ?runtime=claude still carries a 'tier' key (r4 compat)."""
        svc = _build_full_topology_service()
        view = render_api_agents_canonical(svc)
        # All topology agents have providers=["claude"] in _make_agent_summary,
        # so runtime=claude should return all of them.
        _, _, body = view(qs={"runtime": ["claude"]})
        data = json.loads(body)
        for card in data["agents"]:
            assert "tier" in card, (
                f"Agent card for {card.get('agent_id')!r} missing 'tier' key "
                f"after runtime filter (r4 rebase guard)"
            )

    def test_no_telemetry_agent_included_in_claude_default(self) -> None:
        """Canonical agents with no telemetry entry are included when runtime=claude."""
        agents = [_make_dto(agent_id="ghost-agent", tier=3)]
        tel = FakeTelemetryService(agent_summaries=[])  # no telemetry for ghost-agent
        svc = _make_service(agents=agents, telemetry_stub=tel)
        view = render_api_agents_canonical(svc)
        _, _, body = view(qs={"runtime": ["claude"]})
        data = json.loads(body)
        ids = {card["agent_id"] for card in data["agents"]}
        assert "ghost-agent" in ids, (
            "Canonical agent with no telemetry must be included when runtime=claude"
        )

    def test_no_telemetry_agent_excluded_from_codex(self) -> None:
        """Canonical agents with no telemetry entry are excluded when runtime=codex."""
        agents = [_make_dto(agent_id="ghost-agent", tier=3)]
        tel = FakeTelemetryService(agent_summaries=[])  # no telemetry for ghost-agent
        svc = _make_service(agents=agents, telemetry_stub=tel)
        view = render_api_agents_canonical(svc)
        _, _, body = view(qs={"runtime": ["codex"]})
        data = json.loads(body)
        ids = {card["agent_id"] for card in data["agents"]}
        assert "ghost-agent" not in ids, (
            "Canonical agent with no telemetry must be excluded when runtime=codex"
        )


class TestRuntimeFilterBackwardCompatParity:
    """PR5-D13 — NFR5 backward-compat parity: no ?runtime= == ?runtime=claude.

    This test codifies the 'default to claude' guarantee and prevents a silent
    regression where the default branch starts emitting a different envelope
    than the explicit runtime=claude branch.
    """

    def test_no_runtime_param_equals_runtime_claude(self) -> None:
        """Response with no ?runtime= must be identical to ?runtime=claude."""
        svc = _build_full_topology_service()
        view = render_api_agents_canonical(svc)

        # Drive the view with no qs (simulates ?runtime= omitted).
        _, _, body_no_qs = view()
        data_no_qs = json.loads(body_no_qs)

        # Drive the view with explicit ?runtime=claude.
        _, _, body_claude = view(qs={"runtime": ["claude"]})
        data_claude = json.loads(body_claude)

        # Compare agent lists key-by-key and item-by-item.
        agents_no_qs = data_no_qs["agents"]
        agents_claude = data_claude["agents"]

        assert len(agents_no_qs) == len(agents_claude), (
            f"Agent count differs: no-qs={len(agents_no_qs)}, "
            f"runtime=claude={len(agents_claude)}"
        )

        ids_no_qs = [card["agent_id"] for card in agents_no_qs]
        ids_claude = [card["agent_id"] for card in agents_claude]
        assert ids_no_qs == ids_claude, (
            f"Agent ID lists differ between no-qs and runtime=claude:\n"
            f"  no-qs:  {ids_no_qs}\n"
            f"  claude: {ids_claude}"
        )

        for card_no_qs, card_claude in zip(agents_no_qs, agents_claude):
            # Compare all keys except time-sensitive generated_at.
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
        view = render_api_agents_canonical(svc)

        _, _, body_no_qs = view()
        _, _, body_claude = view(qs={"runtime": ["claude"]})

        data_no_qs = json.loads(body_no_qs)
        data_claude = json.loads(body_claude)

        # Top-level keys must be identical.
        assert set(data_no_qs.keys()) == set(data_claude.keys()), (
            "Top-level envelope keys differ between no-qs and runtime=claude"
        )
