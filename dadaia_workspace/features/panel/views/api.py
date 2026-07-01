"""Panel API views — JSON endpoints for /api/panel-status, /api/contexts, /api/agents, /api/agents/<id>/prompt, /api/workflows, /api/workflows/<name>, /api/sessions, /api/sessions/<runtime>/<session_id>.

JSON shapes (stable contract — if changed, panel.js must be updated in lockstep):

/api/panel-status response:
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
        "status":        "alive"
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
        "model_inherited": bool,     # true when no model: frontmatter — show inherited default
        "max_turns":      int | null,
        "input_contract": dict | null,
        "gate_role":      str | null,  # §7 review-gate / phase role from frontmatter
        "phases":         list[str],   # §7 lifecycle phase(s) owned/gated (constitution-derived)
        "workflows":      list[str],   # workflow display names this agent takes part in
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
import re
from collections.abc import Callable
from pathlib import Path

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


def _workflow_membership(service: PanelService) -> dict[str, list[str]]:
    """Build an ``agent_id -> [workflow display names]`` map.

    Derived at request time by parsing the canonical workflow definitions via
    ``PanelService.list_workflow_summaries()`` and reading each workflow's
    ``agent_ids`` (the distinct agents appearing in its stages). Best-effort:
    a workflows-read failure yields an empty map rather than failing the
    /api/agents response.
    """
    membership: dict[str, list[str]] = {}
    try:
        summaries = service.list_workflow_summaries()
    except Exception:  # noqa: BLE001
        logger.warning(
            "_workflow_membership: list_workflow_summaries() failed; "
            "continuing with empty workflow membership"
        )
        return membership
    for wf in summaries:
        for agent_id in wf.agent_ids:
            bucket = membership.setdefault(agent_id, [])
            if wf.display_name not in bucket:
                bucket.append(wf.display_name)
    return membership


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
                    "status": c.status,
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
        # Parse runtime filter from query-string (NFR5: default to "claude").
        qs: dict[str, list[str]] = _kwargs.get("qs", {})  # type: ignore[assignment]
        _runtime_vals = qs.get("runtime")
        runtime = (_runtime_vals[0].strip().lower() if _runtime_vals else "").strip()
        if runtime not in ("claude", "codex", "pi"):
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

        # Workflow membership: agent_id -> [workflow display names], derived once
        # per request by parsing the canonical workflow definitions.
        membership = _workflow_membership(service)

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
                    "tier": dto.tier,
                    "status": status,
                    "skills": list(dto.skills),
                    "tools": list(dto.tools),
                    "model": dto.model,
                    "model_inherited": dto.model is None,
                    "max_turns": dto.max_turns,
                    "input_contract": dto.input_contract,
                    "gate_role": dto.gate_role,
                    "phases": _agent_phases(dto.id),
                    "workflows": list(membership.get(dto.id, [])),
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
                    "lifecycle_phase": str,    # canonical dev-lifecycle group
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
        # Parse runtime filter from query-string (NFR5: default to "claude").
        # Canonical workflow definitions carry no per-provider discriminator;
        # all workflows are returned regardless of runtime.  The param is parsed
        # here so that ?runtime=codex requests are accepted without error.
        qs: dict[str, list[str]] = _kwargs.get("qs", {})  # type: ignore[assignment]
        _runtime_vals = qs.get("runtime")
        _runtime = (_runtime_vals[0].strip().lower() if _runtime_vals else "").strip()
        if _runtime not in ("claude", "codex", "pi"):
            _runtime = "claude"

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
                "lifecycle_phase": s.lifecycle_phase,
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
    workflows_service: object,
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
            logger.debug("render_api_workflow_detail: workflow not found name=%r", workflow_name)
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
            "lifecycle_phase": detail.lifecycle_phase,
            "inputs": detail.inputs,
            "stages": stages_list,
            "diagram_svg": detail.diagram_svg,
            "source_path": detail.source_path,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


# ---------------------------------------------------------------------------
# dadaia-workflow catalog endpoints (WS-8 / ADR-E)
#
# These describe the *real* Python-owned dadaia-workflows (release_definition,
# implementation, deferred) with purpose, per-step harness/model options,
# availability, and a server-rendered SVG + Mermaid diagram. They are wholly
# additive to the legacy ``/api/workflows`` endpoints above (which serve the
# declarative ``*.workflow.md`` DAGs unchanged).
# ---------------------------------------------------------------------------


def _dadaia_workflow_to_dict(wf: object, *, include_steps: bool) -> dict[str, object]:
    """Serialise a DadaiaWorkflowDTO to a JSON-ready dict.

    The list form omits the heavy step bodies + diagram (lean cards); the detail
    form includes the full step sequence and the server-rendered SVG fluxogram.
    """
    base: dict[str, object] = {
        "name": getattr(wf, "name"),  # noqa: B009
        "display_name": getattr(wf, "display_name"),  # noqa: B009
        "purpose": getattr(wf, "purpose"),  # noqa: B009
        "availability": getattr(wf, "availability"),  # noqa: B009
        "step_count": getattr(wf, "step_count"),  # noqa: B009
    }
    if not include_steps:
        return base
    steps = [
        {
            "order": s.order,
            "label": s.label,
            "role": s.role,
            "purpose": s.purpose,
            "is_gate": s.is_gate,
            "harness_options": list(s.harness_options),
            "model_options": {k: list(v) for k, v in s.model_options.items()},
            "runtime_kind": s.runtime_kind,
            "fragment_id": s.fragment_id,
        }
        for s in getattr(wf, "steps")  # noqa: B009
    ]
    base["steps"] = steps
    base["diagram_svg"] = getattr(wf, "diagram_svg")  # noqa: B009
    return base


def render_api_dadaia_workflows_list(
    workflows_service: object,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/dadaia-workflows.

    Lists every dadaia-workflow with its purpose, availability, and step count
    (lean cards — no per-step bodies or diagrams). A deferred workflow is listed
    with ``availability == "deferred"`` so the panel can mark it unavailable.

    Security (OWASP A03, A06): no user input consumed; json.dumps escapes output.
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        workflows = workflows_service.list_dadaia_workflows()  # type: ignore[attr-defined]
        items = [_dadaia_workflow_to_dict(wf, include_steps=False) for wf in workflows]
        generated_at = datetime.datetime.now(tz=datetime.UTC).isoformat()
        payload = {
            "generated_at": generated_at,
            "source_hint": "dadaia-workflows (Python-owned lifecycle workflows)",
            "workflows": items,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_dadaia_workflow_detail(
    workflows_service: object,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/dadaia-workflows/<name>.

    Returns the full self-description: purpose, the ordered step sequence with
    per-step role/harness_options/model_options/availability flags, and the
    server-rendered SVG DAG fluxogram (``diagram_svg``) of the step sequence.

    Status codes: 200 found; 400 invalid name (regex / traversal); 404 unknown.

    Security (OWASP A03, A06): name validated against _WORKFLOW_NAME_RE before
    any lookup; generic error messages; json.dumps escapes output.
    """

    def _view(workflow_name: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        if not workflow_name or not _WORKFLOW_NAME_RE.match(workflow_name):
            logger.warning(
                "render_api_dadaia_workflow_detail: invalid name=%r (regex failed)",
                workflow_name,
            )
            error_body = json.dumps(
                {
                    "error": "invalid_workflow_name",
                    "message": "Invalid workflow name format or path traversal attempt.",
                }
            ).encode("utf-8")
            return (400, "application/json; charset=utf-8", error_body)

        detail = workflows_service.get_dadaia_workflow(workflow_name)  # type: ignore[attr-defined]
        if detail is None:
            logger.debug("render_api_dadaia_workflow_detail: not found name=%r", workflow_name)
            error_body = json.dumps(
                {
                    "error": "not_found",
                    "message": f"Workflow {workflow_name!r} not found.",
                }
            ).encode("utf-8")
            return (404, "application/json; charset=utf-8", error_body)

        payload = _dadaia_workflow_to_dict(detail, include_steps=True)
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


# ---------------------------------------------------------------------------
# Sessions endpoints (panel-r5-v1 FR3)
# ---------------------------------------------------------------------------

_DEFAULT_SESSIONS_RUNTIME = "claude"
_DEFAULT_SESSIONS_LIMIT = 50


def render_api_sessions(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/sessions.

    Query parameters:
    - runtime: "claude" | "codex" | "pi" (default: "claude")
    - project: optional project slug filter
    - limit:   max rows to return (default 50, must be positive int)

    Response envelope:
        {
            "generated_at": str,         # ISO-8601
            "runtime":      str,
            "project":      str | null,
            "limit":        int | null,
            "total_count":  int,
            "sessions":     [SessionRow, ...]
        }

    Status codes:
        200 — success
        401 — missing / invalid Bearer (enforced by handler, not this view)
        503 — telemetry unavailable

    Security (OWASP A03, A06):
    - limit is validated as a positive integer; invalid values fall back to default.
    - No user-controlled input is reflected verbatim in error messages.
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        if service.telemetry is None:
            body = json.dumps({"error": "telemetry not configured"}).encode("utf-8")
            return (503, "application/json; charset=utf-8", body)

        # Parse query-string kwargs forwarded by the handler.
        qs: dict[str, list[str]] = _kwargs.get("qs", {})  # type: ignore[assignment]

        runtime_vals = qs.get("runtime")
        runtime = runtime_vals[0] if runtime_vals else _DEFAULT_SESSIONS_RUNTIME

        project_vals = qs.get("project")
        project: str | None = project_vals[0] if project_vals else None

        limit_vals = qs.get("limit")
        limit: int | None = None
        if limit_vals:
            try:
                parsed = int(limit_vals[0])
                if parsed > 0:
                    limit = parsed
            except (ValueError, IndexError):
                pass

        try:
            result = service.telemetry.list_sessions(
                runtime=runtime,
                project=project,
                limit=limit,
            )
        except Exception:  # noqa: BLE001
            logger.warning("render_api_sessions: telemetry.list_sessions() failed")
            body = json.dumps({"error": "telemetry unavailable"}).encode("utf-8")
            return (503, "application/json; charset=utf-8", body)

        # Apply runtime adapter enrichment per row.
        adapter = service.get_session_adapter(runtime)
        enriched_sessions = []
        for row in result.sessions:
            if adapter is not None:
                row = adapter.enrich_row(row)
            enriched_sessions.append(
                {
                    "session_id": row.session_id,
                    "runtime": row.runtime,
                    "project": row.project,
                    "cwd": row.cwd,
                    "model": row.model,
                    "started_at": row.started_at,
                    "last_activity_at": row.last_activity_at,
                    "message_count": row.message_count,
                    "context_size_tokens": row.context_size_tokens,
                    "cumulative_cost_usd": row.cumulative_cost_usd,
                    "cost_known": row.cost_known,
                    "status": row.status,
                    "agent_name": row.agent_name,
                    "ai_title": row.ai_title,
                }
            )

        payload = {
            "generated_at": result.generated_at,
            "runtime": result.runtime,
            "project": result.project,
            "limit": result.limit,
            "total_count": result.total_count,
            "sessions": enriched_sessions,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_session_detail(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/sessions/<runtime>/<session_id>.

    Path parameters (forwarded as kwargs by the handler):
    - runtime:    "claude" | "codex" | "pi"
    - session_id: full session identifier

    Response envelope on success (200): same fields as SessionRow plus
    ``event_timestamps`` (list of ISO-8601 strings, ascending).

    Status codes:
        200 — found
        404 — runtime/session_id combination not found
        401 — missing / invalid Bearer (enforced by handler)
        503 — telemetry unavailable

    Security (OWASP A03, A06):
    - session_id is passed directly to the aggregator which uses a parameterised
      SQL query; no string interpolation occurs.
    - Error messages do not expose internal paths or stack traces.
    """

    def _view(
        runtime: str = _DEFAULT_SESSIONS_RUNTIME,
        session_id: str = "",
        **_kwargs: object,
    ) -> tuple[int, str, bytes]:
        if service.telemetry is None:
            body = json.dumps({"error": "telemetry not configured"}).encode("utf-8")
            return (503, "application/json; charset=utf-8", body)

        try:
            detail = service.telemetry.get_session(
                runtime=runtime,
                session_id=session_id,
            )
        except Exception:  # noqa: BLE001
            logger.warning(
                "render_api_session_detail: telemetry.get_session() failed "
                "runtime=%r session_id=%r",
                runtime,
                session_id,
            )
            body = json.dumps({"error": "telemetry unavailable"}).encode("utf-8")
            return (503, "application/json; charset=utf-8", body)

        if detail is None:
            body = json.dumps({"error": "not_found", "message": "Session not found."}).encode(
                "utf-8"
            )
            return (404, "application/json; charset=utf-8", body)

        # Apply runtime adapter enrichment.
        adapter = service.get_session_adapter(runtime)
        if adapter is not None:
            detail = adapter.enrich_detail(detail)

        payload = {
            "session_id": detail.session_id,
            "runtime": detail.runtime,
            "project": detail.project,
            "cwd": detail.cwd,
            "model": detail.model,
            "started_at": detail.started_at,
            "last_activity_at": detail.last_activity_at,
            "message_count": detail.message_count,
            "context_size_tokens": detail.context_size_tokens,
            "cumulative_cost_usd": detail.cumulative_cost_usd,
            "cost_known": detail.cost_known,
            "status": detail.status,
            "agent_name": detail.agent_name,
            "ai_title": detail.ai_title,
            "event_timestamps": list(detail.event_timestamps),
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_academy(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return ``GET /api/academy`` view — list the shipped course catalog.

    Lists the ``knowledge_basis`` modules that ship with the package (the browse
    source for the Academy tab), NOT the user-created course copies under
    ``.dadaia/academy``. Each module carries its title, lesson count, and lessons so
    the panel can expand a module to its lessons and open each lesson via
    ``GET /academy/<module>/<lesson>``.

    Returns 200 with an empty list when ``service.academy`` is None.

    Response shape::

        {"modules": [
            {"module": "07_codex", "module_number": 7, "title": "...",
             "lesson_count": 9,
             "lessons": [{"lesson": "01_codex_mental_model.md", "title": "..."}]}
        ]}
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        if service.academy is None:
            body = json.dumps({"modules": []}).encode("utf-8")
            return (200, "application/json; charset=utf-8", body)
        catalog = service.academy.list_module_catalog()
        body = json.dumps({"modules": catalog}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def render_api_reports(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return ``GET /api/reports`` view — list human-readable HTML reports.

    Reports are discovered from rendered artifacts under
    ``<workspace_root>/.dadaia/reports/`` and enriched from canonical handoffs in
    ``.dadaia/handoff/`` plus legacy adjacent handoffs in ``.dadaia/reports/``.
    Malformed handoffs are skipped with a WARNING log.

    Response shape: {"reports": [{title, agent, context, created_at, path, findings_summary}]}
    findings_summary: {"CRITICAL": N, "HIGH": N, "MEDIUM": N, "LOW": N}
    """
    _log = logging.getLogger(__name__)

    def _severity_counts(findings: object) -> dict[str, int]:
        counts: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        if not isinstance(findings, list):
            return counts
        for f in findings:
            if not isinstance(f, dict):
                continue
            sev = f.get("severity", "").upper()
            if sev in counts:
                counts[sev] += 1
        return counts

    def _created_at_from_file(path: Path) -> str:
        match = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{6}Z)", path.name)
        if match:
            raw = match.group(1)
            return f"{raw[:13]}:{raw[13:15]}:{raw[15:]}"
        return (
            datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.UTC)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def _empty_counts() -> dict[str, int]:
        return {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    def _row_from_report(report: Path, reports_root: Path) -> dict[str, object]:
        route_path = report.relative_to(reports_root).as_posix()
        parts = Path(route_path).parts
        return {
            "title": report.stem,
            "agent": parts[1] if len(parts) > 1 else "",
            "context": parts[0] if parts else "",
            "created_at": _created_at_from_file(report),
            "path": route_path,
            "findings_summary": _empty_counts(),
        }

    def _iter_handoffs(reports_root: Path) -> list[Path]:
        handoffs: list[Path] = []
        for root in (service.workspace_root / ".dadaia" / "handoff", reports_root):
            if root.exists():
                handoffs.extend(root.rglob("*.handoff.json"))
        return handoffs

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        reports_root = (service.workspace_root / ".dadaia" / "reports").resolve()
        retention = service.get_report_retention()
        try:
            retention.cleanup()
        except Exception as exc:  # noqa: BLE001
            _log.warning("Report retention cleanup skipped: %s", exc)
        retention_by_route = {
            record.artifact_path.removeprefix(".dadaia/reports/"): record
            for record in retention.list_reports()
        }
        results_by_path: dict[str, dict[str, object]] = {}
        if reports_root.exists():
            for report in reports_root.rglob("*.html"):
                if report.is_file():
                    row = _row_from_report(report, reports_root)
                    results_by_path[str(row["path"])] = row

            for handoff in _iter_handoffs(reports_root):
                try:
                    data = json.loads(handoff.read_text(encoding="utf-8"))
                    artifact = data.get("artifact", {})
                    if not isinstance(artifact, dict):
                        continue
                    artifact_path = str(artifact.get("path", ""))
                    if not artifact_path.startswith(".dadaia/reports/"):
                        continue
                    report_path = _report_route_path(artifact_path)
                    report_file = (reports_root / report_path).resolve()
                    try:
                        report_file.relative_to(reports_root)
                    except ValueError:
                        continue
                    if not report_file.is_file() or report_file.suffix.lower() != ".html":
                        continue
                    row = results_by_path.setdefault(
                        report_path,
                        _row_from_report(report_file, reports_root),
                    )
                    row["agent"] = data.get("agent") or row["agent"]
                    row["context"] = data.get("context") or row["context"]
                    row["created_at"] = data.get("produced_at") or row["created_at"]
                    row["findings_summary"] = _severity_counts(data.get("findings", []))
                except Exception as exc:  # noqa: BLE001
                    _log.warning("Skipping malformed handoff %s: %s", handoff, exc)

        results = list(results_by_path.values())
        now = datetime.datetime.now(tz=datetime.UTC)
        for row in results:
            record = retention_by_route.get(str(row["path"]))
            if record is None:
                row["important"] = False
                row["expires_at"] = None
                row["is_expired"] = False
                row["retention_reason"] = None
                row["retention_status"] = "unknown"
                continue
            expires_at = record.effective_timestamp + datetime.timedelta(hours=48)
            is_expired = expires_at <= now
            row["important"] = record.important
            row["expires_at"] = expires_at.isoformat().replace("+00:00", "Z")
            row["is_expired"] = is_expired
            if record.important:
                row["retention_status"] = "important"
                row["retention_reason"] = "Marked important"
            elif is_expired:
                row["retention_status"] = "expired"
                row["retention_reason"] = "Expired after 48h"
            else:
                row["retention_status"] = "expires"
                row["retention_reason"] = "Expires after 48h"
        results.sort(key=lambda r: str(r["created_at"]), reverse=True)
        body = json.dumps({"reports": results}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def mark_report_important(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Mark a report important from the Reports panel."""

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        retention = service.get_report_retention()
        try:
            artifact = retention.mark_important(path)
        except ValueError as exc:
            body = json.dumps({"error": "invalid_path", "message": str(exc)}).encode("utf-8")
            return (400, "application/json; charset=utf-8", body)
        body = json.dumps({"important": True, "artifact_path": artifact}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def unmark_report_important(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Remove important protection from a report from the Reports panel."""

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        retention = service.get_report_retention()
        try:
            artifact = retention.unmark_important(path)
        except ValueError as exc:
            body = json.dumps({"error": "invalid_path", "message": str(exc)}).encode("utf-8")
            return (400, "application/json; charset=utf-8", body)
        body = json.dumps({"important": False, "artifact_path": artifact}).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view


def _report_route_path(artifact_path: str) -> str:
    prefix = ".dadaia/reports/"
    if artifact_path.startswith(prefix):
        return artifact_path[len(prefix) :]
    return artifact_path


# ---------------------------------------------------------------------------
# Report identity injection (operator demand 2026-06-11)
#
# Agent-authored reports carry arbitrary inline styles, frequently unreadable.
# At serve time we inject the dadaia identity stylesheets into the <head> so
# every report inherits the visual identity regardless of how it was authored.
# The link tags reference /static/tokens.css (palette + theme) and
# /static/reports-doc.css (base identity + a readability override that WINS
# over agent styling for body fg/bg). Only text/html bodies are mutated.
# ---------------------------------------------------------------------------

_REPORT_IDENTITY_HEAD = (
    "<script>(function(){var t=localStorage.getItem('dadaia-panel-theme');"
    "if(t&&(t==='mint'||t==='sage'||t==='warm')){document.documentElement.dataset.theme=t;}})();</script>"
    '<link rel="stylesheet" href="/static/tokens.css">'
    '<link rel="stylesheet" href="/static/reports-doc.css">'
)

_HEAD_OPEN_RE = re.compile(r"<head[^>]*>", re.IGNORECASE)
_HTML_OPEN_RE = re.compile(r"<html[^>]*>", re.IGNORECASE)

_REPORT_ASSET_MIME: dict[str, str] = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".json": "application/json; charset=utf-8",
}


def _report_content_type(suffix: str) -> str:
    """Content-type for a non-HTML report asset (default text/html for legacy)."""
    return _REPORT_ASSET_MIME.get(suffix, "text/html; charset=utf-8")


def _inject_report_identity(html: str) -> str:
    """Inject the dadaia identity stylesheets into a report's HTML <head>.

    Insertion makes inheritance win for base readability: the base layer is
    injected right after ``<head>`` (before any agent ``<style>`` inside head),
    and the reports-doc.css override layer uses ``!important`` on body fg/bg so
    it still wins regardless of agent inline styles.

    Falls back to inserting after ``<html>`` or prepending a ``<head>`` block
    when the report has no ``<head>``. Idempotent: a report already carrying the
    marker link is left unchanged.
    """
    if "/static/reports-doc.css" in html:
        return html
    head_match = _HEAD_OPEN_RE.search(html)
    if head_match is not None:
        idx = head_match.end()
        return html[:idx] + _REPORT_IDENTITY_HEAD + html[idx:]
    html_match = _HTML_OPEN_RE.search(html)
    if html_match is not None:
        idx = html_match.end()
        return html[:idx] + "<head>" + _REPORT_IDENTITY_HEAD + "</head>" + html[idx:]
    return "<head>" + _REPORT_IDENTITY_HEAD + "</head>" + html


def serve_report_file(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Serve a report HTML file with path-traversal guard.

    Resolves the requested path under ``<workspace_root>/.dadaia/reports/``.
    Returns 403 if the resolved path escapes the boundary.
    Returns 404 if the file does not exist.

    For ``text/html`` reports, the dadaia identity stylesheets are injected into
    the ``<head>`` at serve time (operator demand 2026-06-11) so every report
    inherits the visual identity. Non-HTML report assets are served verbatim.

    Security (OWASP A01, A03): Path.resolve() is used to canonicalise the
    requested path; relative_to() enforces the boundary without string ops.
    """

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        reports_root = (service.workspace_root / ".dadaia" / "reports").resolve()
        requested = (service.workspace_root / ".dadaia" / "reports" / path).resolve()
        # Path-traversal guard (OWASP A01)
        try:
            requested.relative_to(reports_root)
        except ValueError:
            return (403, "text/plain; charset=utf-8", b"403 Forbidden")
        if not requested.exists() or not requested.is_file():
            return (404, "text/plain; charset=utf-8", b"404 Not Found")
        content = requested.read_bytes()
        # Only mutate HTML reports; serve every other asset byte-verbatim.
        if requested.suffix.lower() in (".html", ".htm"):
            try:
                injected = _inject_report_identity(content.decode("utf-8"))
                return (200, "text/html; charset=utf-8", injected.encode("utf-8"))
            except UnicodeDecodeError:
                # Non-UTF-8 HTML — serve verbatim rather than corrupt bytes.
                return (200, "text/html; charset=utf-8", content)
        return (200, _report_content_type(requested.suffix.lower()), content)

    return _view


def delete_report_file(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Delete a report HTML file and handoffs that reference it.

    Path-traversal guard: resolves path under .dadaia/reports/.
    Returns 403 if outside boundary, 404 if not found, 200 on success.

    Security (OWASP A01, A03): same boundary check as serve_report_file.
    Deletes handoff JSON files under .dadaia/handoff/ and legacy adjacent
    handoffs under .dadaia/reports/ whose artifact.path points at the target
    report.
    """

    def _view(*, path: str, **_kwargs: object) -> tuple[int, str, bytes]:
        reports_root = (service.workspace_root / ".dadaia" / "reports").resolve()
        target = (service.workspace_root / ".dadaia" / "reports" / path).resolve()
        try:
            target.relative_to(reports_root)
        except ValueError:
            return (403, "application/json; charset=utf-8", b'{"error": "forbidden"}')
        if not target.exists():
            return (404, "application/json; charset=utf-8", b'{"error": "not found"}')
        target.unlink()
        target_ref = target.relative_to(service.workspace_root).as_posix()
        for handoff_root in (
            service.workspace_root / ".dadaia" / "handoff",
            service.workspace_root / ".dadaia" / "reports",
        ):
            if not handoff_root.exists():
                continue
            for handoff in handoff_root.rglob("*.handoff.json"):
                try:
                    data = json.loads(handoff.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    continue
                artifact = data.get("artifact", {})
                if isinstance(artifact, dict) and artifact.get("path") == target_ref:
                    handoff.unlink()
        return (200, "application/json; charset=utf-8", b'{"deleted": true}')

    return _view


def render_health() -> Callable[..., tuple[int, str, bytes]]:
    """Return a view callable for GET /health — public, no auth, agent-friendly."""
    import importlib.metadata

    try:
        version = importlib.metadata.version("dadaia-workspace")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"

    body = json.dumps({"status": "ok", "version": version}).encode()

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        return (200, "application/json", body)

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
