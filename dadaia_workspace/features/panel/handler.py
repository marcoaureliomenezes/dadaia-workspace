"""PanelHandler — regex-dispatch HTTP request handler for the panel.

Design (architect D3):
  ROUTES is a compiled ordered list of ``(pattern, view_callable)`` pairs.
  ``do_GET`` walks the list in order; the first match wins.  Named capture
  groups from the regex are passed as keyword arguments to the view callable.

  View callables are injected at handler-class creation time via
  ``make_handler_class(views)``, so this module carries zero rendering logic
  and can be unit-tested with stub views without spinning a real server.

404 body (T-2.3, constitution error contract — capability + context + next step):
  "Route not found. The panel exposes / /api/servers /api/contexts
   /memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>.
   Open / for the index."
"""

from __future__ import annotations

import re
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler

_NOT_FOUND_BODY = (
    b"Route not found. "
    b"The panel exposes / /api/servers /api/contexts "
    b"/memory/<slug>/<file> /memory-view/<slug>/<file> /static/<name>. "
    b"Open / for the index."
)

# Route patterns: order matters — more-specific patterns first.
_RAW_ROUTES: list[tuple[str, str]] = [
    (r"^/$", "index"),
    (r"^/api/servers$", "api_servers"),
    (r"^/api/contexts$", "api_contexts"),
    (r"^/memory/(?P<slug>[^/]+)/(?P<path>.+)$", "memory"),
    (r"^/memory-view/(?P<slug>[^/]+)/(?P<path>.+)$", "memory_view"),
    (r"^/static/(?P<name>[^/]+)$", "static"),
]


def make_handler_class(
    views: dict[str, Callable[..., tuple[int, str, bytes]]],
) -> type[BaseHTTPRequestHandler]:
    """Return a PanelHandler subclass with *views* injected.

    Parameters
    ----------
    views:
        Mapping from route name (str) to a callable that accepts the named
        capture groups from the regex as keyword arguments and returns a
        ``(status_code, content_type, body_bytes)`` triple.

        Required keys: ``"index"``, ``"api_servers"``, ``"api_contexts"``,
        ``"memory"``, ``"memory_view"``, ``"static"``.
    """
    compiled: list[tuple[re.Pattern[str], Callable[..., tuple[int, str, bytes]]]] = [
        (re.compile(pat), views[name]) for pat, name in _RAW_ROUTES
    ]

    class PanelHandler(BaseHTTPRequestHandler):
        _routes = compiled

        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]  # strip query string
            for pattern, view in self._routes:
                m = pattern.match(path)
                if m is not None:
                    status, content_type, body = view(**m.groupdict())
                    self._respond(status, content_type, body)
                    return
            # 404 fall-through (T-2.3)
            self._respond(404, "text/plain; charset=utf-8", _NOT_FOUND_BODY)

        def _respond(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # suppress access log noise; callers can override

    return PanelHandler
