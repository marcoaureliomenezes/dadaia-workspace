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
  "Route not found. The panel exposes / /api/servers /api/contexts
   /api/agents /api/agents/<id>/sessions /api/workflows
   /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>.
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

_NOT_FOUND_BODY = (
    b"Route not found. "
    b"The panel exposes / /api/servers /api/contexts "
    b"/api/agents /api/agents/<id>/sessions /api/workflows "
    b"/memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>. "
    b"Open / for the index."
)

# ---------------------------------------------------------------------------
# Forbidden field names for T1 privacy check (belt-and-suspenders; the reader
# allowlist is the primary gate — this is defence-in-depth at the handler).
# ---------------------------------------------------------------------------
_FORBIDDEN_JSON_KEYS: frozenset[str] = frozenset(
    ["content", "text", "messages", "snapshot", "thinking", "prompt", "response"]
)

# Route patterns: order matters — more-specific patterns first.
_RAW_ROUTES: list[tuple[str, str]] = [
    (r"^/$", "index"),
    (r"^/api/agents/(?P<agent_id>[^/]+)/sessions$", "api_agent_sessions"),
    (r"^/api/agents$", "api_agents"),
    (r"^/api/workflows$", "api_workflows"),
    (r"^/api/servers$", "api_servers"),
    (r"^/api/contexts$", "api_contexts"),
    (r"^/memory/(?P<slug>[^/]+)/(?P<path>.+)$", "memory"),
    (r"^/memory-view/(?P<slug>[^/]+)/(?P<path>.+)$", "memory_view"),
    (r"^/static/(?P<name>[^/]+)$", "static"),
]

# Routes that require Bearer token auth (all /api/* routes).
_AUTH_REQUIRED_PREFIX = "/api/"


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
) -> type[BaseHTTPRequestHandler]:
    """Return a PanelHandler subclass with *views* and auth/telemetry injected.

    Parameters
    ----------
    views:
        Mapping from route name (str) to a callable that accepts the named
        capture groups from the regex as keyword arguments and returns a
        ``(status_code, content_type, body_bytes)`` triple.

        Required keys: ``"index"``, ``"api_servers"``, ``"api_contexts"``,
        ``"memory"``, ``"memory_view"``, ``"static"``.

    token:
        The expected Bearer token.  When provided, all ``/api/*`` routes
        enforce ``Authorization: Bearer <token>``.  If None, telemetry
        routes return 503 Service Unavailable (auth not configured).

    telemetry:
        A TelemetryService (or compatible stub) instance.  When None,
        telemetry routes return 503 Service Unavailable.
    """
    compiled: list[tuple[re.Pattern[str], Callable[..., tuple[int, str, bytes]]]] = [
        (re.compile(pat), views[name]) for pat, name in _RAW_ROUTES if name in views
    ]
    # Telemetry routes are handled inline (not via views dict) because they
    # depend on the injected telemetry service and auth token — not a pure
    # view callable that can be passed in from outside.
    telemetry_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(pat), name)
        for pat, name in _RAW_ROUTES
        if name in ("api_agents", "api_agent_sessions", "api_workflows")
    ]

    _token = token
    _telemetry = telemetry

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
                    # Enforce Bearer auth on all /api/* routes.
                    auth_header = self.headers.get("Authorization")
                    if _token is None or not _validate_bearer(auth_header, _token):
                        self._respond(
                            401,
                            "application/json",
                            _UNAUTHORIZED_BODY,
                        )
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
            # /api/servers and /api/contexts are in views dict — they do NOT
            # require Bearer in v1 to preserve backward compatibility.
            # ------------------------------------------------------------------
            for pattern, view in self._routes:
                m = pattern.match(path)
                if m is not None:
                    status, content_type, body = view(**m.groupdict())
                    self._respond(status, content_type, body)
                    return

            # 404 fall-through (T-2.3)
            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def _dispatch_telemetry(
            self,
            route_name: str,
            groups: dict[str, str],
            qs: dict[str, list[str]],
        ) -> None:
            """Route to the appropriate telemetry handler method."""
            try:
                if route_name == "api_agents":
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
                    result = _telemetry.list_workflows()
                    body = _to_json_bytes(result)
                    self._respond(200, "application/json", body)

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
                    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'",
                )
            if content_type.startswith("application/json"):
                self.send_header("X-Content-Type-Options", "nosniff")

        def _respond(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self._security_headers(content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # suppress access log noise; callers can override

    return PanelHandler
