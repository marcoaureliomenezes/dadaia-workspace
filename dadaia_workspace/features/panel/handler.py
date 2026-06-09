"""PanelHandler — regex-dispatch HTTP request handler for the panel.

Design (architect D3):
  ROUTES is a compiled ordered list of ``(pattern, view_callable)`` pairs.
  ``do_GET`` walks the list in order; the first match wins.  Named capture
  groups from the regex are passed as keyword arguments to the view callable.

  View callables are injected at handler-class creation time via
  ``make_handler_class(views)``, so this module carries zero rendering logic
  and can be unit-tested with stub views without spinning a real server.

Auth (T-AM-13, T-AM-15, T-016-P05):
  Every registered route carries an explicit ``auth_class`` in the declarative
  ``_ROUTE_TABLE`` constant.  ``auth_class`` is one of:

      PUBLIC             — no auth required.
      BEARER             — Bearer token required; no telemetry dependency.
      BEARER_SECOND_LOOP — Bearer required when NOT on loopback; data is workspace-
                           sensitive but not gated by telemetry.
      BEARER_TELEMETRY   — Bearer required; returns 503 when telemetry is None.

  A route omitted from ``_ROUTE_TABLE`` cannot exist — there is no silent-public
  fallback.  Adding a route without assigning an ``auth_class`` is a
  ``ValueError`` at import time.

  For DELETE, the dedicated ``_DELETE_ROUTE_TABLE`` defines its own ordered
  patterns so that ``/important$`` is matched before the catch-all ``^/api/reports/
  (?P<path>.+)$``.  The ordering is structural (list position) and is tested by
  ``test_handler_route_classification.py``.

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
import enum
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
# Auth class enum (T-016-P05 unified classification)
# ---------------------------------------------------------------------------


class AuthClass(enum.Enum):
    """Auth classification for every registered panel route.

    PUBLIC:
        No auth required (e.g. index, static assets, health).
    BEARER:
        Bearer token required; no telemetry dependency (bearer-only routes).
    BEARER_SECOND_LOOP:
        Bearer required when NOT loopback-bound; returns workspace-sensitive data
        (e.g. server registry, context paths, report/memory content).
    BEARER_TELEMETRY:
        Bearer required; returns 503 when telemetry is None or degraded
        (e.g. agent sessions, agent list with telemetry overlay).
    """

    PUBLIC = "PUBLIC"
    BEARER = "BEARER"
    BEARER_SECOND_LOOP = "BEARER_SECOND_LOOP"
    BEARER_TELEMETRY = "BEARER_TELEMETRY"


# ---------------------------------------------------------------------------
# Declarative route table (T-016-P05).
#
# Each entry is (pattern_str, route_name, auth_class).
# Order matters — more-specific patterns first; the first match wins.
#
# Invariant: every route_name in this table MUST have an explicit AuthClass.
# The make_handler_class factory enforces this at class-creation time.
# ---------------------------------------------------------------------------

_ROUTE_TABLE: list[tuple[str, str, AuthClass]] = [
    # PUBLIC routes
    (r"^/$", "index", AuthClass.PUBLIC),
    (r"^/health$", "health", AuthClass.PUBLIC),
    (r"^/static/(?P<name>[^/]+)$", "static", AuthClass.PUBLIC),
    # BEARER_SECOND_LOOP routes (sensitive data, auth on non-loopback)
    (r"^/api/panel-status$", "api_panel_status", AuthClass.BEARER_SECOND_LOOP),
    (r"^/api/contexts$", "api_contexts", AuthClass.BEARER_SECOND_LOOP),
    (r"^/memory/(?P<slug>[^/]+)/(?P<path>.+)$", "memory", AuthClass.BEARER_SECOND_LOOP),
    (r"^/memory-view/(?P<slug>[^/]+)/(?P<path>.+)$", "memory_view", AuthClass.BEARER_SECOND_LOOP),
    (r"^/reports/(?P<path>.+)$", "reports_serve", AuthClass.BEARER_SECOND_LOOP),
    # BEARER-only routes (auth required; no telemetry dependency)
    (r"^/api/academy$", "api_academy", AuthClass.BEARER),
    (r"^/api/kanban$", "api_kanban", AuthClass.BEARER),
    (r"^/api/reports$", "api_reports", AuthClass.BEARER),
    # /api/reports/<path>/important must come before /api/reports/<path> (more specific first)
    (r"^/api/reports/(?P<path>.+)/important$", "api_report_mark_important", AuthClass.BEARER),
    (r"^/api/reports/(?P<path>.+)$", "api_report_delete", AuthClass.BEARER),
    (r"^/api/agents/(?P<agent_id>[^/]+)/prompt$", "api_agent_prompt", AuthClass.BEARER),
    # /api/workflows/<name>/run and /api/workflows/<name> before /api/workflows
    (r"^/api/workflows/(?P<workflow_name>[^/]+)/run$", "api_workflow_run", AuthClass.BEARER),
    (
        r"^/api/workflows/(?P<workflow_name>[^/]+)$",
        "api_workflow_detail",
        AuthClass.BEARER,
    ),
    (r"^/api/workflows$", "api_workflows", AuthClass.BEARER),
    # BEARER_TELEMETRY routes (require active telemetry service)
    (
        r"^/api/agents/(?P<agent_id>[^/]+)/sessions$",
        "api_agent_sessions",
        AuthClass.BEARER_TELEMETRY,
    ),
    (r"^/api/agents$", "api_agents", AuthClass.BEARER_TELEMETRY),
    # /api/sessions/<runtime>/<session_id> before /api/sessions
    (
        r"^/api/sessions/(?P<runtime>[^/]+)/(?P<session_id>[^/]+)$",
        "api_session_detail",
        AuthClass.BEARER_TELEMETRY,
    ),
    (r"^/api/sessions$", "api_sessions", AuthClass.BEARER_TELEMETRY),
]

# ---------------------------------------------------------------------------
# DELETE route table — ordered separately so that the /important suffix is
# matched before the catch-all path pattern.  Structural ordering (list
# position) is the enforcement mechanism; no runtime sorting is applied.
# ---------------------------------------------------------------------------

_DELETE_ROUTE_TABLE: list[tuple[str, str]] = [
    # MUST come first: DELETE /api/reports/<path>/important → unmark action
    (r"^/api/reports/(?P<path>.+)/important$", "api_report_mark_important"),
    # catch-all: DELETE /api/reports/<path> → delete report file
    (r"^/api/reports/(?P<path>.+)$", "api_report_delete"),
]

# Compile _ROUTE_TABLE patterns once at module load time.
_COMPILED_ROUTE_TABLE: list[tuple[re.Pattern[str], str, AuthClass]] = [
    (re.compile(pat), name, auth) for pat, name, auth in _ROUTE_TABLE
]

# Compile _DELETE_ROUTE_TABLE patterns once at module load time.
_COMPILED_DELETE_ROUTE_TABLE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat), name) for pat, name in _DELETE_ROUTE_TABLE
]

# Convenience sets derived from the single source of truth (_ROUTE_TABLE).
_BEARER_ONLY_ROUTE_NAMES: frozenset[str] = frozenset(
    name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER
)
_SECOND_LOOP_AUTH_ROUTE_NAMES: frozenset[str] = frozenset(
    name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER_SECOND_LOOP
)
_TELEMETRY_ROUTE_NAMES: frozenset[str] = frozenset(
    name for _, name, auth in _ROUTE_TABLE if auth == AuthClass.BEARER_TELEMETRY
)

# Legacy aliases preserved for backward compatibility (external tests may import these).
_BEARER_ONLY_ROUTES = _BEARER_ONLY_ROUTE_NAMES
_SECOND_LOOP_AUTH_ROUTES = _SECOND_LOOP_AUTH_ROUTE_NAMES

# Backward-compatible flat raw routes list (pattern, name) — consumed by some tests.
_RAW_ROUTES: list[tuple[str, str]] = [(pat, name) for pat, name, _ in _ROUTE_TABLE]

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
    # Build compiled route list, filtering only routes whose names are in views
    # OR that are telemetry-dispatched (handled inline, not via views).
    compiled: list[
        tuple[re.Pattern[str], str, AuthClass, Callable[..., tuple[int, str, bytes]] | None]
    ] = []
    for pat, name, auth in _ROUTE_TABLE:
        if name in views:
            compiled.append((re.compile(pat), name, auth, views[name]))
        elif auth in (AuthClass.BEARER_TELEMETRY, AuthClass.BEARER):
            # Telemetry-dispatched routes or bearer routes not in views dict
            # are registered without a view callable — dispatch handles them inline.
            compiled.append((re.compile(pat), name, auth, None))

    _token = token
    _telemetry = telemetry
    _loopback_bypass = loopback_bypass

    if _loopback_bypass:
        import logging as _logging

        _logging.getLogger(__name__).warning(
            "[PANEL] Auth disabled for loopback (127.0.0.1) connections."
        )

    _UNAUTHORIZED_BODY = b'{"error": "unauthorized"}'

    # Keep the legacy tel_patterns for _dispatch_telemetry (used for BEARER_TELEMETRY routes).
    _BEARER_AUTH_ROUTE_NAMES = (
        "api_academy",
        "api_agents",
        "api_agent_prompt",
        "api_agent_sessions",
        "api_kanban",
        "api_report_delete",
        "api_report_mark_important",
        "api_report_unmark_important",
        "api_reports",
        "api_workflows",
        "api_workflow_detail",
        "api_sessions",
        "api_session_detail",
    )
    telemetry_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(pat), name) for pat, name in _RAW_ROUTES if name in _BEARER_AUTH_ROUTE_NAMES
    ]

    class PanelHandler(BaseHTTPRequestHandler):
        _compiled_routes = compiled
        _tel_patterns = telemetry_patterns

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            for pattern, route_name, auth_class, view in self._compiled_routes:
                m = pattern.match(path)
                if m is None:
                    continue

                # Auth enforcement based on auth_class.
                if auth_class == AuthClass.PUBLIC:
                    # No auth required.
                    pass
                elif auth_class == AuthClass.BEARER:
                    # Bearer required; no telemetry dependency.
                    if not _loopback_bypass and (
                        _token is None
                        or not _validate_bearer(self.headers.get("Authorization"), _token)
                    ):
                        self._respond(401, "application/json", _UNAUTHORIZED_BODY)
                        return
                elif auth_class == AuthClass.BEARER_SECOND_LOOP:
                    # Bearer required on non-loopback connections.
                    if not _loopback_bypass and (
                        _token is None
                        or not _validate_bearer(self.headers.get("Authorization"), _token)
                    ):
                        self._respond(401, "application/json", _UNAUTHORIZED_BODY)
                        return
                elif auth_class == AuthClass.BEARER_TELEMETRY:
                    # Bearer required; telemetry must be available.
                    if not _loopback_bypass and (
                        _token is None
                        or not _validate_bearer(self.headers.get("Authorization"), _token)
                    ):
                        self._respond(401, "application/json", _UNAUTHORIZED_BODY)
                        return
                    if _telemetry is None:
                        self._respond(
                            503,
                            "application/json",
                            b'{"error": "telemetry not configured"}',
                        )
                        return
                    # T-AM-21: degraded mode.
                    if getattr(_telemetry, "is_degraded", False):
                        self._respond(
                            503,
                            "application/json",
                            b'{"error": "telemetry_degraded", "message": "Telemetry database is corrupt and has been quarantined. Restart the panel after investigating ~/.dadaia/state/telemetry/telemetry.sqlite.corrupt.*"}',
                        )
                        return

                # Dispatch.
                if view is not None:
                    # BEARER-only or PUBLIC routes dispatched directly from views.
                    if auth_class in (
                        AuthClass.PUBLIC,
                        AuthClass.BEARER,
                        AuthClass.BEARER_SECOND_LOOP,
                    ):
                        status, content_type, body = view(**m.groupdict())
                        is_static = path.startswith("/static/")
                        self._respond(
                            status,
                            content_type,
                            body,
                            cache_control="no-cache" if is_static else None,
                        )
                        return
                    # BEARER_TELEMETRY with view in views dict (e.g. api_agents canonical overlay).
                    self._dispatch_telemetry(route_name, m.groupdict(), qs)
                    return
                else:
                    # Route registered without a view: delegate to telemetry dispatch.
                    self._dispatch_telemetry(route_name, m.groupdict(), qs)
                    return

            # 404 fall-through (T-2.3)
            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            # Use the dedicated DELETE route table (ordering is structural).
            for pattern, route_name in _COMPILED_DELETE_ROUTE_TABLE:
                m = pattern.match(path)
                if m is not None:
                    auth_header = self.headers.get("Authorization")
                    if _token is None or not _validate_bearer(auth_header, _token):
                        self._respond(401, "application/json", _UNAUTHORIZED_BODY)
                        return
                    if route_name == "api_report_mark_important":
                        # DELETE /important → unmark action.
                        if "api_report_unmark_important" in views:
                            status, content_type, body = views["api_report_unmark_important"](
                                path=m.groupdict().get("path", "")
                            )
                            self._respond(status, content_type, body)
                        else:
                            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)
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

            for pattern, route_name in self._tel_patterns:
                m_api = pattern.match(path)
                if m_api is None or route_name not in {
                    "api_report_mark_important",
                }:
                    continue
                auth_header = self.headers.get("Authorization")
                if _token is None or not _validate_bearer(auth_header, _token):
                    self._respond(401, "application/json", _UNAUTHORIZED_BODY)
                    return
                self._dispatch_telemetry(route_name, m_api.groupdict(), {})
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

                elif route_name in {"api_report_mark_important", "api_report_unmark_important"}:
                    path = groups.get("path", "")
                    if route_name in views:
                        status, content_type, body = views[route_name](path=path)
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
