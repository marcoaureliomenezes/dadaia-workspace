"""Memory view — serves memory atoms rendered from .md source (D-4, T-MMS-06).

Design decisions (SPEC memory-markdown-source-v1 §2.1):

D-4 (in-memory render):
  The view reads the ``.md`` source file, renders it to HTML via mistune (D-1),
  sanitises the output, and returns the rendered bytes.  No ``.html`` is written
  to disk.  The 21 committed ``.html`` atoms are retired in W4 (T-MMS-10).

SPEC-DOC-008 byte-identity invariant:
  This invariant applied to committed ``.html`` files.  It is now **retired** —
  the ``.md`` source is the canonical artefact, and served HTML is ephemeral
  (rendered in-memory).  The canary tests for byte-identity are replaced by
  Markdown render tests in test_views_memory.py.

Path traversal guard (OWASP A03):
  After resolving the absolute path with ``Path.resolve()``, we assert that the
  resolved path is relative to the memory root (``repos/<slug>/specs/memory/``).
  Any path that escapes the root returns 404 (no information disclosure).
  This guard covers both ``.md`` and all other file types.

Non-Markdown files (assets):
  For any file that is NOT a ``.md`` file the view falls back to serving bytes
  verbatim (same behaviour as before for images, CSS, JS assets).  Content-type
  is sniffed from file extension.

Arch note (architect D4.A):
  This module reads disk files directly (no domain service abstraction) as an
  intentional HTTP-layer concern.  The operation is read-only; the path guard
  is the adequate security boundary.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from dadaia_workspace.features.panel.views._md_render import (
    build_renderer,
    render_md_to_html,
)

_log = logging.getLogger(__name__)

# Content-type map keyed by file suffix (lower-case, dot included).
_CONTENT_TYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".md": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}

_NOT_FOUND: tuple[int, str, bytes] = (
    404,
    "text/plain; charset=utf-8",
    b"Not found.",
)


def render_memory(
    workspace_root: Path,
) -> Callable[..., tuple[int, str, bytes]]:
    """Return a closure that serves memory atoms.

    For ``.md`` files, the Markdown source is rendered to HTML in-memory
    (D-4) and returned as ``text/html``.  All other file types are served
    verbatim (byte-identical) with the appropriate content-type.

    Parameters
    ----------
    workspace_root:
        Absolute path to the dadaia workspace root directory.
        Memory files are resolved under ``<workspace_root>/repos/<slug>/specs/memory/``.
    """

    def _view(slug: str = "", path: str = "", **_kwargs: object) -> tuple[int, str, bytes]:
        """Serve a memory atom.

        ``.md`` files are rendered to HTML in-memory (D-4).
        All other files are served verbatim (byte-identical).

        The Markdown renderer is fetched from the per-slug cache (T-016-P04),
        so wikilinks resolve to the correct context slug, not the hardcoded
        ``"dadaia-workspace"`` default.
        """
        memory_root = (workspace_root / "repos" / slug / "specs" / "memory").resolve()
        if path == "constitution.md":
            # Explicit single-file allowlist (operator: the constitution is the
            # main file of a project): `constitution.md` lives one level ABOVE
            # the memory root, at repos/<slug>/specs/constitution.md. Only this
            # literal path is re-rooted — everything else under specs/
            # (releases/, bugs/, _archive/, ...) stays unreachable.
            target = (workspace_root / "repos" / slug / "specs" / "constitution.md").resolve()
            specs_root = (workspace_root / "repos" / slug / "specs").resolve()
            if target.parent != specs_root:
                return _NOT_FOUND
        else:
            target = (memory_root / path).resolve()

            # Path traversal guard (OWASP A03)
            if not target.is_relative_to(memory_root):
                return _NOT_FOUND

        if not target.exists() or not target.is_file():
            return _NOT_FOUND

        suffix = target.suffix.lower()
        content_type = _CONTENT_TYPES.get(suffix, "application/octet-stream")

        if suffix == ".md":
            # D-4: render Markdown to HTML in-memory; never write HTML to disk.
            # Use the per-slug renderer so wikilinks resolve to the active context.
            try:
                source = target.read_text(encoding="utf-8")
                renderer = build_renderer(slug)
                html_str = render_md_to_html(source, renderer=renderer)
                return (200, "text/html; charset=utf-8", html_str.encode("utf-8"))
            except Exception:
                _log.exception("Failed to render memory atom: %s", target)
                return _NOT_FOUND

        # Non-Markdown assets: serve verbatim (images, CSS, JS, legacy .html).
        data = target.read_bytes()
        return (200, content_type, data)

    return _view
