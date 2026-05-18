"""Panel API views — JSON endpoints for /api/servers, /api/contexts, /api/agents.

JSON shapes (stable contract — if changed, panel.js must be updated in lockstep):

/api/servers response:
  {
    "groups": [
      {
        "group_label": str,          # repo slug or "Outros"
        "context_name": str | null,  # human-readable context name, or null
        "rows": [
          {
            "port":       int,
            "project":    str,
            "url":        str,
            "status":     "active" | "stale",
            "pid":        int | null,
            "expires_at": str,       # ISO-8601 expiry timestamp
            "description": str | null
          }
        ]
      }
    ],
    "unregistered": [                # v0.1.1: orphan listeners (Bug D)
      {
        "port":        int,
        "bind":        str,          # "127.0.0.1" / "0.0.0.0" / "::" / etc.
        "pid":         int,          # always set (pidless filtered out)
        "cmdline":     str,
        "cwd":         str,
        "lan_exposed": bool          # bind in {"0.0.0.0", "::"}
      }
    ]
  }

/api/contexts response:
  {
    "contexts": [
      {
        "slug":          str,
        "name":          str,
        "repo_path":     str,
        "branch":        str | null,
        "is_primary":    bool
      }
    ]
  }

/api/agents response (SPEC §5.1 — normative):
  {
    "generated_at":       str,   # ISO-8601
    "status_window_days": int,   # active/inactive threshold (default 30, range 1-365)
    "window_days":        int,   # telemetry aggregation window (180)
    "pricing_age_days":   int | null,
    "pricing_model_date": str | null,
    "agents": [
      {
        "agent_id":       str,
        "display_name":   str,
        "description":    str,
        "status":         "active" | "inactive",
        "skills":         list[str],
        "tools":          list[str],
        "model":          str | null,
        "opencode_model": str | null,
        "max_turns":      int | null,
        "input_contract": dict | null,
        "telemetry": {
          "session_count":      int,
          "total_cost_usd":     float | null,
          "total_cost_30d_usd": float | null,
          "cost_known":         bool,
          "last_activity_at":   str | null,
          "providers":          list[str],
          "dominant_model":     str | null,
          "is_subagent":        bool,
          "suspect_count":      int,
          "token_totals":       {input, cache_creation, cache_read, output},
          "context_breakdown":  list,
          "recent_sessions":    list
        }
      }
    ]
  }

  Validation: active_window_days must be in range [1, 365]. Returns 400 if
  out of range. Telemetry-only agents (not in canonical catalog) are excluded.

Security (R3-A): json.dumps() handles JSON-string escaping; no HTML escaping needed here.
Content-Type is always set to application/json; charset=utf-8.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import logging
from collections.abc import Callable

from dadaia_workspace.features.panel.service import PanelService
from dadaia_workspace.features.telemetry.aggregator.models import AgentSummary

logger = logging.getLogger(__name__)

_ACTIVE_WINDOW_DAYS_MIN = 1
_ACTIVE_WINDOW_DAYS_MAX = 365
_ACTIVE_WINDOW_DAYS_DEFAULT = 30
_TELEMETRY_WINDOW_DAYS = 180  # existing aggregation window — not configurable


def render_api_servers(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serialises list_servers_grouped() as JSON."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        groups = service.list_servers_grouped()
        # Unregistered listeners section removed from UI (panel-defects hotfix).
        # Key kept for back-compat with any client that reads it.
        unregistered: list = []
        payload = {
            "groups": [
                {
                    "group_label": g.group_label,
                    "context_name": g.context_name,
                    "rows": [
                        {
                            "port": r.port,
                            "project": r.project,
                            "url": r.url,
                            "status": str(r.status),
                            "pid": r.pid,
                            "expires_at": r.expires_at,
                            "description": r.description,
                        }
                        for r in g.rows
                    ],
                }
                for g in groups
            ],
            "unregistered": unregistered,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_contexts(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serialises list_active_contexts() as JSON."""

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        contexts = service.list_active_contexts()
        payload = {
            "contexts": [
                {
                    "slug": c.slug,
                    "name": c.name,
                    "repo_path": str(c.repo_path),
                    "branch": c.branch,
                    "is_primary": c.is_primary,
                }
                for c in contexts
            ]
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_agents_canonical(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that builds the SPEC §5.1 /api/agents response.

    The view accepts an optional ``active_window_days`` keyword argument
    (int, default 30) which is validated against [1, 365].  The handler
    is responsible for parsing ``?active_window_days=N`` from the query
    string and forwarding it here.

    Behaviour:
    - Reads the canonical agent catalog via PanelService.
    - Overlays telemetry from the injected TelemetryService (if available).
    - Agents present only in telemetry (not in canonical catalog) are excluded.
    - ``status`` = "active" if ``last_activity_at`` is within ``active_window_days``
      from *now*; else "inactive".
    - Telemetry fields are nested under a ``"telemetry"`` sub-object (NORMATIVE).
    - Returns 400 if ``active_window_days`` is out of [1, 365].
    """

    def _view(
        active_window_days: int = _ACTIVE_WINDOW_DAYS_DEFAULT,
        **_kwargs: object,
    ) -> tuple[int, str, bytes]:
        # Validate active_window_days range.
        if not (_ACTIVE_WINDOW_DAYS_MIN <= active_window_days <= _ACTIVE_WINDOW_DAYS_MAX):
            body = json.dumps(
                {
                    "error": "invalid_parameter",
                    "message": (
                        f"active_window_days must be in range "
                        f"[{_ACTIVE_WINDOW_DAYS_MIN}, {_ACTIVE_WINDOW_DAYS_MAX}], "
                        f"got {active_window_days}"
                    ),
                }
            ).encode("utf-8")
            return (400, "application/json; charset=utf-8", body)

        # Fetch telemetry aggregation (best-effort — None if not configured).
        tel_result = None
        if service.telemetry is not None:
            try:
                tel_result = service.telemetry.list_agents(
                    window_days=_TELEMETRY_WINDOW_DAYS,
                    context_slug=None,
                    limit=200,
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "render_api_agents_canonical: telemetry.list_agents() failed; "
                    "continuing with zero-telemetry overlay"
                )

        # Build a lookup: agent_id → AgentSummary from telemetry.
        tel_by_id: dict[str, AgentSummary] = {}
        tel_meta: dict[str, object] = {
            "generated_at": datetime.datetime.now(tz=datetime.UTC).isoformat(),
            "window_days": _TELEMETRY_WINDOW_DAYS,
            "pricing_age_days": None,
            "pricing_model_date": None,
        }
        if tel_result is not None:
            for s in tel_result.agents:
                tel_by_id[s.agent_id] = s
            tel_meta = {
                "generated_at": tel_result.generated_at,
                "window_days": tel_result.window_days,
                "pricing_age_days": tel_result.pricing_age_days,
                "pricing_model_date": tel_result.pricing_model_date,
            }

        # Cutoff datetime for status computation.
        now = datetime.datetime.now(tz=datetime.UTC)
        cutoff = now - datetime.timedelta(days=active_window_days)

        # Read canonical agents.  PanelService exposes the list via its internal
        # override (for tests) or by calling the real reader.
        canonical_agents = service.list_canonical_agents()

        # Build output — one entry per canonical agent.
        agent_entries = []
        for dto in canonical_agents:
            tel_summary: AgentSummary | None = tel_by_id.get(dto.id)

            # Determine status and telemetry overlay.
            if tel_summary is not None:
                last_activity_at: str | None = tel_summary.last_activity_at
                # last_activity_at may be an empty string when the agent has
                # never been invoked (the aggregator returns "" for no activity).
                if not last_activity_at:
                    last_activity_at = None

                if last_activity_at:
                    try:
                        last_dt = datetime.datetime.fromisoformat(
                            last_activity_at.replace("Z", "+00:00")
                        )
                        # Ensure timezone-aware comparison.
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=datetime.UTC)
                        status = "active" if last_dt >= cutoff else "inactive"
                    except ValueError:
                        status = "inactive"
                else:
                    status = "inactive"

                telemetry_sub: dict[str, object] = {
                    "session_count": tel_summary.session_count,
                    "total_cost_usd": tel_summary.total_cost_usd,
                    "total_cost_30d_usd": _compute_30d_cost(tel_summary),
                    "cost_known": tel_summary.cost_known,
                    "last_activity_at": last_activity_at,
                    "providers": list(tel_summary.providers),
                    "dominant_model": tel_summary.dominant_model,
                    "is_subagent": tel_summary.is_subagent,
                    "suspect_count": tel_summary.suspect_count,
                    "token_totals": dataclasses.asdict(tel_summary.token_totals),
                    "context_breakdown": [
                        dataclasses.asdict(cb)
                        for cb in tel_summary.context_breakdown
                    ],
                    "recent_sessions": [
                        dataclasses.asdict(rs)
                        for rs in tel_summary.recent_sessions
                    ],
                }
            else:
                # No telemetry data for this canonical agent.
                status = "inactive"
                telemetry_sub = _empty_telemetry_sub()

            agent_entries.append(
                {
                    "agent_id": dto.id,
                    "display_name": dto.name,
                    "description": dto.description,
                    "status": status,
                    "skills": list(dto.skills),
                    "tools": list(dto.tools),
                    "model": dto.model,
                    "opencode_model": dto.opencode_model,
                    "max_turns": dto.max_turns,
                    "input_contract": dto.input_contract,
                    "telemetry": telemetry_sub,
                }
            )

        payload = {
            "generated_at": tel_meta["generated_at"],
            "status_window_days": active_window_days,
            "window_days": tel_meta["window_days"],
            "pricing_age_days": tel_meta["pricing_age_days"],
            "pricing_model_date": tel_meta["pricing_model_date"],
            "agents": agent_entries,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def _empty_telemetry_sub() -> dict[str, object]:
    """Return a zero-state telemetry sub-object for agents with no telemetry data."""
    return {
        "session_count": 0,
        "total_cost_usd": None,
        "total_cost_30d_usd": None,
        "cost_known": False,
        "last_activity_at": None,
        "providers": [],
        "dominant_model": None,
        "is_subagent": False,
        "suspect_count": 0,
        "token_totals": {"input": 0, "cache_creation": 0, "cache_read": 0, "output": 0},
        "context_breakdown": [],
        "recent_sessions": [],
    }


def _compute_30d_cost(summary: AgentSummary) -> float | None:
    """Compute total_cost_30d_usd from the summary's recent_sessions.

    We use recent_sessions to sum costs for sessions within the last 30 days.
    If cost is unknown for all recent sessions, return None.
    """
    cutoff_30d = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=30)
    total: float = 0.0
    any_known = False

    for rs in summary.recent_sessions:
        try:
            session_date = datetime.datetime.fromisoformat(rs.date).replace(
                tzinfo=datetime.UTC
            )
        except ValueError:
            continue
        if session_date >= cutoff_30d and rs.cost_usd is not None:
            total += rs.cost_usd
            any_known = True

    return total if any_known else None
