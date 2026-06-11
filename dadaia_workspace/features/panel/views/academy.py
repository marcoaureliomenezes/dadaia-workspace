"""Academy tab scaffold + lesson-serving view.

``render_academy_section`` returns the static HTML scaffold for the Academy tab.
``render_academy_lesson`` serves a single knowledge_basis lesson, rendered from its
``.md`` source to HTML in-memory.

Security (OWASP A03):
  ``render_academy_section`` returns a static HTML scaffold only — no academy data is
  serialised server-side into it; all dynamic content is loaded client-side by
  academy.js after the auth handshake.

  ``render_academy_lesson`` is READ-ONLY and path-traversal-guarded. The actual
  resolve + ``is_relative_to`` guard lives in
  ``AcademyService.read_lesson`` (mirrors ``views/memory.py``): the resolved target
  must be a regular ``.md`` file located exactly one level below the knowledge_basis
  root. Any escaping / non-``.md`` / non-file path yields 404 with no information
  disclosure.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from dadaia_workspace.features.panel.views._md_render import (
    build_renderer,
    render_md_to_html,
)

_log = logging.getLogger(__name__)

_NOT_FOUND: tuple[int, str, bytes] = (
    404,
    "text/plain; charset=utf-8",
    b"Not found.",
)


def render_academy_section() -> str:
    """Return the static HTML scaffold for the Academy section.

    academy.js fetches /api/academy on tab activation and populates
    #academy-content with module cards. The server never serialises
    course records into this HTML.
    """
    return (
        '<section id="section-academy" class="section" aria-label="Academy modules"\n'
        '         role="tabpanel" tabindex="0" aria-labelledby="tab-academy">\n'
        '  <div class="section-header">\n'
        "    <h2>Academy</h2>\n"
        "    <p>Course modules and learning resources for the workspace.</p>\n"
        "  </div>\n"
        '  <div id="academy-content">\n'
        '    <div class="empty-state">Loading academy modules...</div>\n'
        "  </div>\n"
        "</section>"
    )


def _memory_doc_css_link() -> str:
    """Return a stylesheet ``<link>`` for ``/static/memory-doc.css`` iff it exists.

    Another agent owns the document stylesheet this wave. If the asset has been
    registered (key present in the static asset map) we link it so lessons inherit
    the workspace visual identity; otherwise we emit no link and the lesson renders
    plain. This avoids a hard dependency on an asset that may not exist yet.
    """
    try:
        from dadaia_workspace.features.panel.views.static import _ASSETS

        if "memory-doc.css" in _ASSETS:
            return '<link rel="stylesheet" href="/static/memory-doc.css">'
    except Exception:  # pragma: no cover - defensive: never break a lesson render
        _log.debug("memory-doc.css presence check failed", exc_info=True)
    return ""


def render_academy_lesson(
    service: Any,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return ``GET /academy/<module>/<lesson>`` view — render a lesson to HTML.

    The lesson Markdown is read from the shipped ``knowledge_basis`` content via
    ``service.read_lesson(module, lesson)`` (read-only, path-traversal-guarded there)
    and rendered to HTML in-memory using the same ``_md_render`` seam as memory atoms.
    The rendered body is wrapped in a minimal document that links
    ``/static/memory-doc.css`` when that asset exists, so the lesson inherits the
    workspace visual identity.

    Returns 404 (no information disclosure) when the academy service is unavailable
    or the lesson is missing / out of bounds.
    """

    def _view(module: str = "", lesson: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        if service is None:
            return _NOT_FOUND
        try:
            source = service.read_lesson(module, lesson)
        except Exception:
            _log.exception("Failed to read academy lesson: %s/%s", module, lesson)
            return _NOT_FOUND
        if source is None:
            return _NOT_FOUND
        try:
            renderer = build_renderer()
            body_html = render_md_to_html(source, renderer=renderer)
        except Exception:
            _log.exception("Failed to render academy lesson: %s/%s", module, lesson)
            return _NOT_FOUND

        css_link = _memory_doc_css_link()
        document = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f"{css_link}\n"
            '</head>\n<body class="memory-doc">\n'
            f"{body_html}\n"
            "</body>\n</html>"
        )
        return (200, "text/html; charset=utf-8", document.encode("utf-8"))

    return _view
