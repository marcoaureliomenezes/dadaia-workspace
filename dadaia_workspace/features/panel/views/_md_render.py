"""Markdown → HTML renderer for memory atoms (D-1, T-MMS-06).

Design decisions (from SPEC §2.1):

- D-1: renderer = mistune~=3.0 (pure-Python, zero transitive deps).
- Mermaid fences: ```mermaid block → <pre class="mermaid">…</pre>.
  Content is NOT HTML-escaped so the Mermaid JS client can process it.
- [[wikilink]] → <a href="/memory-view/<slug>/<slug>"> anchor linking to
  the panel's memory route convention.
- Sanitiser: strip/escape raw inline <script> and <style> from atom content
  (OWASP A03 / XSS). The mistune HTMLRenderer(escape=True) handles inline
  and block HTML; a post-render regex pass strips any residual <script> /
  <style> tags as defence-in-depth.

Arch note (architect D4.A):
  This module is a pure transformation utility — no I/O, no disk access.
  Callers (views/memory.py) are responsible for reading source and returning
  HTTP responses.
"""

from __future__ import annotations

import re
from collections.abc import Callable

import mistune
from mistune import InlineParser, InlineState, Markdown
from mistune.renderers.html import HTMLRenderer

__all__ = [
    "Markdown",
    "build_renderer",
    "memory_raw_url",
    "memory_view_url",
    "render_md_to_html",
]

# ---------------------------------------------------------------------------
# Canonical memory-URL builder (single source of truth — T-016-P03)
#
# ALL panel code that produces a URL referencing a memory atom MUST use these
# two functions.  Never hardcode extensions or route prefixes outside this
# module.
#
# Route conventions:
#   /memory-view/<slug>/<path>  — wrapper page (back-bar + iframe)
#   /memory/<slug>/<path>       — raw rendered HTML (served by memory.py)
#
# Extension convention: atoms are .md on disk.  Paths are always .md.
# ---------------------------------------------------------------------------


def memory_view_url(slug: str, path: str) -> str:
    """Return the /memory-view/ URL for a memory atom.

    Parameters
    ----------
    slug:
        Spec context project slug (e.g. "dadaia-workspace").
    path:
        Relative path to the atom within ``specs/memory/``, with ``.md``
        extension (e.g. "architecture.md", "product/index.md").

    Returns
    -------
    str
        Absolute path URL: ``/memory-view/<slug>/<path>``.
    """
    return f"/memory-view/{slug}/{path}"


def memory_raw_url(slug: str, path: str) -> str:
    """Return the /memory/ raw URL for a memory atom.

    Parameters
    ----------
    slug:
        Spec context project slug.
    path:
        Relative path to the atom within ``specs/memory/``, with ``.md``
        extension.

    Returns
    -------
    str
        Absolute path URL: ``/memory/<slug>/<path>``.
    """
    return f"/memory/{slug}/{path}"


_MEMORY_VIEW_PREFIX = "/memory-view"

# ---------------------------------------------------------------------------
# Mermaid renderer
# ---------------------------------------------------------------------------


class _MemoryHTMLRenderer(HTMLRenderer):
    """HTMLRenderer with mermaid-fence passthrough.

    Inherits all GFM behaviour (tables, nested lists, etc.) from HTMLRenderer.
    Overrides ``block_code`` to emit ``<pre class="mermaid">`` instead of
    ``<pre><code class="language-mermaid">`` for mermaid fences.
    """

    def block_code(self, code: str, info: str | None = None, **attrs: object) -> str:  # noqa: ARG002
        """Render fenced code blocks.

        Mermaid fences → ``<pre class="mermaid">`` with raw content (not
        HTML-escaped) so the client-side Mermaid JS can process the diagram.
        All other fences → standard escaped ``<pre><code>`` block.
        """
        if info and info.strip().split(None, 1)[0].lower() == "mermaid":
            # Preserve the diagram source verbatim for the Mermaid client.
            # We intentionally do NOT html-escape here — escaping would break
            # arrow operators like --> and ->>.
            return f'<pre class="mermaid">{code}</pre>\n'
        return super().block_code(code, info)


# ---------------------------------------------------------------------------
# Wikilink inline plugin
# ---------------------------------------------------------------------------

# Pattern: [[slug-with-dashes-or-underscores]]
_WIKILINK_PATTERN = r"\[\[[^\]]+\]\]"


def _parse_wikilink(inline: InlineParser, m: re.Match[str], state: InlineState) -> int:
    """Extract slug from [[slug]] and emit a wikilink token."""
    # m.group(0) is the full [[slug]] text (group numbers shift in the
    # combined scanner, so we parse from the full match string).
    raw = m.group(0)
    slug = raw[2:-2].strip()
    state.append_token({"type": "wikilink", "raw": slug})
    return m.end()


def _make_render_wikilink(context_slug: str) -> Callable[[HTMLRenderer, str], str]:
    """Return a wikilink render function that closes over *context_slug*.

    Parameters
    ----------
    context_slug:
        The active Spec Context Project slug.  Every ``[[wikilink]]`` in an
        atom rendered under this context will resolve to
        ``/memory-view/<context_slug>/<link>.md``.
    """

    def _render_wikilink(renderer: HTMLRenderer, text: str) -> str:  # noqa: ARG001
        href = memory_view_url(context_slug, f"{text}.md")
        return f'<a href="{href}">{text}</a>'

    return _render_wikilink


def _make_wikilink_plugin(context_slug: str) -> Callable[[Markdown], None]:
    """Return a wikilink plugin that closes over *context_slug*."""
    render_fn = _make_render_wikilink(context_slug)

    def _wikilink_plugin(md: Markdown) -> None:
        md.inline.register(
            "wikilink",
            _WIKILINK_PATTERN,
            _parse_wikilink,
            before="link",
        )
        if md.renderer and md.renderer.NAME == "html":
            md.renderer.register("wikilink", render_fn)

    return _wikilink_plugin


# ---------------------------------------------------------------------------
# Post-render sanitiser (OWASP A03 — defence-in-depth)
# ---------------------------------------------------------------------------

# Strip <script ...>…</script> and <style ...>…</style> blocks that survive
# rendering (e.g. inside mermaid content or via any renderer gap).
_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)


def _sanitise(text: str) -> str:
    """Strip <script>/<style> blocks (content included) from text.

    Applied to BOTH the raw source (pre-render) and the rendered HTML
    (post-render). Source-side stripping is required because mistune's
    ``escape=True`` only entity-escapes raw HTML — it neutralises execution
    but leaves the inner text in place. Removing the whole block at the source
    guarantees no ``<script>``/``<style>`` content survives in any form.
    """
    text = _SCRIPT_RE.sub("", text)
    text = _STYLE_RE.sub("", text)
    return text


# ---------------------------------------------------------------------------
# Public factory + per-slug cache
# ---------------------------------------------------------------------------

# Cache: slug → Markdown instance.  Renderers are stateless once built so
# sharing across requests is safe.  We cache per slug because each slug has
# its own wikilink closure.
_RENDERER_CACHE: dict[str, Markdown] = {}

_DEFAULT_SLUG = "dadaia-workspace"


def build_renderer(slug: str = _DEFAULT_SLUG) -> Markdown:
    """Build and return a configured Markdown renderer for *slug*.

    Renderers are cached per slug.  Calling ``build_renderer("x")`` twice
    returns the same instance, so the caller can freely call this function on
    every request without paying the construction cost each time.

    Parameters
    ----------
    slug:
        Spec Context Project slug.  Wikilinks in atoms rendered with this
        renderer resolve to ``/memory-view/<slug>/<link>.md``.
        Defaults to ``"dadaia-workspace"`` for backward compatibility.

    Returns
    -------
    Markdown
        A ``mistune.Markdown`` instance with:
        - GFM table support (via mistune table plugin).
        - Mermaid fence → ``<pre class="mermaid">`` passthrough.
        - ``[[wikilink]]`` → panel ``<a>`` anchor for *slug*.
        - ``escape=True`` so inline/block HTML is entity-escaped by default.
    """
    if slug not in _RENDERER_CACHE:
        renderer = _MemoryHTMLRenderer(escape=True)
        _RENDERER_CACHE[slug] = Markdown(
            renderer=renderer,
            plugins=[_make_wikilink_plugin(slug), mistune.import_plugin("table")],  # type: ignore[attr-defined,list-item]
        )
    return _RENDERER_CACHE[slug]


def render_md_to_html(source: str, renderer: Markdown | None = None) -> str:
    """Convert Markdown source to sanitised HTML.

    Parameters
    ----------
    source:
        Raw Markdown text (frontmatter already stripped if present).
    renderer:
        Optional pre-built Markdown instance (for caching / reuse).
        If ``None``, a new instance is built via :func:`build_renderer`.

    Returns
    -------
    str
        Sanitised HTML string ready to serve as ``text/html``.
    """
    md = renderer if renderer is not None else build_renderer()
    raw_html: str = md(_sanitise(source))  # type: ignore[assignment]
    return _sanitise(raw_html)
