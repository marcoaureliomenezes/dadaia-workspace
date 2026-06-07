"""Unit tests for the canonical memory-URL builder in views/_md_render.py.

T-016-P03: Single source of truth for memory URL construction.
"""

from __future__ import annotations

from dadaia_workspace.features.panel.views._md_render import (
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

        from dadaia_workspace.features.panel.views.index import render_index
        from dadaia_workspace.features.panel.service import PanelContext, PanelService

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
