"""PanelHandler — regex-dispatch HTTP request handler for the panel.

Design (architect D3):
  ROUTES is a compiled ordered list of ``(pattern, view_callable)`` pairs.
  ``do_GET`` walks the list in order; the first match wins.  Named capture
  groups from the regex are passed as keyword arguments to the view callable.

  View callables are injected at handler-class creation time via
  ``make_handler_class(views)``, so this module carries zero rendering logic
  and can be unit-tested with stub views without spinning a real server.

Auth (T-AM-13, T-AM-15):
  API routes (``/api/*``) require ``Authorization: Bearer <token>``.
  Without a valid token: 401 Unauthorized.

  The HTML root (``/``) remains unauthenticated in v1.  The SPEC § Auth model
  documents that the `dadaia panel start` command prints the URL with
  ``?token=<value>`` for browser first-load; the token then migrates to a
  session cookie via JS after the first fetch.  Cookie-based auth enforcement
  on ``/`` is deferred to a future hotfix once the cookie flow is implemented.

Security headers (T-AM-14, T8):
  _security_headers(content_type) — CSP for HTML, nosniff for JSON.

404 body (T-2.3, constitution error contract — updated for T-AM-15):
  "Route not found. The panel exposes / /api/panel-status /api/contexts
   /api/agents /api/agents/<id>/sessions /api/workflows
   /api/sessions /api/sessions/<runtime>/<session_id>
   /health /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>.
   Open / for the index."
"""

from __future__ import annotations

import dataclasses
import json
import re
import urllib.parse
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler
from typing import Any

from dadaia_workspace.features.panel.auth import validate as _validate_bearer

# ---------------------------------------------------------------------------
# CSP script-src SHA-256 hashes (T-14..T-17).
# These must exactly match the inline <script> content in index.py / wrapper.py.
# Recompute with:
#   import hashlib, base64
#   base64.b64encode(hashlib.sha256(content.encode()).digest()).decode()
# ---------------------------------------------------------------------------
# Theme-switcher snippet (used in index.py and wrapper.py):
#   (function(){var t=localStorage.getItem('dadaia-panel-theme');
#    if(t&&(t==='mint'||t==='sage'||t==='warm')){
#    document.documentElement.dataset.theme=t;}})();
_CSP_SCRIPT_HASH_1 = "'sha256-GRTndW6m1zCm5uxB5kEDoOXw05c1c9MDdem3TFqSMfQ='"
# Runtime-switcher snippet (used in index.py only):
#   (function(){var r=localStorage.getItem('dadaia-panel-runtime');
#    if(r&&(r==='claude'||r==='codex')){
#    document.documentElement.dataset.runtime=r;}})();
_CSP_SCRIPT_HASH_2 = "'sha256-u9QKVWf5nJ6CpgKA7eHqzt+KvUm6M4dcZhYWRxJuAbA='"

_NOT_FOUND_BODY = (
    b"Route not found. "
    b"The panel exposes / /api/panel-status /api/contexts "
    b"/api/agents /api/agents/<id>/prompt /api/agents/<id>/sessions "
    b"/api/workflows /api/workflows/<name> /api/workflows/<name>/run "
    b"/api/sessions /api/sessions/<runtime>/<session_id> "
    b"/api/kanban "
    b"/health /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>. "
    b"Open / for the index."
)

_WORKFLOW_NAME_RE = re.compile(r"^[a-zA-Z0-9\-]+$")

# ---------------------------------------------------------------------------
# Forbidden field names for T1 privacy check (belt-and-suspenders; the reader
# allowlist is the primary gate — this is defence-in-depth at the handler).
# ---------------------------------------------------------------------------
_FORBIDDEN_JSON_KEYS: frozenset[str] = frozenset(
    ["content", "text", "messages", "snapshot", "thinking", "prompt", "response"]
)

# ---------------------------------------------------------------------------
# Route categories — declare category before adding a new route.
#
# PUBLIC (no auth required):
#   /                              index (full panel HTML)
#   /memory/<slug>/<path>          memory atom HTML
#   /memory-view/<slug>/<path>     memory atom wrapper HTML
#   /static/<name>                 static assets (CSS, JS, SVG)
#
# BEARER-ONLY (Bearer token required; no telemetry dependency; always 200):
#   /api/academy                   academy course list
#   /api/agents/<id>/prompt        agent prompt text
#   /api/reports                   report sidecar list (sorted by date)
#   /api/reports/<path>            delete a report file + its sidecar
#   /api/workflows                 workflow list
#   /api/workflows/<name>          workflow detail + DAG SVG
#
# BEARER + TELEMETRY (Bearer token required; returns 503 when telemetry is None):
#   /api/agents                    canonical agent catalog with telemetry overlay
#   /api/agents/<id>/sessions      per-agent session list
#   /api/contexts                  active Spec Context Projects
#   /api/panel-status              server registry grouped by context
#   /api/sessions                  active sessions across all runtimes
#   /api/sessions/<runtime>/<id>   single session detail
#   /health                        health probe (no auth, agent-friendly)
# ---------------------------------------------------------------------------

# Route patterns: order matters — more-specific patterns first.
_RAW_ROUTES: list[tuple[str, str]] = [
    (r"^/$", "index"),
    (r"^/api/agents/(?P<agent_id>[^/]+)/prompt$", "api_agent_prompt"),
    (r"^/api/agents/(?P<agent_id>[^/]+)/sessions$", "api_agent_sessions"),
    (r"^/api/agents$", "api_agents"),
    # /api/workflows/<name>/run and /api/workflows/<name> before /api/workflows (more specific first).
    (r"^/api/workflows/(?P<workflow_name>[^/]+)/run$", "api_workflow_run"),
    (r"^/api/workflows/(?P<workflow_name>[^/]+)$", "api_workflow_detail"),
    (r"^/api/workflows$", "api_workflows"),
    # /api/sessions/<runtime>/<session_id> must come before /api/sessions (more specific first).
    (r"^/api/sessions/(?P<runtime>[^/]+)/(?P<session_id>[^/]+)$", "api_session_detail"),
    (r"^/api/sessions$", "api_sessions"),
    (r"^/api/panel-status$", "api_panel_status"),
    (r"^/health$", "health"),
    (r"^/api/academy$", "api_academy"),
    # /api/reports/<path> must come before /api/reports$ (more specific first).
    (r"^/api/reports/(?P<path>.+)$", "api_report_delete"),
    (r"^/api/reports$", "api_reports"),
    (r"^/api/contexts$", "api_contexts"),
    (r"^/api/kanban$", "api_kanban"),
    (r"^/memory/(?P<slug>[^/]+)/(?P<path>.+)$", "memory"),
    (r"^/memory-view/(?P<slug>[^/]+)/(?P<path>.+)$", "memory_view"),
    # /reports/<path>: public route — serves HTML report files directly.
    (r"^/reports/(?P<path>.+)$", "reports_serve"),
    (r"^/static/(?P<name>[^/]+)$", "static"),
]

# Routes that require Bearer token auth (all /api/* routes).
_AUTH_REQUIRED_PREFIX = "/api/"

# Routes that require Bearer auth but do NOT need the telemetry service.
# These are dispatched after auth check, bypassing the telemetry-not-configured 503.
_BEARER_ONLY_ROUTES: frozenset[str] = frozenset(
    {
        "api_academy",
        "api_agent_prompt",
        "api_kanban",
        "api_report_delete",
        "api_reports",
        "api_workflows",
        "api_workflow_detail",
        "api_workflow_run",
    }
)

_POST_WORKFLOW_RUN_RE = re.compile(r"^/api/workflows/(?P<workflow_name>[^/]+)/run$")

# Routes that are GET-only and must return 405 Method Not Allowed on POST.
_GET_ONLY_API_ROUTES_RE = re.compile(r"^/api/kanban$")


# ---------------------------------------------------------------------------
# JSON serialisation helper
# ---------------------------------------------------------------------------


def _to_json_bytes(obj: Any) -> bytes:
    """Serialise a dataclass (recursively) to JSON bytes.

    Privacy invariant (T1): strips any key whose name matches a forbidden
    field before encoding.  This is defence-in-depth; the reader allowlist
    is the primary gate.
    """

    def _default(o: Any) -> Any:
        if dataclasses.is_dataclass(o) and not isinstance(o, type):
            d = dataclasses.asdict(o)
            return {k: v for k, v in d.items() if k not in _FORBIDDEN_JSON_KEYS}
        raise TypeError(f"Object of type {type(o)} is not JSON serialisable")

    # Use dataclasses.asdict for the top-level object as well.
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        raw = dataclasses.asdict(obj)
    else:
        raw = obj

    return json.dumps(raw, default=_default).encode("utf-8")


# ---------------------------------------------------------------------------
# Query-string parsing helpers
# ---------------------------------------------------------------------------


def _parse_int(params: dict[str, list[str]], key: str, default: int) -> int:
    vals = params.get(key)
    if vals:
        try:
            return int(vals[0])
        except (ValueError, IndexError):
            pass
    return default


def _parse_str(params: dict[str, list[str]], key: str) -> str | None:
    vals = params.get(key)
    return vals[0] if vals else None


# ---------------------------------------------------------------------------
# make_handler_class
# ---------------------------------------------------------------------------


def make_handler_class(
    views: dict[str, Callable[..., tuple[int, str, bytes]]],
    *,
    token: str | None = None,
    telemetry: Any = None,
    loopback_bypass: bool = False,
) -> type[BaseHTTPRequestHandler]:
    """Return a PanelHandler subclass with *views* and auth/telemetry injected.

    Parameters
    ----------
    views:
        Mapping from route name (str) to a callable that accepts the named
        capture groups from the regex as keyword arguments and returns a
        ``(status_code, content_type, body_bytes)`` triple.

        Required keys: ``"index"``, ``"api_panel_status"``, ``"api_contexts"``,
        ``"api_academy"``, ``"memory"``, ``"memory_view"``, ``"static"``.

    token:
        The expected Bearer token.  When provided, all ``/api/*`` routes
        enforce ``Authorization: Bearer <token>``.  If None, telemetry
        routes return 503 Service Unavailable (auth not configured).

    telemetry:
        A TelemetryService (or compatible stub) instance.  When None,
        telemetry routes return 503 Service Unavailable.

    loopback_bypass:
        When True (set by panel.py when ``bind == "127.0.0.1"``), the Bearer
        token requirement on ``/api/*`` routes is waived.  This allows local
        human and AI-agent clients to call the panel API without supplying an
        Authorization header.  Detection is at the server bind level — NOT
        derived from the client TCP peer address.

        Security note: any local process can read panel data without a token
        when this flag is active — a deliberate dev-local trade-off for a
        read-only GET surface.
    """
    compiled: list[tuple[re.Pattern[str], Callable[..., tuple[int, str, bytes]]]] = [
        (re.compile(pat), views[name]) for pat, name in _RAW_ROUTES if name in views
    ]
    # Telemetry routes are handled inline (not via views dict) because they
    # depend on the injected telemetry service and auth token — not a pure
    # view callable that can be passed in from outside.
    # Exception: "api_agents" may be provided in views (PR3-08 canonical overlay)
    # in which case it is dispatched from views with active_window_days kwarg.
    # Routes that require Bearer auth: telemetry routes + bearer-only (no telemetry needed).
    _BEARER_AUTH_ROUTE_NAMES = (
        "api_academy",
        "api_agents",
        "api_agent_prompt",
        "api_agent_sessions",
        "api_kanban",
        "api_report_delete",
        "api_reports",
        "api_workflows",
        "api_workflow_detail",
        "api_sessions",
        "api_session_detail",
    )
    telemetry_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(pat), name) for pat, name in _RAW_ROUTES if name in _BEARER_AUTH_ROUTE_NAMES
    ]

    _token = token
    _telemetry = telemetry
    _loopback_bypass = loopback_bypass

    if _loopback_bypass:
        import logging as _logging

        _logging.getLogger(__name__).warning(
            "[PANEL] Auth disabled for loopback (127.0.0.1) connections."
        )

    _UNAUTHORIZED_BODY = b'{"error": "unauthorized"}'

    class PanelHandler(BaseHTTPRequestHandler):
        _routes = compiled
        _tel_patterns = telemetry_patterns

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            # ------------------------------------------------------------------
            # Check telemetry routes first (they require Bearer auth).
            # ------------------------------------------------------------------
            for pattern, route_name in self._tel_patterns:
                m = pattern.match(path)
                if m is not None:
                    # Enforce Bearer auth on all /api/* routes unless the server
                    # is bound to loopback (127.0.0.1) with bypass active.
                    auth_header = self.headers.get("Authorization")
                    if not _loopback_bypass and (
                        _token is None or not _validate_bearer(auth_header, _token)
                    ):
                        self._respond(
                            401,
                            "application/json",
                            _UNAUTHORIZED_BODY,
                        )
                        return

                    # Bearer-only routes (e.g. api_agent_prompt) do not require
                    # the telemetry service — dispatch them directly from views.
                    if route_name in _BEARER_ONLY_ROUTES:
                        if route_name in views:
                            self._dispatch_telemetry(route_name, m.groupdict(), qs)
                        else:
                            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)
                        return

                    if _telemetry is None:
                        self._respond(
                            503,
                            "application/json",
                            b'{"error": "telemetry not configured"}',
                        )
                        return

                    # T-AM-21: degraded mode — SQLite was corrupt and quarantined.
                    # Auth is checked first (401 precedes 503 per ordering requirement).
                    if getattr(_telemetry, "is_degraded", False):
                        self._respond(
                            503,
                            "application/json",
                            b'{"error": "telemetry_degraded", "message": "Telemetry database is corrupt and has been quarantined. Restart the panel after investigating ~/.dadaia/state/telemetry/telemetry.sqlite.corrupt.*"}',
                        )
                        return

                    self._dispatch_telemetry(route_name, m.groupdict(), qs)
                    return

            # ------------------------------------------------------------------
            # Existing routes (no auth required in v1 for non-/api/* paths).
            # /api/panel-status and /api/contexts are in views dict — they do NOT
            # require Bearer in v1 to preserve backward compatibility.
            # ------------------------------------------------------------------
            for pattern, view in self._routes:
                m = pattern.match(path)
                if m is not None:
                    status, content_type, body = view(**m.groupdict())
                    is_static = path.startswith("/static/")
                    self._respond(
                        status, content_type, body, cache_control="no-cache" if is_static else None
                    )
                    return

            # 404 fall-through (T-2.3)
            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            for pattern, route_name in self._tel_patterns:
                m = pattern.match(path)
                if m is not None:
                    auth_header = self.headers.get("Authorization")
                    if _token is None or not _validate_bearer(auth_header, _token):
                        self._respond(401, "application/json", _UNAUTHORIZED_BODY)
                        return
                    self._dispatch_telemetry(route_name, m.groupdict(), {})
                    return
            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # Return 405 for GET-only API routes.
            if _GET_ONLY_API_ROUTES_RE.match(path):
                self._respond(
                    405,
                    "application/json",
                    b'{"error": "method not allowed"}',
                )
                return

            m = _POST_WORKFLOW_RUN_RE.match(path)
            if m is not None:
                auth_header = self.headers.get("Authorization")
                if _token is None or not _validate_bearer(auth_header, _token):
                    self._respond(401, "application/json", _UNAUTHORIZED_BODY)
                    return
                workflow_name = m.group("workflow_name")
                if not _WORKFLOW_NAME_RE.match(workflow_name):
                    self._respond(
                        400,
                        "application/json",
                        b'{"error": "invalid workflow name"}',
                    )
                    return
                if "api_workflow_run" in views:
                    try:
                        status, content_type, body = views["api_workflow_run"](
                            workflow_name=workflow_name,
                        )
                        self._respond(status, content_type, body)
                    except Exception as exc:  # noqa: BLE001
                        import logging

                        logging.getLogger(__name__).warning(
                            "PanelHandler: api_workflow_run error: %s", exc
                        )
                        self._respond(
                            500,
                            "application/json",
                            b'{"error": "internal server error"}',
                        )
                else:
                    self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)
                return

            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def _dispatch_telemetry(
            self,
            route_name: str,
            groups: dict[str, str],
            qs: dict[str, list[str]],
        ) -> None:
            """Route to the appropriate telemetry handler method."""
            try:
                if route_name == "api_academy":
                    # T-P5-25: academy course list (bearer-only, no telemetry needed).
                    if "api_academy" in views:
                        status, content_type, body = views["api_academy"]()
                        self._respond(status, content_type, body)
                    else:
                        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

                elif route_name == "api_kanban":
                    # K-1: Kanban board (bearer-only, no telemetry needed).
                    if "api_kanban" in views:
                        status, content_type, body = views["api_kanban"]()
                        self._respond(status, content_type, body)
                    else:
                        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

                elif route_name == "api_reports":
                    # T-P5-29: report sidecar list (bearer-only, no telemetry needed).
                    if "api_reports" in views:
                        status, content_type, body = views["api_reports"]()
                        self._respond(status, content_type, body)
                    else:
                        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

                elif route_name == "api_report_delete":
                    # T-P5-31: delete a report file and its sidecar (bearer-only).
                    path = groups.get("path", "")
                    if "api_report_delete" in views:
                        status, content_type, body = views["api_report_delete"](path=path)
                        self._respond(status, content_type, body)
                    else:
                        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

                elif route_name == "api_agent_prompt":
                    # PR3-09: path-traversal-guarded prompt endpoint.
                    # The view callable performs all validation; handler just forwards.
                    agent_id = groups.get("agent_id", "")
                    status, content_type, body = views["api_agent_prompt"](
                        agent_id=agent_id,
                    )
                    self._respond(status, content_type, body)

                elif route_name == "api_agents":
                    # PR3-08: if the canonical overlay view is provided in views,
                    # delegate to it with active_window_days kwarg.
                    if "api_agents" in views:
                        active_window_days = _parse_int(qs, "active_window_days", 30)
                        status, content_type, body = views["api_agents"](
                            active_window_days=active_window_days,
                        )
                        self._respond(status, content_type, body)
                    else:
                        # Legacy fallback: direct telemetry aggregation (pre-PR3-08).
                        window_days = _parse_int(qs, "window_days", 180)
                        context = _parse_str(qs, "context")
                        limit = _parse_int(qs, "limit", 50)
                        result = _telemetry.list_agents(
                            window_days=window_days,
                            context_slug=context,
                            limit=limit,
                        )
                        body = _to_json_bytes(result)
                        self._respond(200, "application/json", body)

                elif route_name == "api_agent_sessions":
                    agent_id = groups["agent_id"]
                    limit = _parse_int(qs, "limit", 50)
                    offset = _parse_int(qs, "offset", 0)
                    sessions = _telemetry.list_sessions_by_agent(
                        agent_id=agent_id,
                        limit=limit,
                        offset=offset,
                    )
                    # Wrap in {"sessions": [...]} per SPEC contract.
                    payload = {"sessions": [dataclasses.asdict(s) for s in sessions]}
                    body = json.dumps(payload).encode("utf-8")
                    self._respond(200, "application/json", body)

                elif route_name == "api_workflows":
                    # PR3-14: canonical workflow list (bearer-only, no telemetry needed).
                    # Bearer-only dispatch is handled above; this branch is a fallback
                    # for the legacy telemetry path when api_workflows is NOT in views.
                    if "api_workflows" in views:
                        status, content_type, body = views["api_workflows"]()
                        self._respond(status, content_type, body)
                    else:
                        result = _telemetry.list_workflows()
                        body = _to_json_bytes(result)
                        self._respond(200, "application/json", body)

                elif route_name == "api_workflow_detail":
                    # PR3-15: workflow detail endpoint (bearer-only, no telemetry needed).
                    workflow_name = groups.get("workflow_name", "")
                    if "api_workflow_detail" in views:
                        status, content_type, body = views["api_workflow_detail"](
                            workflow_name=workflow_name,
                        )
                        self._respond(status, content_type, body)
                    else:
                        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

                elif route_name == "api_sessions":
                    # PR5-B2: session list endpoint — requires telemetry.
                    if "api_sessions" in views:
                        status, content_type, body = views["api_sessions"](qs=qs)
                        self._respond(status, content_type, body)
                    else:
                        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

                elif route_name == "api_session_detail":
                    # PR5-B2: session detail endpoint — requires telemetry.
                    runtime = groups.get("runtime", "claude")
                    session_id = groups.get("session_id", "")
                    if "api_session_detail" in views:
                        status, content_type, body = views["api_session_detail"](
                            runtime=runtime,
                            session_id=session_id,
                        )
                        self._respond(status, content_type, body)
                    else:
                        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

                else:
                    self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

            except Exception as exc:  # noqa: BLE001
                # Do NOT expose internal details (A06).
                import logging

                logging.getLogger(__name__).warning("PanelHandler: telemetry route error: %s", exc)
                self._respond(
                    500,
                    "application/json",
                    b'{"error": "internal server error"}',
                )

        def _security_headers(self, content_type: str) -> None:
            """Apply CSP for HTML, nosniff for JSON. SPEC § Threat matrix T8."""
            if content_type.startswith("text/html"):
                self.send_header(
                    "Content-Security-Policy",
                    (
                        "default-src 'self'; "
                        f"script-src 'self' {_CSP_SCRIPT_HASH_1} {_CSP_SCRIPT_HASH_2}; "
                        "style-src 'self' 'unsafe-inline'"
                    ),
                )
            if content_type.startswith("application/json"):
                self.send_header("X-Content-Type-Options", "nosniff")

        def _respond(
            self,
            status: int,
            content_type: str,
            body: bytes,
            cache_control: str | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self._security_headers(content_type)
            if cache_control is not None:
                self.send_header("Cache-Control", cache_control)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # suppress access log noise; callers can override

    return PanelHandler
