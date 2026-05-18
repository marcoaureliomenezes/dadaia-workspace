"""Panel API views — JSON endpoints for /api/servers, /api/contexts, /api/agents, /api/agents/<id>/prompt, /api/workflows, /api/workflows/<name>.

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
import re
from collections.abc import Callable

from dadaia_workspace.features.agents.reader import AgentNotFoundError, InvalidAgentIdError, get_prompt
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


def render_api_agent_prompt(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/agents/<id>/prompt.

    Response shape (SPEC §5.2):
        {
            "agent_id": "<id>",
            "system_prompt": "<body text, frontmatter stripped>",
            "source_path": "<relative path hint>"
        }

    Status codes:
        200  — agent found, body returned.
        400  — id fails regex OR resolved path escapes the agents base dir.
        404  — id is valid but no corresponding .md file exists.

    Security (OWASP A03, A06):
        - id validated against ^[a-z0-9](?:[a-z0-9_-]{0,63}[a-z0-9])?$ before any I/O.
        - After resolution, Path.resolve().is_relative_to(base) is asserted (path traversal
          defence-in-depth per architect note and SPEC §6).
        - Error messages returned to clients are generic (A06); detail is only logged.
    """

    def _view(agent_id: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        try:
            body, source_path = get_prompt(agent_id, service._workspace_root)
        except InvalidAgentIdError as exc:
            logger.warning("render_api_agent_prompt: invalid agent_id=%r: %s", agent_id, exc)
            error_body = json.dumps(
                {
                    "error": "invalid_agent_id",
                    "message": "Invalid agent ID format or path traversal attempt.",
                }
            ).encode("utf-8")
            return (400, "application/json; charset=utf-8", error_body)
        except AgentNotFoundError as exc:
            logger.debug("render_api_agent_prompt: agent not found agent_id=%r: %s", agent_id, exc)
            error_body = json.dumps(
                {
                    "error": "not_found",
                    "message": f"Agent {agent_id!r} not found.",
                }
            ).encode("utf-8")
            return (404, "application/json; charset=utf-8", error_body)

        # Build a relative source_path hint for the response.
        try:
            relative_hint = str(source_path.relative_to(service._workspace_root))
        except ValueError:
            relative_hint = str(source_path)

        payload = {
            "agent_id": agent_id,
            "system_prompt": body,
            "source_path": relative_hint,
        }
        return (200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

    return _view


# ---------------------------------------------------------------------------
# Workflow name validation regex (SPEC §5.4, §6 path traversal guard)
# Allows: A-Z a-z 0-9 _ -  (no dots, no slashes, no spaces, no special chars)
# ---------------------------------------------------------------------------
_WORKFLOW_NAME_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_-]+$")


def render_api_workflows_list(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/workflows.

    Response shape (SPEC §5.3 — normative):
        {
            "generated_at": "ISO-8601",
            "source_hint": ".dadaia/agentic/workflows/",
            "workflows": [
                {
                    "name": str,
                    "display_name": str,
                    "description": str,
                    "version": str,
                    "schema_version": str,
                    "stage_count": int,        # integer — NOT stages[]
                    "agent_ids": list[str],
                    "has_parallel": bool,
                    "has_gates": bool,
                    "source_path": str
                }
            ]
        }

    No "diagram_svg", no "stages[]" in the items — LIST is lean (D1 synthesis decision).
    Bearer required (SPEC §5.5, G9). Auth is enforced by the handler; this view
    only produces the payload.

    Security (OWASP A03, A06):
        - No user-controlled input is consumed in this view (no path params).
        - json.dumps() handles JSON-string escaping.
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        summaries = service.list_workflow_summaries()
        generated_at = datetime.datetime.now(tz=datetime.UTC).isoformat()
        # Use a stable source_hint; the actual directory is opaque to the client.
        source_hint = ".dadaia/agentic/workflows/"
        workflow_items = [
            {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
                "version": s.version,
                "schema_version": s.schema_version,
                "stage_count": s.stage_count,
                "agent_ids": list(s.agent_ids),
                "has_parallel": s.has_parallel,
                "has_gates": s.has_gates,
                "source_path": s.source_path,
            }
            for s in summaries
        ]
        payload = {
            "generated_at": generated_at,
            "source_hint": source_hint,
            "workflows": workflow_items,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_workflow_detail(
    workflows_service: "object",
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/workflows/<name>.

    Response shape (SPEC §5.4 — normative):
        {
            "name": str,
            "display_name": str,
            "description": str,
            "version": str,
            "schema_version": str,
            "inputs": [...],
            "stages": [{
                "id": str, "agent": str, "needs": [...],
                "parallel_group": str | null, "gate": bool,
                "expected_output_path": str | null,
                "must_include": [...] | null,
                "on_failure": str
            }],
            "diagram_svg": "<svg ... role='img' ...>...</svg>",
            "source_path": str
        }

    Status codes:
        200  — workflow found, detail returned.
        400  — name fails the regex ^[A-Za-z0-9_-]+$ OR path traversal attempt.
        404  — name valid but no matching workflow file exists.

    Security (OWASP A03, A06):
        - name validated against _WORKFLOW_NAME_RE before any service call.
        - Generic error messages to clients; detail logged at WARNING level.
        - json.dumps() handles JSON-string escaping.
    """

    def _view(workflow_name: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        # --- Validate workflow name against the regex ---
        if not workflow_name or not _WORKFLOW_NAME_RE.match(workflow_name):
            logger.warning(
                "render_api_workflow_detail: invalid workflow_name=%r (regex failed)",
                workflow_name,
            )
            error_body = json.dumps(
                {
                    "error": "invalid_workflow_name",
                    "message": "Invalid workflow name format or path traversal attempt.",
                }
            ).encode("utf-8")
            return (400, "application/json; charset=utf-8", error_body)

        # --- Call the service ---
        detail = workflows_service.get_detail(workflow_name)  # type: ignore[attr-defined]
        if detail is None:
            logger.debug(
                "render_api_workflow_detail: workflow not found name=%r", workflow_name
            )
            error_body = json.dumps(
                {
                    "error": "not_found",
                    "message": f"Workflow {workflow_name!r} not found.",
                }
            ).encode("utf-8")
            return (404, "application/json; charset=utf-8", error_body)

        # --- Serialise stages --- (StageDTO dataclass → dict)
        stages_list = [
            {
                "id": s.id,
                "agent": s.agent,
                "needs": list(s.needs),
                "parallel_group": s.parallel_group,
                "gate": s.gate,
                "expected_output_path": s.expected_output_path,
                "must_include": list(s.must_include) if s.must_include is not None else None,
                "on_failure": s.on_failure,
            }
            for s in detail.stages
        ]

        payload = {
            "name": detail.name,
            "display_name": detail.display_name,
            "description": detail.description,
            "version": detail.version,
            "schema_version": detail.schema_version,
            "stage_count": detail.stage_count,
            "agent_ids": list(detail.agent_ids),
            "has_parallel": detail.has_parallel,
            "has_gates": detail.has_gates,
            "inputs": detail.inputs,
            "stages": stages_list,
            "diagram_svg": detail.diagram_svg,
            "source_path": detail.source_path,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


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
