"""PanelHandler — table-dispatch HTTP request handler for the panel (K8).

Design:
  ``_ROUTES`` is ONE ordered tuple of ``_Route(method, pattern, view_name,
  requires_telemetry, mutation)``. Each ``do_*`` method walks it for its own
  HTTP method; the first pattern match wins. Named capture groups from the
  regex, plus (for the few routes that need it) the parsed query string, are
  passed to ``views[view_name]``.

  View callables are injected at handler-class creation time via
  ``make_handler_class(views)``, so this module carries zero rendering logic
  and can be unit-tested with stub views without spinning a real server.

  ``PanelHandler`` is a MODULE-LEVEL class (never defined inside a function):
  ``make_handler_class`` builds a per-call subclass via ``type(...)`` binding
  only ``_views``/``_telemetry`` as class attributes. A function-nested class
  statement is what previously made ``make_handler_class`` misread as one
  71-branch function to radon's per-file walk while ruff's C901 (which does
  walk into a nested class) correctly scored it far higher — bug
  ``radon-undercounts-nested-class-in-function-complexity-vs-ruff-c901``. With
  no nested ``class`` statement left, both tools score the same, smaller
  number for ``make_handler_class`` and each ``PanelHandler`` method is scored
  on its own already-small body.

No authentication (operator decision 2026-06-11):
  The panel is a loopback-only (127.0.0.1-bound) local dev tool.  The operator
  ruled out all credentials — no Bearer tokens, no cookies, no launch URLs.
  Every route serves WITHOUT any credential.  The v0.1.11 token/cookie design
  shipped a browser-dead panel and was removed in full; the ``AuthClass``
  route-classification enum that survived that removal as inert metadata is
  now gone too (K8) — the only per-route distinction left is whether it needs
  telemetry (``requires_telemetry``), which still 503s when the service is
  None or degraded.

  The single silent guard that remains is a **Host-header allowlist** (NOT
  authentication, zero UX cost): a request whose ``Host`` header is not one of
  ``127.0.0.1[:port]`` / ``localhost[:port]`` / ``[::1][:port]`` is answered with
  403.  This is DNS-rebinding protection — a browser on the same machine always
  sends a matching ``Host`` when talking to the loopback bind, so it costs the
  legitimate local user nothing.  It applies to every route.

  A route omitted from ``_ROUTES`` cannot exist — there is no silent-public
  fallback. A route present in ``_ROUTES`` but absent from the injected
  ``views`` dict 404s (same contract for every route, no per-name ladder).

Security headers (T-AM-14, T8):
  _security_headers(content_type) — CSP for HTML, nosniff for JSON.

404 body (T-2.3, constitution error contract — updated for T-AM-15):
  "Route not found. The panel exposes / /api/panel-status /api/contexts
   /api/agents /api/agents/<id>/sessions
   /api/sessions
   /health /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>.
   Open / for the index."
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
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
#    if(r&&(r==='claude'||r==='codex'||r==='kimi-code')){
#    document.documentElement.dataset.runtime=r;}})();
_CSP_SCRIPT_HASH_2 = "'sha256-RSFA3aRvQBf2fCuuTX2WgBq5hIbpATPJs4WDnw3YeNw='"

_NOT_FOUND_BODY = (
    b"Route not found. "
    b"The panel exposes / /api/panel-status /api/contexts "
    b"/api/agents /api/agents/<id>/prompt /api/agents/<id>/sessions "
    b"/api/sessions "
    b"/health /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>. "
    b"Open / for the index."
)

_FORBIDDEN_HOST_BODY = b'{"error": "forbidden host"}'
_TELEMETRY_UNCONFIGURED_BODY = b'{"error": "telemetry not configured"}'
_TELEMETRY_DEGRADED_BODY = (
    b'{"error": "telemetry_degraded", "message": "Telemetry database is corrupt '
    b"and has been quarantined. Restart the panel after investigating "
    b'~/.dadaia/state/telemetry/telemetry.sqlite.corrupt.*"}'
)

#: Max accepted request body for any panel mutation, in bytes. A guard at the handler
#: BEFORE reading the body (defence against an oversized Content-Length). The view also
#: enforces its own 413 limit; this is the outer envelope.
_MAX_MUTATION_BODY_BYTES = 256 * 1024


# ---------------------------------------------------------------------------
# The route table — the single source of truth for every method/pattern/view.
# Order matters within a method — more-specific patterns first, first match wins.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Route:
    method: str
    pattern: re.Pattern[str]
    view_name: str
    requires_telemetry: bool = False
    mutation: bool = False


def _r(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


_ROUTES: tuple[_Route, ...] = (
    # --- GET ---
    _Route("GET", _r(r"^/$"), "index"),
    _Route("GET", _r(r"^/health$"), "health"),
    _Route("GET", _r(r"^/static/(?P<name>[^/]+)$"), "static"),
    _Route("GET", _r(r"^/api/panel-status$"), "api_panel_status"),
    _Route("GET", _r(r"^/api/contexts$"), "api_contexts"),
    _Route("GET", _r(r"^/memory/(?P<slug>[^/]+)/(?P<path>.+)$"), "memory"),
    _Route("GET", _r(r"^/memory-view/(?P<slug>[^/]+)/(?P<path>.+)$"), "memory_view"),
    _Route("GET", _r(r"^/api/agents/(?P<agent_id>[^/]+)/prompt$"), "api_agent_prompt"),
    # L1 agent model-governance control plane (v0.1.65 FR8 — T-65-11).
    _Route("GET", _r(r"^/api/agent-model-policy$"), "api_agent_model_policy"),
    _Route("GET", _r(r"^/api/agent-model-templates$"), "api_agent_model_templates"),
    # Telemetry-backed routes.
    _Route(
        "GET",
        _r(r"^/api/agents/(?P<agent_id>[^/]+)/sessions$"),
        "api_agent_sessions",
        requires_telemetry=True,
    ),
    _Route("GET", _r(r"^/api/agents$"), "api_agents", requires_telemetry=True),
    _Route("GET", _r(r"^/api/sessions$"), "api_sessions", requires_telemetry=True),
    # --- POST --- (body: mutation validate)
    _Route(
        "POST",
        _r(r"^/api/agent-model-policy/validate$"),
        "api_agent_model_policy_validate",
        mutation=True,
    ),
    # --- PUT --- (body: policy write, Wave C / T-65-11)
    _Route("PUT", _r(r"^/api/agent-model-policy$"), "api_agent_model_policy_put", mutation=True),
)

#: Routes whose view wants the raw parsed query string forwarded as ``qs=``.
_QS_FORWARDING_VIEWS: frozenset[str] = frozenset({"api_sessions", "api_agent_sessions"})


def _parse_int(params: dict[str, list[str]], key: str, default: int) -> int:
    vals = params.get(key)
    if vals:
        try:
            return int(vals[0])
        except (ValueError, IndexError):
            pass
    return default


def _extra_view_kwargs(view_name: str, qs: dict[str, list[str]]) -> dict[str, Any]:
    """Per-view extra kwargs beyond the regex's named groups.

    Almost every view needs only its named groups; the two exceptions above
    forward the raw ``qs``, and ``api_agents`` pre-parses ``active_window_days``
    (its own validated [1, 365] int) the same way the handler always has.
    """
    if view_name in _QS_FORWARDING_VIEWS:
        return {"qs": qs}
    if view_name == "api_agents":
        return {
            "active_window_days": _parse_int(qs, "active_window_days", 30),
            "window_days": _parse_int(qs, "window_days", 180),
        }
    return {}


# ---------------------------------------------------------------------------
# PanelHandler — MODULE-LEVEL (never nested inside a function; see the module
# docstring for why that matters for the mccabe/radon ratchet).
# ---------------------------------------------------------------------------


class PanelHandler(BaseHTTPRequestHandler):
    """Regex-table-dispatch request handler. Views/telemetry are bound as
    class attributes by ``make_handler_class`` via ``type(...)`` — never by a
    nested ``class`` statement."""

    _views: dict[str, Callable[..., tuple[int, str, bytes]]] = {}
    _telemetry: Any = None

    def _host_rejected(self) -> bool:
        """403 + True if the Host header is foreign (DNS-rebinding guard).

        Applies to EVERY route.  A loopback browser always sends a matching
        Host, so the legitimate local user is never blocked.
        """
        if not _is_allowed_host(self.headers.get("Host")):
            self._respond(403, "application/json", _FORBIDDEN_HOST_BODY)
            return True
        return False

    def _dispatch(self, method: str, path: str, qs: dict[str, list[str]]) -> None:
        for route in _ROUTES:
            if route.method != method:
                continue
            m = route.pattern.match(path)
            if m is None:
                continue

            if route.requires_telemetry:
                if self._telemetry is None:
                    self._respond(503, "application/json", _TELEMETRY_UNCONFIGURED_BODY)
                    return
                # T-AM-21: degraded mode.
                if getattr(self._telemetry, "is_degraded", False):
                    self._respond(503, "application/json", _TELEMETRY_DEGRADED_BODY)
                    return

            if route.mutation:
                self._dispatch_mutation(route.view_name, qs)
                return
            self._dispatch_view(route.view_name, m.groupdict(), qs)
            return

        # 404 fall-through (T-2.3)
        self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

    def _dispatch_view(
        self, view_name: str, groups: dict[str, str], qs: dict[str, list[str]]
    ) -> None:
        """Call ``views[view_name](**groups, **extra)``; 404 if unwired."""
        if view_name not in self._views:
            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)
            return
        kwargs: dict[str, Any] = dict(groups)
        kwargs.update(_extra_view_kwargs(view_name, qs))
        status, content_type, body = self._views[view_name](**kwargs)
        cache_control = "no-cache" if view_name == "static" else None
        self._respond(status, content_type, body, cache_control=cache_control)

    def do_GET(self) -> None:  # noqa: N802
        if self._host_rejected():
            return
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        self._dispatch("GET", parsed.path, qs)

    def do_POST(self) -> None:  # noqa: N802
        if self._host_rejected():
            return
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        self._dispatch("POST", parsed.path, qs)

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
        qs = urllib.parse.parse_qs(parsed.query)
        self._dispatch("PUT", parsed.path, qs)

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
        if route_name not in self._views:
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
            status, ct, resp_body = self._views[route_name](
                body=body, content_type=content_type, qs=qs
            )
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning("PanelHandler: mutation route error: %s", exc)
            self._respond(500, "application/json", b'{"error": "internal server error"}')
            return
        self._respond(status, ct, resp_body)

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


def make_handler_class(
    views: dict[str, Callable[..., tuple[int, str, bytes]]],
    *,
    token: str | None = None,
    telemetry: Any = None,
) -> type[BaseHTTPRequestHandler]:
    """Return a ``PanelHandler`` subclass with *views* and telemetry bound.

    Parameters
    ----------
    views:
        Mapping from route name (str) to a callable that accepts the named
        capture groups from the regex (plus, for a couple of routes, ``qs=``
        or ``active_window_days=``) as keyword arguments and returns a
        ``(status_code, content_type, body_bytes)`` triple. A route present in
        ``_ROUTES`` but absent here 404s.

    token:
        Deprecated and ignored (no-auth decision, 2026-06-11).  Accepted for
        backward compatibility with existing callers/tests that still pass it;
        no credential is ever validated.

    telemetry:
        A TelemetryService (or compatible stub) instance.  When None,
        ``requires_telemetry`` routes return 503 Service Unavailable.

    Security note (operator decision, 2026-06-11 — no-auth loopback panel):
        The panel is a loopback-only local dev tool and serves every route
        WITHOUT any credential.  The only residual guard is the Host-header
        allowlist (``_is_allowed_host``): a request whose ``Host`` is a foreign
        name is answered with 403 (DNS-rebinding protection).
    """
    _ = token  # accepted-but-ignored (no-auth decision)
    # A type() call, not a nested `class` statement — see module docstring.
    return type("PanelHandler", (PanelHandler,), {"_views": views, "_telemetry": telemetry})
