"""Unit contracts for the memory wrapper view.

Two survivors:
  1. iframe src correct + nested path + sandbox attr + tokens/memory CSS links
     + prepaint, merged into one.
  2. slug + path HTML-escaping — param (XSS).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.panel.views.wrapper import render_memory_wrapper

pytestmark = pytest.mark.unit


def _render(slug: str, path: str) -> str:
    workspace_root = Path("/workspace")
    view = render_memory_wrapper(workspace_root)
    status, content_type, body = view(slug=slug, path=path)
    assert status == 200
    assert content_type == "text/html; charset=utf-8"
    return body.decode("utf-8")


# ---------------------------------------------------------------------------
# 1. iframe src + nested path + sandbox + tokens/memory css + prepaint
# ---------------------------------------------------------------------------


def test_wrapper_iframe_sandbox_css_links_and_prepaint() -> None:
    html = _render("dadaia-workspace", "architecture.html")

    assert "Voltar ao Painel" in html
    assert 'href="/"' in html
    assert 'src="/memory/dadaia-workspace/architecture.html"' in html
    assert "<iframe" in html
    assert "sandbox" in html

    assert "var(--color-accent" in html
    assert "var(--color-surface" in html
    assert "var(--color-border" in html
    assert "/static/tokens.css" in html
    assert "/static/memory.css" in html

    assert "localStorage" in html
    assert "dadaia-panel-theme" in html
    assert "dataset.theme" in html

    # Nested paths render the iframe src correctly too.
    nested_html = _render("dadaia-workspace", "product/index.html")
    assert 'src="/memory/dadaia-workspace/product/index.html"' in nested_html


# ---------------------------------------------------------------------------
# 2. slug + path HTML-escaping (XSS)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "path", "forbidden", "escaped_needle"),
    [
        pytest.param(
            "<script>alert(1)</script>",
            "file.html",
            "<script>alert(1)</script>",
            "&lt;script&gt;",
            id="slug-escaped",
        ),
        pytest.param(
            "safe-slug",
            "<img src=x onerror=alert(1)>.html",
            "<img src=x onerror=alert(1)>",
            "&lt;img",
            id="path-escaped",
        ),
    ],
)
def test_slug_and_path_are_html_escaped(
    slug: str, path: str, forbidden: str, escaped_needle: str
) -> None:
    html = _render(slug, path)
    assert forbidden not in html
    assert escaped_needle in html
