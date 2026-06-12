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

import html as _html
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from dadaia_workspace.features.panel.views._md_render import (
    build_renderer,
    render_md_to_html,
)

_log = logging.getLogger(__name__)

# YAML frontmatter delimited by leading `---` ... `---`.
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<fm>.*?)\n---\s*\n?", re.DOTALL)

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


def _split_frontmatter(source: str) -> tuple[dict[str, Any], str]:
    """Split a leading YAML frontmatter block from Markdown source.

    Returns ``(metadata, body)``.  When no frontmatter is present, returns
    ``({}, source)``.  A malformed YAML block is treated as no frontmatter and
    left in the body (never raised) so a bad atom still renders.
    """
    match = _FRONTMATTER_RE.match(source)
    if match is None:
        return {}, source
    try:
        loaded = yaml.safe_load(match.group("fm"))
    except yaml.YAMLError:
        return {}, source
    meta = loaded if isinstance(loaded, dict) else {}
    body = source[match.end() :]
    return meta, body


def _render_meta_header(meta: dict[str, Any]) -> str:
    """Render the frontmatter as a compact styled meta header (no raw YAML soup).

    Surfaces ``title``, ``tldr``, ``tags`` (as chips) and ``last_updated``.
    All values are HTML-escaped (OWASP A03).  Returns ``""`` when there is
    nothing worth showing.
    """
    title = meta.get("title") or meta.get("slug")
    tldr = meta.get("tldr")
    tags = meta.get("tags")
    last_updated = meta.get("last_updated")

    if not any((title, tldr, tags, last_updated)):
        return ""

    parts: list[str] = ['<header class="memory-meta">']
    if title:
        parts.append(f'<h1 class="memory-meta__title">{_html.escape(str(title))}</h1>')
    if tldr:
        parts.append(f'<p class="memory-meta__tldr">{_html.escape(str(tldr))}</p>')
    if isinstance(tags, list) and tags:
        chips = "".join(
            f'<li class="memory-meta__chip">{_html.escape(str(tag))}</li>' for tag in tags
        )
        parts.append(f'<ul class="memory-meta__tags">{chips}</ul>')
    if last_updated:
        parts.append(
            f'<p class="memory-meta__footer">Last updated: {_html.escape(str(last_updated))}</p>'
        )
    parts.append("</header>")
    return "".join(parts)


# Theme pre-paint: apply the stored panel theme before first contentful paint
# so a memory document opened standalone matches the panel's active theme.
_THEME_PREPAINT = (
    "<script>(function(){var t=localStorage.getItem('dadaia-panel-theme');"
    "if(t&&(t==='mint'||t==='sage'||t==='warm')){document.documentElement.dataset.theme=t;}})();</script>"
)


def _wrap_document(title: str, meta_header: str, body_html: str) -> str:
    """Wrap rendered memory body in a full HTML document carrying the identity.

    Links ``/static/tokens.css`` (palette + theme) and ``/static/memory-doc.css``
    (document typography/tables/code) into ``<head>`` so the rendered memory
    document carries the dadaia visual identity whether viewed standalone or
    inside the wrapper iframe.
    """
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_html.escape(title)}</title>\n"
        f"{_THEME_PREPAINT}\n"
        '<link rel="stylesheet" href="/static/tokens.css">\n'
        '<link rel="stylesheet" href="/static/memory-doc.css">\n'
        "</head>\n<body>\n"
        '<main class="memory-doc">\n'
        f"{meta_header}{body_html}"
        "\n</main>\n</body>\n</html>\n"
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
                # Strip YAML frontmatter so it never renders as raw key:value
                # soup; surface it as a styled compact meta header instead.
                meta, md_body = _split_frontmatter(source)
                renderer = build_renderer(slug)
                body_html = render_md_to_html(md_body, renderer=renderer)
                meta_header = _render_meta_header(meta)
                doc_title = str(meta.get("title") or meta.get("slug") or target.stem)
                document = _wrap_document(doc_title, meta_header, body_html)
                return (200, "text/html; charset=utf-8", document.encode("utf-8"))
            except Exception:
                _log.exception("Failed to render memory atom: %s", target)
                return _NOT_FOUND

        # Non-Markdown assets: serve verbatim (images, CSS, JS, legacy .html).
        data = target.read_bytes()
        return (200, content_type, data)

    return _view
