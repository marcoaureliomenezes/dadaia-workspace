"""Unit tests for GET /api/sessions — the server-side aggregate (v0.1.52 FR1).

The endpoint no longer returns a session *list*: it returns a single aggregate
cost-summary envelope built server-side by ``TelemetryService.aggregate_sessions``.
The per-session detail view (``render_api_session_detail``) was DELETED.

Two survivors:
  1. Aggregate envelope: exact key set, no ``sessions`` array, values
     passthrough, top_agent shape/null, codex null-cost, runtime default/forward,
     detail-view-removed hasattr.
  2. 503 when telemetry None/raises + Host-guard access (foreign-host 403,
     credential-free 200).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.panel.views import api_sessions as api_module
from dadaia_workspace.features.panel.views.api_sessions import render_api_sessions
from dadaia_workspace.features.telemetry.aggregator.runtimes import ADAPTER_REGISTRY

pytestmark = pytest.mark.unit


class _FakeServerRegistryService:
    def list_entries(self, project: Any = None, include_stale: bool = True) -> list[Any]:
        return []


class _FakeSpecContextService:
    def list_all(self) -> list[Any]:
        return []


def _make_service(telemetry_stub: Any = None) -> PanelService:
    return PanelService(
        registry=_FakeServerRegistryService(),  # type: ignore[arg-type]
        spec_context=_FakeSpecContextService(),  # type: ignore[arg-type]
        workspace_root=Path("/workspace"),
        telemetry=telemetry_stub,
        adapter_registry=dict(ADAPTER_REGISTRY),
    )


def _aggregate(
    runtime: str,
    *,
    total_sessions: int,
    active_sessions: int,
    total_cost_usd: float | None,
    cost_known: bool,
    total_messages: int,
    top_agent: SimpleNamespace | None,
    generated_at: str = "2026-05-19T10:00:00Z",
) -> SimpleNamespace:
    """Duck-typed SessionAggregate stand-in (the view reads attributes only)."""
    return SimpleNamespace(
        runtime=runtime,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_cost_usd=total_cost_usd,
        cost_known=cost_known,
        total_messages=total_messages,
        top_agent=top_agent,
        generated_at=generated_at,
    )


_AGG_CLAUDE = _aggregate(
    "claude",
    total_sessions=5,
    active_sessions=2,
    total_cost_usd=0.42,
    cost_known=True,
    total_messages=87,
    top_agent=SimpleNamespace(name="software-engineer", session_count=3),
)

_AGG_CODEX = _aggregate(
    "codex",
    total_sessions=4,
    active_sessions=1,
    total_cost_usd=None,
    cost_known=False,
    total_messages=30,
    top_agent=SimpleNamespace(name="operator", session_count=4),
)


class _FakeTelemetry:
    """Returns a canned SessionAggregate per runtime and records the call."""

    def __init__(self, aggregate: SimpleNamespace | None = None) -> None:
        self._override = aggregate
        self._by_runtime = {"claude": _AGG_CLAUDE, "codex": _AGG_CODEX}
        self.last_kwargs: dict[str, Any] = {}

    def aggregate_sessions(self, runtime: str) -> SimpleNamespace:
        self.last_kwargs = {"runtime": runtime}
        if self._override is not None:
            return self._override
        return self._by_runtime.get(
            runtime,
            _aggregate(
                runtime,
                total_sessions=0,
                active_sessions=0,
                total_cost_usd=None,
                cost_known=False,
                total_messages=0,
                top_agent=None,
            ),
        )


class _RaisingTelemetry:
    def aggregate_sessions(self, **_kw: Any) -> SimpleNamespace:
        raise RuntimeError("db unavailable")


# ---------------------------------------------------------------------------
# 1. Aggregate envelope
# ---------------------------------------------------------------------------


def test_aggregate_envelope_shape_and_values() -> None:
    service = _make_service(telemetry_stub=_FakeTelemetry())

    status, content_type, body = render_api_sessions(service)(qs={"runtime": ["claude"]})
    assert status == 200
    assert content_type == "application/json; charset=utf-8"
    data = json.loads(body)
    assert set(data.keys()) == {
        "runtime",
        "total_sessions",
        "active_sessions",
        "total_cost_usd",
        "cost_known",
        "total_messages",
        "top_agent",
        "generated_at",
    }
    assert "sessions" not in data
    assert data["runtime"] == "claude"
    assert data["total_sessions"] == 5
    assert data["active_sessions"] == 2
    assert data["total_cost_usd"] == 0.42
    assert data["cost_known"] is True
    assert data["total_messages"] == 87
    assert data["generated_at"] == "2026-05-19T10:00:00Z"
    assert data["top_agent"] == {"name": "software-engineer", "session_count": 3}

    # top_agent null passthrough.
    agg_no_top = _aggregate(
        "claude",
        total_sessions=0,
        active_sessions=0,
        total_cost_usd=None,
        cost_known=False,
        total_messages=0,
        top_agent=None,
    )
    service_no_top = _make_service(telemetry_stub=_FakeTelemetry(aggregate=agg_no_top))
    _, _, body_no_top = render_api_sessions(service_no_top)(qs={"runtime": ["claude"]})
    assert json.loads(body_no_top)["top_agent"] is None

    # codex cost fields are null and unknown.
    _, _, body_codex = render_api_sessions(service)(qs={"runtime": ["codex"]})
    data_codex = json.loads(body_codex)
    assert data_codex["runtime"] == "codex"
    assert data_codex["total_cost_usd"] is None
    assert data_codex["cost_known"] is False

    # default runtime is claude; explicit runtime is forwarded.
    tel = _FakeTelemetry()
    service_default = _make_service(telemetry_stub=tel)
    render_api_sessions(service_default)(qs={})
    assert tel.last_kwargs["runtime"] == "claude"
    render_api_sessions(service_default)(qs={"runtime": ["codex"]})
    assert tel.last_kwargs["runtime"] == "codex"

    # The per-session detail view was deleted (v0.1.52 FR1).
    assert not hasattr(api_module, "render_api_session_detail")


# ---------------------------------------------------------------------------
# 2. 503 when telemetry None/raises
# ---------------------------------------------------------------------------


def test_503_when_telemetry_unavailable() -> None:
    service_none = _make_service(telemetry_stub=None)
    status_none, _content_type, body_none = render_api_sessions(service_none)()
    assert status_none == 503
    assert "error" in json.loads(body_none)

    service_raises = _make_service(telemetry_stub=_RaisingTelemetry())
    status_raises, _content_type, _body_raises = render_api_sessions(service_raises)(qs={})
    assert status_raises == 503
