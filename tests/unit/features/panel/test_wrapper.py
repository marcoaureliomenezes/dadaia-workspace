"""Unit tests for views/wrapper.py — T-3.10 / T-PUX-03.

Covers:
  - Back-bar "Voltar ao Painel" link present with href "/"
  - iframe src points at /memory/<slug>/<file>
  - slug and path are HTML-escaped (R3-A / OWASP A03)
  - Returns (200, "text/html; charset=utf-8", bytes)
  - PR3-05: no hard-coded palette hex literals; var(--color-*) tokens used;
    tokens.css linked; pre-paint theme script present (theme follows active theme)
  - T-PUX-03: memory.css linked so iframe host page uses panel visual identity
"""

from pathlib import Path

from dadaia_workspace.features.panel.views.wrapper import render_memory_wrapper


def _render(slug: str, path: str) -> str:
    workspace_root = Path("/workspace")
    view = render_memory_wrapper(workspace_root)
    status, content_type, body = view(slug=slug, path=path)
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    return body.decode("utf-8")


def test_wrapper_back_link_present() -> None:
    """Back-bar must contain 'Voltar ao Painel' text."""
    html = _render("dadaia-workspace", "architecture.html")
    assert "Voltar ao Painel" in html


def test_wrapper_back_link_href_root() -> None:
    """Back link href must be '/'."""
    html = _render("dadaia-workspace", "architecture.html")
    assert 'href="/"' in html


def test_wrapper_iframe_src() -> None:
    """iframe src must be /memory/<slug>/<path>."""
    html = _render("dadaia-workspace", "architecture.html")
    assert 'src="/memory/dadaia-workspace/architecture.html"' in html


def test_wrapper_iframe_nested_path() -> None:
    """iframe src must work for nested paths like product/index.html."""
    html = _render("dadaia-workspace", "product/index.html")
    assert 'src="/memory/dadaia-workspace/product/index.html"' in html


def test_wrapper_slug_escaped() -> None:
    """R3-A: slug with special HTML chars must be escaped in output."""
    html = _render("<script>alert(1)</script>", "file.html")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_wrapper_path_escaped() -> None:
    """R3-A: path with special HTML chars must be escaped in output."""
    html = _render("safe-slug", "<img src=x onerror=alert(1)>.html")
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img" in html


def test_wrapper_returns_correct_tuple() -> None:
    """View must return (int, str, bytes) triple."""
    view = render_memory_wrapper(Path("/workspace"))
    result = view(slug="s", path="f.html")
    assert isinstance(result, tuple)
    assert len(result) == 3
    status, ct, body = result
    assert isinstance(status, int)
    assert isinstance(ct, str)
    assert isinstance(body, bytes)


def test_wrapper_contains_iframe_tag() -> None:
    """HTML must contain an iframe element."""
    html = _render("slug", "path.html")
    assert "<iframe" in html
    assert "sandbox" in html


# ── PR3-05: token consumption fix ────────────────────────────────────────────

# Palette hex literals that lived in the old :root block and must be gone.
_PALETTE_LITERALS = [
    "#7ec8e3",  # old accent (replaced by #9cddc8 in brand-identity-v1)
    "#2d7d9a",  # accent-dark (now via var(--color-accent-dark))
    "#fafafa",  # bg (now via var(--color-bg))
    "#ffffff",  # surface (now via var(--color-surface))
    "#111111",  # heading (now via var(--color-heading))
    "#666666",  # muted (now via var(--color-muted))
    "#dddddd",  # border (now via var(--color-border))
    "#333333",  # border-strong (now via var(--color-border-strong))
    "#f0f0f0",  # code-bg (now via var(--color-code-bg))
]


def test_wrapper_no_hardcoded_palette_literals() -> None:
    """PR3-05: wrapper HTML must not contain any hard-coded palette hex literals."""
    rendered = _render("dadaia-workspace", "architecture.html")
    for literal in _PALETTE_LITERALS:
        assert literal not in rendered, (
            f"Hard-coded palette literal {literal!r} found in wrapper output; "
            "replace with the appropriate var(--color-*) reference."
        )


def test_wrapper_uses_color_tokens() -> None:
    """PR3-05: wrapper CSS must reference var(--color-*) tokens, not hard-coded hex."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "var(--color-accent" in rendered
    assert "var(--color-surface" in rendered
    assert "var(--color-border" in rendered


def test_wrapper_links_tokens_css() -> None:
    """PR3-05: wrapper must link /static/tokens.css so theme palettes are available."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "/static/tokens.css" in rendered


def test_wrapper_links_memory_css() -> None:
    """T-PUX-03: wrapper must link /static/memory.css for panel visual identity."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "/static/memory.css" in rendered


def test_wrapper_prepaint_theme_script() -> None:
    """PR3-05: wrapper must include pre-paint inline script that reads localStorage
    and applies data-theme before first contentful paint (no FOUC on theme)."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "localStorage" in rendered
    assert "dadaia-panel-theme" in rendered
    assert "dataset.theme" in rendered
