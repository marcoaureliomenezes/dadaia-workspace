"""Unit tests for the canonical memory-URL builder + wikilink renderer + mermaid
fence escaping in views/_md_render.py.

T-016-P03: Single source of truth for memory URL construction.
T-016-P04: Parameterized wikilink renderer by context slug.
v0.1.52 FR4: mermaid fence escaping (OWASP A03 / XSS).

The index-chip-href .md-not-.html regression duplicate was DELETED — owned by
the ``test_views_index.py`` card-contract survivor.

Three survivors:
  1. URL builders: view vs raw prefix + nested path + .md never .html param.
  2. Wikilink renderer slug parameterisation + default + no-hardcode + cache per-slug.
  3. Mermaid fence escaping: hostile <script> + <img onerror> via block_code directly.
"""

from __future__ import annotations

import pytest

from dadaia_workspace.features.panel.views._md_render import (
    build_renderer,
    memory_raw_url,
    memory_view_url,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 1. URL builders: view vs raw prefix + nested path + .md never .html
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("builder", "slug", "path", "expected"),
    [
        pytest.param(
            memory_view_url,
            "dadaia-workspace",
            "architecture.md",
            "/memory-view/dadaia-workspace/architecture.md",
            id="view-architecture",
        ),
        pytest.param(
            memory_view_url,
            "dadaia-workspace",
            "product/index.md",
            "/memory-view/dadaia-workspace/product/index.md",
            id="view-nested-path-preserved",
        ),
        pytest.param(
            memory_view_url,
            "my-project",
            "architecture.md",
            "/memory-view/my-project/architecture.md",
            id="view-arbitrary-slug",
        ),
        pytest.param(
            memory_raw_url,
            "dadaia-workspace",
            "architecture.md",
            "/memory/dadaia-workspace/architecture.md",
            id="raw-architecture",
        ),
        pytest.param(
            memory_raw_url,
            "dadaia-workspace",
            "product/index.md",
            "/memory/dadaia-workspace/product/index.md",
            id="raw-nested-path-preserved",
        ),
        pytest.param(
            memory_raw_url,
            "other-context",
            "architecture.md",
            "/memory/other-context/architecture.md",
            id="raw-arbitrary-slug",
        ),
    ],
)
def test_url_builders(builder, slug: str, path: str, expected: str) -> None:  # type: ignore[no-untyped-def]
    url = builder(slug, path)
    assert url == expected
    assert url.startswith("/")
    assert ".html" not in url

    if (slug, path) != ("dadaia-workspace", "architecture.md"):
        return
    # view vs raw prefix distinctness, checked once regardless of which builder ran.
    raw = memory_raw_url("slug", "file.md")
    view = memory_view_url("slug", "file.md")
    assert raw.startswith("/memory/")
    assert view.startswith("/memory-view/")
    assert raw != view


# ---------------------------------------------------------------------------
# 2. Wikilink renderer slug parameterisation + default + no-hardcode + cache
# ---------------------------------------------------------------------------


def test_wikilink_renderer_slug_parameterisation_default_and_cache() -> None:
    # A non-default slug renders with the given slug's href, never hardcoded
    # 'dadaia-workspace', and always with a .md extension.
    md = build_renderer("my-project")
    result: str = md("[[architecture]]")  # type: ignore[assignment]
    # v6 canon single (FR1/A1.5/A1.6, T-050-06): [[architecture]] resolves to the
    # RENAMED file, not the generic "<slug>.md" guess.
    assert "/memory-view/my-project/ARCHITECTURE.md" in result

    md_default = build_renderer()
    result_default: str = md_default("[[tech-stack]]")  # type: ignore[assignment]
    assert "/memory-view/dadaia-workspace/TECHSTACK.md" in result_default

    md_other = build_renderer("other-project")
    result_other: str = md_other("[[architecture]]")  # type: ignore[assignment]
    assert "dadaia-workspace" not in result_other
    assert "/memory-view/other-project/ARCHITECTURE.md" in result_other

    md_ext = build_renderer("some-context")
    result_ext: str = md_ext("[[product]]")  # type: ignore[assignment]
    assert "/memory-view/some-context/product.md" in result_ext
    assert "product.html" not in result_ext

    # Same slug returns the same cached renderer instance; different slugs don't.
    md_a = build_renderer("project-a")
    md_a2 = build_renderer("project-a")
    md_b = build_renderer("project-b")
    assert md_a is md_a2, "Same slug should return the same cached renderer instance"
    assert md_a is not md_b, "Different slugs must return distinct renderer instances"


# ---------------------------------------------------------------------------
# 3. Mermaid fence escaping (v0.1.52 FR4 — OWASP A03 / XSS)
#
# block_code emits <pre class="mermaid"> for mermaid fences. No Mermaid client
# ships on the panel (the CSP forbids the CDN import), so the fence body must
# arrive HTML-ESCAPED — never as live HTML. Exercised directly via the
# renderer (bypassing the view's outer _sanitise defence-in-depth) so it
# probes the escape itself: an UNescaped block_code emits raw <script>/<img>
# and FAILS these assertions. The falsifiability probe (SPEC §5 AC-7).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fence_body", "escaped_needle", "raw_needle"),
    [
        pytest.param(
            "<script>alert(1)</script>",
            "&lt;script&gt;alert(1)&lt;/script&gt;",
            "<script>alert(1)</script>",
            id="hostile-script-fence",
        ),
        pytest.param(
            "<img src=x onerror=alert(1)>",
            "&lt;img src=x onerror=alert(1)&gt;",
            "<img src=x onerror=alert(1)>",
            id="hostile-img-onerror-fence",
        ),
    ],
)
def test_mermaid_fence_escapes_hostile_payloads(
    fence_body: str, escaped_needle: str, raw_needle: str
) -> None:
    md = build_renderer("proj")
    result: str = md(f"```mermaid\n{fence_body}\n```\n")  # type: ignore[assignment]
    assert '<pre class="mermaid">' in result
    assert escaped_needle in result
    assert raw_needle not in result
