"""Panel API view — GET /api/sessions (server-side session cost aggregate).

The endpoint returns a single aggregate cost-summary envelope built server-side by
``TelemetryService.aggregate_sessions`` (panel-plumbing v0.1.52 FR1), NOT a session list.

Response envelope:
    {
        "runtime":         str,
        "total_sessions":  int,
        "active_sessions": int,
        "total_cost_usd":  float | null,
        "cost_known":      bool,
        "total_messages":  int,
        "top_agent":       {"name": str, "session_count": int} | null,
        "generated_at":    str,           # ISO-8601
    }

Security (OWASP A03, A06):
- No user-controlled input is reflected verbatim in error messages.
- No content fields are read or returned (privacy invariant T1).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

from dadaia_workspace.features.panel.service import PanelService

logger = logging.getLogger(__name__)

_DEFAULT_SESSIONS_RUNTIME = "claude"


def render_api_sessions(
    service: PanelService,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves GET /api/sessions.

    Query parameters:
    - runtime: "claude" | "codex" | "pi" (default: "claude")

    Status codes:
        200 — success
        503 — telemetry unavailable

    Security (OWASP A03, A06):
    - No user-controlled input is reflected verbatim in error messages.
    - No content fields are read or returned (privacy invariant T1).
    """

    def _view(**_kwargs: object) -> tuple[int, str, bytes]:
        if service.telemetry is None:
            body = json.dumps({"error": "telemetry not configured"}).encode("utf-8")
            return (503, "application/json; charset=utf-8", body)

        # Parse query-string kwargs forwarded by the handler.
        qs: dict[str, list[str]] = _kwargs.get("qs", {})  # type: ignore[assignment]
        runtime_vals = qs.get("runtime")
        runtime = runtime_vals[0] if runtime_vals else _DEFAULT_SESSIONS_RUNTIME

        try:
            result = service.telemetry.aggregate_sessions(runtime=runtime)
        except Exception:  # noqa: BLE001
            logger.warning("render_api_sessions: telemetry.aggregate_sessions() failed")
            body = json.dumps({"error": "telemetry unavailable"}).encode("utf-8")
            return (503, "application/json; charset=utf-8", body)

        top = result.top_agent
        top_agent = None if top is None else {"name": top.name, "session_count": top.session_count}
        payload = {
            "runtime": result.runtime,
            "total_sessions": result.total_sessions,
            "active_sessions": result.active_sessions,
            "total_cost_usd": result.total_cost_usd,
            "cost_known": result.cost_known,
            "total_messages": result.total_messages,
            "top_agent": top_agent,
            "generated_at": result.generated_at,
        }
        body = json.dumps(payload).encode("utf-8")
        return (200, "application/json; charset=utf-8", body)

    return _view
