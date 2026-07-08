"""PanelHandler — regex-dispatch HTTP request handler for the panel.

Design (architect D3):
  ROUTES is a compiled ordered list of ``(pattern, view_callable)`` pairs.
  ``do_GET`` walks the list in order; the first match wins.  Named capture
  groups from the regex are passed as keyword arguments to the view callable.

  View callables are injected at handler-class creation time via
  ``make_handler_class(views)``, so this module carries zero rendering logic
  and can be unit-tested with stub views without spinning a real server.

No authentication (operator decision 2026-06-11):
  The panel is a loopback-only (127.0.0.1-bound) local dev tool.  The operator
  ruled out all credentials — no Bearer tokens, no cookies, no launch URLs.
  Every route serves WITHOUT any credential.  The v0.1.11 token/cookie design
  shipped a browser-dead panel and was removed in full.

  The ``AuthClass`` enum and the declarative ``_ROUTE_TABLE`` are retained as
  the route registry shape, but the classes no longer enforce credentials:

      PUBLIC             — served without credential.
      BEARER             — served without credential (legacy classification).
      BEARER_SECOND_LOOP — served without credential (legacy classification).
      BEARER_TELEMETRY   — served without credential, but still returns 503 when
                           the telemetry service is None or degraded.

  The single silent guard that remains is a **Host-header allowlist** (NOT
  authentication, zero UX cost): a request whose ``Host`` header is not one of
  ``127.0.0.1[:port]`` / ``localhost[:port]`` / ``[::1][:port]`` is answered with
  403.  This is DNS-rebinding protection — a browser on the same machine always
  sends a matching ``Host`` when talking to the loopback bind, so it costs the
  legitimate local user nothing.  It applies to every route, including PUBLIC.

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
   /api/sessions
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

# ---------------------------------------------------------------------------
# Host-header allowlist (DNS-rebinding protection — NOT authentication).
#
# The panel binds loopback only.  A browser on the same machine always sends a
# Host header matching the loopback address it connected to.  A request whose
# Host is a foreign name (e.g. an attacker's DNS-rebound domain pointing at
# 127.0.0.1) is answered with 403.  Empty/absent Host is allowed (HTTP/1.0
# clients, curl without --header) — the threat model is a browser tricked into
# sending a foreign Host, which always sets the header.
# ---------------------------------------------------------------------------
_ALLOWED_HOST_NAMES: frozenset[str] = frozenset({"127.0.0.1", "localhost", "[::1]"})


def _is_allowed_host(host_header: str | None) -> bool:
    """Return True iff *host_header* targets the loopback interface.

    Accepts ``127.0.0.1``, ``localhost``, ``[::1]`` with or without a ``:port``
    suffix.  An absent/empty Host header is allowed (non-browser clients).  A
    foreign hostname is rejected (DNS-rebinding guard).
    """
    if not host_header:
        return True
    host = host_header.strip()
    # IPv6 literal with optional port: "[::1]" or "[::1]:4999".
    if host.startswith("["):
        closing = host.find("]")
        if closing == -1:
            return False
        name = host[: closing + 1]
        return name in _ALLOWED_HOST_NAMES
    # IPv4 / hostname with optional port: split on the LAST colon only.
    name = host.rsplit(":", 1)[0] if ":" in host else host
    return name in _ALLOWED_HOST_NAMES


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
#    if(r&&(r==='claude'||r==='codex'||r==='pi')){
#    document.documentElement.dataset.runtime=r;}})();
_CSP_SCRIPT_HASH_2 = "'sha256-rrb6m84iyHOhA+A1XebxK17XtUkbhWfR95KsYvJgmpA='"

_NOT_FOUND_BODY = (
    b"Route not found. "
    b"The panel exposes / /api/panel-status /api/contexts "
    b"/api/agents /api/agents/<id>/prompt /api/agents/<id>/sessions "
    b"/api/workflows /api/workflows/<name> "
    b"/api/sessions "
    b"/health /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>. "
    b"Open / for the index."
)

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
    """Route classification for every registered panel route.

    Retained as the route-registry shape after the no-auth decision
    (2026-06-11).  No class enforces credentials any more; the only residual
    behavioural difference is BEARER_TELEMETRY's 503-when-telemetry-unavailable.

    PUBLIC:
        Served without credential (e.g. index, static assets, health).
    BEARER:
        Served without credential (legacy bearer-only routes).
    BEARER_SECOND_LOOP:
        Served without credential (legacy workspace-sensitive routes — server
        registry, context paths, report/memory content).
    BEARER_TELEMETRY:
        Served without credential, but returns 503 when telemetry is None or
        degraded (e.g. agent sessions, agent list with telemetry overlay).
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
    # Academy lesson render (read-only; path-traversal guard lives in the view/service).
    (
        r"^/academy/(?P<module>[^/]+)/(?P<lesson>[^/]+)$",
        "academy_lesson",
        AuthClass.BEARER_SECOND_LOOP,
    ),
    # BEARER-only routes (auth required; no telemetry dependency)
    (r"^/api/academy$", "api_academy", AuthClass.BEARER),
    (r"^/api/reports$", "api_reports", AuthClass.BEARER),
    # /api/reports/<path>/important must come before /api/reports/<path> (more specific first)
    (r"^/api/reports/(?P<path>.+)/important$", "api_report_mark_important", AuthClass.BEARER),
    (r"^/api/reports/(?P<path>.+)$", "api_report_delete", AuthClass.BEARER),
    (r"^/api/agents/(?P<agent_id>[^/]+)/prompt$", "api_agent_prompt", AuthClass.BEARER),
    # /api/workflows/<name> before /api/workflows
    (
        r"^/api/workflows/(?P<workflow_name>[^/]+)$",
        "api_workflow_detail",
        AuthClass.BEARER,
    ),
    (r"^/api/workflows$", "api_workflows", AuthClass.BEARER),
    # dadaia-workflow catalog (WS-8 / ADR-E): /api/dadaia-workflows/<name> before list
    (
        r"^/api/dadaia-workflows/(?P<workflow_name>[^/]+)$",
        "api_dadaia_workflow_detail",
        AuthClass.BEARER,
    ),
    (r"^/api/dadaia-workflows$", "api_dadaia_workflows", AuthClass.BEARER),
    # Workflow model-governance control plane (Wave C — T-28-C-01/02). The
    # /<id> detail pattern MUST precede the list pattern (more specific first).
    # The static /validate path MUST precede the catch-all policy route.
    (
        r"^/api/workflow-catalog/(?P<workflow_id>[^/]+)$",
        "api_workflow_catalog_detail",
        AuthClass.BEARER,
    ),
    (r"^/api/workflow-catalog$", "api_workflow_catalog", AuthClass.BEARER),
    (r"^/api/workflow-model-profiles$", "api_workflow_model_profiles", AuthClass.BEARER),
    # Read-only fragment inspector (Wave D — T-28-D-01): /<fragment_id> path param.
    (
        r"^/api/workflow-fragments/(?P<fragment_id>[^/]+)$",
        "api_workflow_fragment",
        AuthClass.BEARER,
    ),
    (r"^/api/workflow-model-policy$", "api_workflow_model_policy", AuthClass.BEARER),
    # L1 agent model-governance control plane (v0.1.65 FR8 — T-65-11).
    (r"^/api/agent-model-policy$", "api_agent_model_policy", AuthClass.BEARER),
    (r"^/api/agent-model-templates$", "api_agent_model_templates", AuthClass.BEARER),
    (r"^/api/lifecycle-runs$", "api_lifecycle_runs", AuthClass.BEARER),
    (r"^/api/workflow-step-ledger$", "api_workflow_step_ledger", AuthClass.BEARER),
    # BEARER_TELEMETRY routes (require active telemetry service)
    (
        r"^/api/agents/(?P<agent_id>[^/]+)/sessions$",
        "api_agent_sessions",
        AuthClass.BEARER_TELEMETRY,
    ),
    (r"^/api/agents$", "api_agents", AuthClass.BEARER_TELEMETRY),
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

# Control-plane GET routes (Wave C) that read the parsed query string. Only these
# receive the ``qs`` kwarg in GET dispatch; every other view keeps its captured-groups
# call convention unchanged.
_QS_AWARE_GET_ROUTES: frozenset[str] = frozenset(
    {
        "api_workflow_catalog",
        "api_workflow_catalog_detail",
        "api_workflow_model_policy",
        "api_lifecycle_runs",
        "api_workflow_step_ledger",
    }
)

# Mutation routes (Wave C) dispatched from do_PUT / do_POST with a body. PUT targets the
# policy route; POST targets the validate route. Both read the request body + content
# type and call the view with ``body`` / ``content_type`` / ``qs``.
_PUT_ROUTE_TABLE: list[tuple[str, str]] = [
    (r"^/api/workflow-model-policy$", "api_workflow_model_policy_put"),
    # L1 agent model-governance Apply (v0.1.65 FR8 / G-2 — T-65-11).
    (r"^/api/agent-model-policy$", "api_agent_model_policy_put"),
]
_POST_BODY_ROUTE_TABLE: list[tuple[str, str]] = [
    (r"^/api/workflow-model-policy/validate$", "api_workflow_model_policy_validate"),
    (r"^/api/agent-model-policy/validate$", "api_agent_model_policy_validate"),
]
_COMPILED_PUT_ROUTE_TABLE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat), name) for pat, name in _PUT_ROUTE_TABLE
]
_COMPILED_POST_BODY_ROUTE_TABLE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat), name) for pat, name in _POST_BODY_ROUTE_TABLE
]

#: Max accepted request body for any panel mutation, in bytes. A guard at the handler
#: BEFORE reading the body (defence against an oversized Content-Length). The view also
#: enforces its own 413 limit; this is the outer envelope.
_MAX_MUTATION_BODY_BYTES = 256 * 1024


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
    """Return a PanelHandler subclass with *views* and telemetry injected.

    Parameters
    ----------
    views:
        Mapping from route name (str) to a callable that accepts the named
        capture groups from the regex as keyword arguments and returns a
        ``(status_code, content_type, body_bytes)`` triple.

        Required keys: ``"index"``, ``"api_panel_status"``, ``"api_contexts"``,
        ``"api_academy"``, ``"academy_lesson"``, ``"memory"``, ``"memory_view"``,
        ``"static"``.

    token:
        Deprecated and ignored (no-auth decision, 2026-06-11).  Accepted for
        backward compatibility with existing callers/tests that still pass it;
        no credential is ever validated.

    telemetry:
        A TelemetryService (or compatible stub) instance.  When None,
        BEARER_TELEMETRY routes return 503 Service Unavailable.

    Security note (operator decision, 2026-06-11 — no-auth loopback panel):
        The panel is a loopback-only local dev tool and serves every route
        WITHOUT any credential.  The only residual guard is the Host-header
        allowlist (``_is_allowed_host``): a request whose ``Host`` is a foreign
        name is answered with 403 (DNS-rebinding protection).  A browser on the
        same machine always sends a matching Host, so this costs the legitimate
        local user nothing.
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

    # token is accepted-but-ignored (no-auth decision); bind to _ to mark unused.
    _ = token
    _telemetry = telemetry

    _FORBIDDEN_HOST_BODY = b'{"error": "forbidden host"}'

    # Keep the legacy tel_patterns for _dispatch_telemetry (used for BEARER_TELEMETRY routes).
    _BEARER_AUTH_ROUTE_NAMES = (
        "api_academy",
        "api_agents",
        "api_agent_prompt",
        "api_agent_sessions",
        "api_report_delete",
        "api_report_mark_important",
        "api_report_unmark_important",
        "api_reports",
        "api_workflows",
        "api_workflow_detail",
        "api_dadaia_workflows",
        "api_dadaia_workflow_detail",
        "api_sessions",
    )
    telemetry_patterns: list[tuple[re.Pattern[str], str]] = [
        (re.compile(pat), name) for pat, name in _RAW_ROUTES if name in _BEARER_AUTH_ROUTE_NAMES
    ]

    class PanelHandler(BaseHTTPRequestHandler):
        _compiled_routes = compiled
        _tel_patterns = telemetry_patterns

        def _host_rejected(self) -> bool:
            """403 + True if the Host header is foreign (DNS-rebinding guard).

            Applies to EVERY route, including PUBLIC.  A loopback browser always
            sends a matching Host, so the legitimate local user is never blocked.
            """
            if not _is_allowed_host(self.headers.get("Host")):
                self._respond(403, "application/json", _FORBIDDEN_HOST_BODY)
                return True
            return False

        def do_GET(self) -> None:  # noqa: N802
            if self._host_rejected():
                return
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)

            for pattern, route_name, auth_class, view in self._compiled_routes:
                m = pattern.match(path)
                if m is None:
                    continue

                # No authentication (operator decision 2026-06-11): every route
                # serves without a credential.  The only class with residual
                # behaviour is BEARER_TELEMETRY, which still 503s when telemetry
                # is unavailable or degraded.
                if auth_class == AuthClass.BEARER_TELEMETRY:
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
                    # PUBLIC / BEARER / BEARER_SECOND_LOOP routes dispatched directly from views.
                    if auth_class in (
                        AuthClass.PUBLIC,
                        AuthClass.BEARER,
                        AuthClass.BEARER_SECOND_LOOP,
                    ):
                        # Only the query-string-aware control-plane GET routes
                        # receive ``qs``; existing views keep their call convention
                        # (captured groups only).
                        if route_name in _QS_AWARE_GET_ROUTES:
                            status, content_type, body = view(qs=qs, **m.groupdict())
                        else:
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
            if self._host_rejected():
                return
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            # Use the dedicated DELETE route table (ordering is structural).
            for pattern, route_name in _COMPILED_DELETE_ROUTE_TABLE:
                m = pattern.match(path)
                if m is not None:
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
            if self._host_rejected():
                return
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            for pattern, route_name in self._tel_patterns:
                m_api = pattern.match(path)
                if m_api is None or route_name not in {
                    "api_report_mark_important",
                }:
                    continue
                self._dispatch_telemetry(route_name, m_api.groupdict(), {})
                return

            # Body-reading POST mutation routes (Wave C: policy validate). These are
            # gated by loopback bind + the Host-header allowlist above (NO bearer);
            # the view performs content-type / size / shape / semantic validation.
            qs = urllib.parse.parse_qs(parsed.query)
            for pattern, route_name in _COMPILED_POST_BODY_ROUTE_TABLE:
                if pattern.match(path) is not None:
                    self._dispatch_mutation(route_name, qs)
                    return

            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def do_PUT(self) -> None:  # noqa: N802
            """Body-reading PUT mutation routes (Wave C: policy write).

            Host-guard runs FIRST (same posture as every other method); no bearer.
            The matched view validates content-type (415), size (413), JSON + overlay
            shape + semantic validity (400 with field-path errors) before any atomic
            write, and keeps a ``.last-good.json`` backup (LAW 5).
            """
            if self._host_rejected():
                return
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)
            for pattern, route_name in _COMPILED_PUT_ROUTE_TABLE:
                if pattern.match(path) is not None:
                    self._dispatch_mutation(route_name, qs)
                    return
            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def _read_body(self) -> bytes | None:
            """Read the request body by Content-Length; None when oversized/invalid.

            Returns ``b""`` for a missing/zero Content-Length. Returns ``None`` (and
            does NOT read the socket) when the declared length exceeds the outer
            envelope ``_MAX_MUTATION_BODY_BYTES`` — the caller answers 413 without
            consuming an attacker-controlled stream.
            """
            raw_len = self.headers.get("Content-Length")
            if raw_len is None:
                return b""
            try:
                length = int(raw_len)
            except ValueError:
                return None
            if length < 0 or length > _MAX_MUTATION_BODY_BYTES:
                return None
            return self.rfile.read(length)

        def _dispatch_mutation(self, route_name: str, qs: dict[str, list[str]]) -> None:
            """Read the body + content type and call the mutation view; 404 if unwired."""
            if route_name not in views:
                self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)
                return
            body = self._read_body()
            if body is None:
                self._respond(
                    413,
                    "application/json",
                    b'{"error": "payload_too_large"}',
                )
                return
            content_type = self.headers.get("Content-Type", "")
            try:
                status, ct, resp_body = views[route_name](
                    body=body, content_type=content_type, qs=qs
                )
            except Exception as exc:  # noqa: BLE001
                import logging

                logging.getLogger(__name__).warning("PanelHandler: mutation route error: %s", exc)
                self._respond(500, "application/json", b'{"error": "internal server error"}')
                return
            self._respond(status, ct, resp_body)

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
                    # The api_workflows view is always container-wired (the legacy telemetry
                    # fallback was removed in v0.1.53).
                    status, content_type, body = views["api_workflows"]()
                    self._respond(status, content_type, body)

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
            extra_headers: list[tuple[str, str]] | None = None,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self._security_headers(content_type)
            if cache_control is not None:
                self.send_header("Cache-Control", cache_control)
            if extra_headers is not None:
                for name, value in extra_headers:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # suppress access log noise; callers can override

    return PanelHandler
