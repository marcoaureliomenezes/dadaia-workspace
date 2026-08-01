"""Unit tests for the canonical /api/agents response — real decisions only.

Response shape/happy-path bytes are pinned by ``test_api_golden.py``; this file
keeps only the tests that flip a real decision:

1. Status-window math (active/inactive incl. custom window + 400/valid range).
2. Runtime filter (provider-scope) + no-qs≡runtime=claude parity.
3. No-telemetry / telemetry-None defaults + telemetry-only exclusion.
4. Plugin-stub exclusion + phases derivation (known/unknown agent).
5. Workflow membership + provider-failure→empty + model_inherited flag.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dadaia_workspace.core.models.agent import AgentDTO
from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views.api_agents import render_api_agents_canonical
from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    AgentSummary,
    TokenTotals,
)

pytestmark = pytest.mark.unit


def _days_ago_iso(days: int) -> str:
    """ISO-8601 UTC timestamp ``days`` in the past, relative to now (never a fixed-date time bomb)."""
    return (datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=days)).isoformat()


class FakeServerRegistryService:
    def list_entries(self, project: Any = None, include_stale: bool = True) -> list[Any]:
        return []


class FakeSpecContextService:
    def list_all(self) -> list[Any]:
        return []


def _make_service(
    agents: list[AgentDTO], telemetry_stub: Any = None, workflows_service: Any = None
) -> PanelService:
    svc = PanelService(
        registry=FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        telemetry=telemetry_stub,
    )
    svc._canonical_agents_override = agents  # type: ignore[attr-defined]
    return svc


def _make_agent_summary(
    agent_id: str = "software-engineer",
    providers: list[str] | None = None,
    last_activity_at: str = "2026-05-17T10:00:00Z",
) -> AgentSummary:
    return AgentSummary(
        agent_id=agent_id,
        display_name=agent_id,
        providers=providers or ["claude"],
        dominant_model="claude-sonnet-4-6",
        is_subagent=False,
        session_count=5,
        total_cost_usd=1.23,
        cost_known=True,
        last_activity_at=last_activity_at,
        token_totals=TokenTotals(input=1000, cache_creation=200, cache_read=800, output=400),
        context_breakdown=[],
        recent_sessions=[],
        suspect_count=0,
    )


class FakeTelemetryService:
    def __init__(self, agent_summaries: list[AgentSummary] | None = None) -> None:
        self._summaries = agent_summaries or []

    def list_agents(
        self, window_days: int = 180, context_slug: Any = None, limit: int = 50
    ) -> AgentListResult:
        return AgentListResult(
            generated_at="2026-05-17T10:00:00Z",
            window_days=180,
            pricing_age_days=12,
            pricing_model_date="2026-05-01",
            agents=list(self._summaries),
        )


def _make_dto(
    agent_id: str = "software-engineer",
    model: str | None = "claude-sonnet-4-6",
    plugin: bool = False,
) -> AgentDTO:
    return AgentDTO(
        id=agent_id,
        name=agent_id,
        description="An agent.",
        dispatch_band=3,
        skills=[],
        tools=[],
        model=model,
        max_turns=60,
        input_contract=None,
        plugin=plugin,
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


# ---------------------------------------------------------------------------
# 1. Status-window math
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("active_window_days", "days_ago", "expected_status_field", "expected_http"),
    [
        pytest.param(None, 10, "active", 200, id="default-window-30-recent-is-active"),
        pytest.param(None, 60, "inactive", 200, id="default-window-30-stale-is-inactive"),
        pytest.param(90, 60, "active", 200, id="custom-window-90-recent-enough-is-active"),
        pytest.param(30, 60, "inactive", 200, id="custom-window-30-same-activity-is-inactive"),
        pytest.param(0, 60, "invalid", 400, id="window-below-min-rejected"),
        pytest.param(366, 60, "invalid", 400, id="window-above-max-rejected"),
        pytest.param(1, 60, "invalid-not-checked", 200, id="window-boundary-min-accepted"),
        pytest.param(365, 60, "invalid-not-checked", 200, id="window-boundary-max-accepted"),
    ],
)
def test_status_window_math(
    active_window_days: int | None,
    days_ago: int,
    expected_status_field: str,
    expected_http: int,
) -> None:
    agents = [_make_dto()]
    summary = _make_agent_summary(last_activity_at=_days_ago_iso(days_ago))
    svc = _make_service(agents, telemetry_stub=FakeTelemetryService([summary]))

    status, _, data = _api_data(svc, active_window_days=active_window_days)

    assert status == expected_http
    if expected_http == 400:
        assert "error" in data
        return
    assert data["status_window_days"] == (active_window_days or 30)
    if expected_status_field not in ("invalid-not-checked",):
        assert data["agents"][0]["status"] == expected_status_field


# ---------------------------------------------------------------------------
# 2. Runtime filter (provider-scope) + no-qs parity
# ---------------------------------------------------------------------------


def _build_mixed_runtime_service() -> PanelService:
    agents = [
        _make_dto(agent_id="agent-claude"),
        _make_dto(agent_id="agent-codex"),
        _make_dto(agent_id="agent-both"),
    ]
    summaries = [
        _make_agent_summary("agent-claude", providers=["claude"]),
        _make_agent_summary("agent-codex", providers=["codex"]),
        _make_agent_summary("agent-both", providers=["claude", "codex"]),
    ]
    return _make_service(agents, telemetry_stub=FakeTelemetryService(summaries))


@pytest.mark.parametrize(
    ("qs", "expected_ids"),
    [
        pytest.param(
            {"runtime": ["claude"]}, {"agent-claude", "agent-both"}, id="runtime-claude-scope"
        ),
        pytest.param(
            {"runtime": ["codex"]}, {"agent-codex", "agent-both"}, id="runtime-codex-scope"
        ),
        pytest.param(
            {"runtime": ["unknown-runtime"]},
            {"agent-claude", "agent-both"},
            id="unknown-runtime-falls-back-claude",
        ),
        pytest.param(
            None, {"agent-claude", "agent-both"}, id="no-runtime-qs-matches-explicit-claude"
        ),
    ],
)
def test_runtime_filter_provider_scope(
    qs: dict[str, list[str]] | None, expected_ids: set[str]
) -> None:
    svc = _build_mixed_runtime_service()
    _, _, data = _api_data(svc, qs=qs)
    ids = {card["agent_id"] for card in data["agents"]}
    assert ids == expected_ids


# ---------------------------------------------------------------------------
# 3. No-telemetry / telemetry-None defaults + telemetry-only exclusion
# ---------------------------------------------------------------------------


def test_no_telemetry_defaults_and_telemetry_only_exclusion() -> None:
    """No-match / no-service both zero-default; telemetry-only rows never leak into the roster."""
    agents = [_make_dto(agent_id="unmatched-agent")]

    # No telemetry match for this agent.
    svc_no_match = _make_service(agents, telemetry_stub=FakeTelemetryService([]))
    _, _, data_no_match = _api_data(svc_no_match)
    card = data_no_match["agents"][0]
    assert card["status"] == "inactive"
    assert card["telemetry"]["session_count"] == 0
    assert card["telemetry"]["cost_known"] is False
    assert card["telemetry"]["last_activity_at"] is None

    # No telemetry service at all.
    svc_none = _make_service(agents, telemetry_stub=None)
    _, _, data_none = _api_data(svc_none)
    card_none = data_none["agents"][0]
    assert card_none["status"] == "inactive"
    assert card_none["telemetry"]["session_count"] == 0

    # Telemetry rows without a matching canonical DTO never leak into the response.
    canonical_agents = [_make_dto(agent_id=f"agent-{i}") for i in range(3)]
    summaries = [_make_agent_summary(agent_id=f"agent-{i}") for i in range(5)]
    svc_extra_telemetry = _make_service(
        canonical_agents, telemetry_stub=FakeTelemetryService(summaries)
    )
    _, _, data_extra = _api_data(svc_extra_telemetry)
    ids = {card["agent_id"] for card in data_extra["agents"]}
    assert len(data_extra["agents"]) == 3
    assert ids == {"agent-0", "agent-1", "agent-2"}


# ---------------------------------------------------------------------------
# 4. Plugin-stub exclusion + phases derivation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("agent_id", "is_plugin", "expected_present", "expected_phases"),
    [
        pytest.param(
            "software-engineer",
            False,
            True,
            ["Implementation"],
            id="core-agent-included-with-phase",
        ),
        pytest.param("design-specialist", True, False, None, id="plugin-stub-excluded"),
        pytest.param("mystery-agent", False, True, [], id="unknown-agent-empty-phases-not-faked"),
    ],
)
def test_plugin_exclusion_and_phase_derivation(
    agent_id: str,
    is_plugin: bool,
    expected_present: bool,
    expected_phases: list[str] | None,
) -> None:
    agents = [_make_dto(agent_id=agent_id, plugin=is_plugin)]
    svc = _make_service(agents, telemetry_stub=FakeTelemetryService())
    _, _, data = _api_data(svc)
    ids = {card["agent_id"] for card in data["agents"]}
    assert (agent_id in ids) is expected_present
    if expected_present:
        card = next(c for c in data["agents"] if c["agent_id"] == agent_id)
        assert card["phases"] == expected_phases


# ---------------------------------------------------------------------------
# 5. Workflow membership + provider-failure→empty + model_inherited
# ---------------------------------------------------------------------------


class _FakeWorkflowsService:
    def __init__(self, workflows: list[SimpleNamespace]) -> None:
        self._workflows = workflows

    def list_dadaia_workflows(self) -> list[SimpleNamespace]:
        return list(self._workflows)

    def get_dadaia_workflow(self, name: str) -> None:
        return None
