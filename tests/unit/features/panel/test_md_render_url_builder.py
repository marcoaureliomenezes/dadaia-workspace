"""Unit tests for the canonical memory-URL builder in views/_md_render.py.

T-016-P03: Single source of truth for memory URL construction.
T-016-P04: Parameterized wikilink renderer by context slug.
"""

from __future__ import annotations

from dadaia_workspace.features.panel.views._md_render import (
    build_renderer,
    memory_raw_url,
    memory_view_url,
)

# ---------------------------------------------------------------------------
# memory_view_url
# ---------------------------------------------------------------------------


class TestMemoryViewUrl:
    def test_architecture_md(self) -> None:
        """Standard architecture atom URL uses /memory-view/ and .md extension."""
        url = memory_view_url("dadaia-workspace", "architecture.md")
        assert url == "/memory-view/dadaia-workspace/architecture.md"

    def test_tech_stack_md(self) -> None:
        url = memory_view_url("dadaia-workspace", "tech-stack.md")
        assert url == "/memory-view/dadaia-workspace/tech-stack.md"

    def test_nested_product_index_md(self) -> None:
        """Nested path (product/index.md) is preserved as-is."""
        url = memory_view_url("dadaia-workspace", "product/index.md")
        assert url == "/memory-view/dadaia-workspace/product/index.md"

    def test_arbitrary_slug(self) -> None:
        """Different context slugs produce correct URLs."""
        url = memory_view_url("my-project", "architecture.md")
        assert url == "/memory-view/my-project/architecture.md"

    def test_no_html_extension(self) -> None:
        """Builder never produces .html URLs for standard atoms."""
        url = memory_view_url("dadaia-workspace", "architecture.md")
        assert ".html" not in url

    def test_returns_absolute_path(self) -> None:
        """URL must start with '/'."""
        url = memory_view_url("slug", "file.md")
        assert url.startswith("/")


# ---------------------------------------------------------------------------
# memory_raw_url
# ---------------------------------------------------------------------------


class TestMemoryRawUrl:
    def test_architecture_md(self) -> None:
        url = memory_raw_url("dadaia-workspace", "architecture.md")
        assert url == "/memory/dadaia-workspace/architecture.md"

    def test_tech_stack_md(self) -> None:
        url = memory_raw_url("dadaia-workspace", "tech-stack.md")
        assert url == "/memory/dadaia-workspace/tech-stack.md"

    def test_nested_product_index_md(self) -> None:
        url = memory_raw_url("dadaia-workspace", "product/index.md")
        assert url == "/memory/dadaia-workspace/product/index.md"

    def test_arbitrary_slug(self) -> None:
        url = memory_raw_url("other-context", "architecture.md")
        assert url == "/memory/other-context/architecture.md"

    def test_no_html_extension(self) -> None:
        url = memory_raw_url("dadaia-workspace", "architecture.md")
        assert ".html" not in url

    def test_returns_absolute_path(self) -> None:
        url = memory_raw_url("slug", "file.md")
        assert url.startswith("/")

    def test_different_prefix_from_view_url(self) -> None:
        """memory_raw_url uses /memory/ not /memory-view/."""
        raw = memory_raw_url("slug", "file.md")
        view = memory_view_url("slug", "file.md")
        assert raw.startswith("/memory/")
        assert view.startswith("/memory-view/")
        assert raw != view


# ---------------------------------------------------------------------------
# Regression guard: chip hrefs in index.py use .md (not .html)
# ---------------------------------------------------------------------------


class TestIndexChipHrefs:
    """Assert index.py emits .md URLs in chip hrefs (T-016-P03 regression guard)."""

    def test_context_card_chips_use_md_extension(self) -> None:
        """_render_context_card must produce .md chip hrefs, not .html."""
        from pathlib import Path
        from unittest.mock import MagicMock

        from dadaia_workspace.features.panel.service import PanelContext, PanelService
        from dadaia_workspace.features.panel.views.index import render_index

        ctx = PanelContext(
            name="Test Context",
            slug="test-context",
            repo_path=Path("/tmp/specs"),
            status="alive",
            branch="main",
        )
        service = MagicMock(spec=PanelService)
        service.list_active_contexts.return_value = [ctx]
        service.list_servers_grouped.return_value = []

        view_fn = render_index(service)
        status, content_type, body = view_fn()
        html = body.decode("utf-8")

        # Chip hrefs must use .md, never .html
        assert "/memory-view/test-context/architecture.md" in html, (
            "Architecture chip href must use .md extension"
        )
        assert "/memory-view/test-context/tech-stack.md" in html, (
            "Tech Stack chip href must use .md extension"
        )
        assert "/memory-view/test-context/product/index.md" in html, (
            "Product chip href must use .md extension"
        )
        assert "architecture.html" not in html, "No .html chip hrefs should remain"
        assert "tech-stack.html" not in html, "No .html chip hrefs should remain"
        assert "product/index.html" not in html, "No .html chip hrefs should remain"


# ---------------------------------------------------------------------------
# T-016-P04: Parameterized wikilink renderer
# ---------------------------------------------------------------------------


class TestWikilinkRendererParamBySlug:
    """build_renderer(slug) closes over the context slug for wikilink hrefs."""

    def test_wikilink_uses_given_slug(self) -> None:
        """Wikilink rendered in 'my-project' context → /memory-view/my-project/..."""
        md = build_renderer("my-project")
        result: str = md("[[architecture]]")  # type: ignore[assignment]
        assert "/memory-view/my-project/architecture.md" in result, (
            "Wikilink href must use the provided slug, not hardcoded 'dadaia-workspace'"
        )

    def test_wikilink_default_slug_is_dadaia_workspace(self) -> None:
        """Calling build_renderer() without slug defaults to 'dadaia-workspace'."""
        md = build_renderer()
        result: str = md("[[tech-stack]]")  # type: ignore[assignment]
        assert "/memory-view/dadaia-workspace/tech-stack.md" in result

    def test_wikilink_non_default_slug_does_not_contain_dadaia_workspace(self) -> None:
        """A non-default slug renderer must NOT reference 'dadaia-workspace'."""
        md = build_renderer("other-project")
        result: str = md("[[architecture]]")  # type: ignore[assignment]
        assert "dadaia-workspace" not in result, (
            "Non-default context renderer must not hardcode 'dadaia-workspace'"
        )
        assert "/memory-view/other-project/architecture.md" in result

    def test_renderer_cache_per_slug(self) -> None:
        """build_renderer returns same instance for same slug (cache hit)."""
        md_a = build_renderer("project-a")
        md_b = build_renderer("project-a")
        assert md_a is md_b, "Same slug should return the same cached renderer instance"

    def test_renderer_cache_different_slugs(self) -> None:
        """build_renderer returns different instances for different slugs."""
        md_a = build_renderer("project-a")
        md_b = build_renderer("project-b")
        assert md_a is not md_b, "Different slugs must return distinct renderer instances"

    def test_wikilink_md_extension_in_href(self) -> None:
        """Wikilink href must end with .md, not .html."""
        md = build_renderer("some-context")
        result: str = md("[[product]]")  # type: ignore[assignment]
        assert "/memory-view/some-context/product.md" in result
        assert "product.html" not in result
