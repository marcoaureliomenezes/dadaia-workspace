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

import mistune
from mistune import InlineParser, InlineState, Markdown
from mistune.renderers.html import HTMLRenderer

__all__ = ["Markdown", "build_renderer", "render_md_to_html"]

# ---------------------------------------------------------------------------
# Route convention: panel memory viewer wrapper uses /memory-view/<slug>/<file>
# ---------------------------------------------------------------------------
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


def _render_wikilink(renderer: HTMLRenderer, text: str) -> str:  # noqa: ARG001
    """Render a wikilink token as an anchor to the panel memory route."""
    slug = text
    href = f"{_MEMORY_VIEW_PREFIX}/dadaia-workspace/{slug}"
    return f'<a href="{href}">{slug}</a>'


def _wikilink_plugin(md: Markdown) -> None:
    """Register wikilink grammar and renderer into a Markdown instance."""
    md.inline.register(
        "wikilink",
        _WIKILINK_PATTERN,
        _parse_wikilink,
        before="link",
    )
    if md.renderer and md.renderer.NAME == "html":
        md.renderer.register("wikilink", _render_wikilink)


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
# Public factory
# ---------------------------------------------------------------------------


def build_renderer() -> Markdown:
    """Build and return a configured Markdown renderer.

    The renderer instance is stateless and thread-safe for repeated calls.

    Returns
    -------
    Markdown
        A ``mistune.Markdown`` instance with:
        - GFM table support (via mistune table plugin).
        - Mermaid fence → ``<pre class="mermaid">`` passthrough.
        - ``[[wikilink]]`` → panel ``<a>`` anchor.
        - ``escape=True`` so inline/block HTML is entity-escaped by default.
    """
    renderer = _MemoryHTMLRenderer(escape=True)
    return Markdown(
        renderer=renderer,
        plugins=[_wikilink_plugin, mistune.import_plugin("table")],  # type: ignore[attr-defined]
    )


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
