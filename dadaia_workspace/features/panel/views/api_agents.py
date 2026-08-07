"""Panel API views — GET /api/agents and GET /api/agents/<id>/prompt.

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
        "model_inherited": bool,     # true when no model: frontmatter — show inherited default
        "max_turns":      int | null,
        "input_contract": dict | null,
        "gate_role":      str | null,  # §7 review-gate / phase role from frontmatter
        "phases":         list[str],   # §7 lifecycle phase(s) owned/gated (constitution-derived)
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
  Plugin STUBS (frontmatter ``plugin: true`` — design-specialist, devops-engineer,
  frontend-engineer) are excluded from the roster (constitution §14).

Security (R3-A): json.dumps() handles JSON-string escaping; no HTML escaping needed here.
Content-Type is always set to application/json; charset=utf-8.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
import logging
from collections.abc import Callable

from dadaia_workspace.core.harness_registry import is_l1
from dadaia_workspace.core.models.agent import AgentNotFoundError, InvalidAgentIdError
from dadaia_workspace.core.models.telemetry import AgentSummary
from dadaia_workspace.features.panel.service import PanelService

logger = logging.getLogger(__name__)

_ACTIVE_WINDOW_DAYS_MIN = 1
_ACTIVE_WINDOW_DAYS_MAX = 365
_ACTIVE_WINDOW_DAYS_DEFAULT = 30
_TELEMETRY_WINDOW_DAYS = 180  # existing aggregation window — not configurable

# Development-lifecycle phase ownership, derived HONESTLY from the constitution
# §7 phase table and §14 roster. Keyed by canonical agent id. Each value is the
# ordered list of phase labels the agent OWNS or GATES. Agents not listed here
# resolve to an empty list (rendered as a neutral "—" in the panel, never faked).
#
# §7 table (normative):
#   1 Backlog definition  — project-manager
#   3 Research            — PM-dispatched
#   4 Audit               — project-auditor
#   5 Release definition  — product-engineer (SPEC/PLAN/TASKS); software-architect feeds
#   6 Implementation      — software-engineer; ai-engineer (AI-entity surface)
#   7 Review gates        — qa-engineer (commit) · security-reviewer (push) · code-reviewer (PR)
#   8 Closure             — product-engineer
_AGENT_PHASES: dict[str, list[str]] = {
    "project-manager": ["Backlog definition", "Coordinator (all phases)"],
    "product-engineer": ["Release definition", "Closure"],
    "software-architect": ["Release definition (architecture feed)"],
    "software-engineer": ["Implementation"],
    "ai-engineer": ["Implementation (AI-entity surface)"],
    "qa-engineer": ["Review gate — commit"],
    "security-reviewer": ["Review gate — push"],
    "code-reviewer": ["Review gate — PR"],
    "project-auditor": ["Audit"],
}


def _agent_phases(agent_id: str) -> list[str]:
    """Return the §7 lifecycle phase(s) an agent owns or gates.

    Derived from the constitution §7 table via ``_AGENT_PHASES``. Returns an
    empty list for any agent not in the table — the panel renders that as a
    neutral placeholder, never a fabricated phase.
    """
    return list(_AGENT_PHASES.get(agent_id, []))


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
        # Parse runtime filter from query-string (NFR5: default to "claude").
        qs: dict[str, list[str]] = _kwargs.get("qs", {})  # type: ignore[assignment]
        _runtime_vals = qs.get("runtime")
        runtime = (_runtime_vals[0].strip().lower() if _runtime_vals else "").strip()
        if not is_l1(runtime):
            runtime = "claude"

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
        # Filter by runtime: include agent if its telemetry providers list contains
        # the requested runtime.  When runtime="claude" and the agent has no telemetry
        # entry, it is included (all canonical agents default to claude).
        agent_entries = []
        for dto in canonical_agents:
            # Exclude plugin STUBS (constitution §14 / plugin-scope rule): they
            # carry no behavior in the core install and must never appear as
            # ghost agents in the Agentic tab.
            if dto.plugin:
                continue

            tel_summary: AgentSummary | None = tel_by_id.get(dto.id)

            # Runtime-scoped filter (FR5 / NFR5).
            if runtime == "claude":
                # Include agents with no telemetry (canonical-only) or providers containing "claude".
                if tel_summary is not None and "claude" not in tel_summary.providers:
                    continue
            else:
                # For any non-claude runtime, only include agents explicitly associated with it.
                if tel_summary is None or runtime not in tel_summary.providers:
                    continue

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
                        dataclasses.asdict(cb) for cb in tel_summary.context_breakdown
                    ],
                    "recent_sessions": [
                        dataclasses.asdict(rs) for rs in tel_summary.recent_sessions
                    ],
                }
            else:
                # No telemetry data for this canonical agent.
                status = "inactive"
                telemetry_sub = _empty_telemetry_sub()

            # Model resolution: the configured model from frontmatter. When the
            # agent declares no ``model:``, ``model`` is null and the panel shows
            # the inherited harness default with a marker — never a fabricated id.
            agent_entries.append(
                {
                    "agent_id": dto.id,
                    "display_name": dto.name,
                    "description": dto.description,
                    "dispatch_band": dto.dispatch_band,
                    "status": status,
                    "skills": list(dto.skills),
                    "tools": list(dto.tools),
                    "model": dto.model,
                    "model_inherited": dto.model is None,
                    "max_turns": dto.max_turns,
                    "input_contract": dto.input_contract,
                    "gate_role": dto.gate_role,
                    "phases": _agent_phases(dto.id),
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
            prompt = service.get_agent_prompt(agent_id)
            body, source_path = prompt.body, prompt.source_path
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
            relative_hint = str(source_path.relative_to(service.workspace_root))
        except ValueError:
            relative_hint = str(source_path)

        payload = {
            "agent_id": agent_id,
            "system_prompt": body,
            "source_path": relative_hint,
        }
        return (200, "application/json; charset=utf-8", json.dumps(payload).encode("utf-8"))

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
            session_date = datetime.datetime.fromisoformat(rs.date).replace(tzinfo=datetime.UTC)
        except ValueError:
            continue
        if session_date >= cutoff_30d and rs.cost_usd is not None:
            total += rs.cost_usd
            any_known = True

    return total if any_known else None
