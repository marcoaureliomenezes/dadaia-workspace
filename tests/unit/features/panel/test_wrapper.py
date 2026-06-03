"""Unit contracts for the memory wrapper view."""

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


def test_wrapper_uses_color_tokens() -> None:
    """Wrapper CSS must reference shared color tokens."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "var(--color-accent" in rendered
    assert "var(--color-surface" in rendered
    assert "var(--color-border" in rendered


def test_wrapper_links_tokens_css() -> None:
    """Wrapper must link /static/tokens.css so theme palettes are available."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "/static/tokens.css" in rendered


def test_wrapper_links_memory_css() -> None:
    """Wrapper must link /static/memory.css for panel visual identity."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "/static/memory.css" in rendered


def test_wrapper_prepaint_theme_script() -> None:
    """Wrapper must apply stored theme before first contentful paint."""
    rendered = _render("dadaia-workspace", "architecture.html")
    assert "localStorage" in rendered
    assert "dadaia-panel-theme" in rendered
    assert "dataset.theme" in rendered
