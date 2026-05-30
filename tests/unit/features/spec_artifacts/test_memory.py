"""Unit tests for dadaia_workspace.features.spec_artifacts.memory.

Covers:
- AC-T3-1: scaffold has index.html with empty catalog
- AC-T3-2: memory_product_add creates feature HTML + updates index
- AC-T3-3: idempotent index regeneration
- AC-C-6: dadaia memory product add <slug> creates feature HTML + regenerates index
- AC-C-7: idempotent on index regeneration
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dadaia_workspace.features.spec_artifacts.memory import (
    MemoryProductAddResult,
    memory_product_add,
)

# ── templates directory for rendering ─────────────────────────────────────────
_TEMPLATES_DIR = (
    Path(__file__).parent.parent.parent.parent.parent
    / "dadaia_workspace"
    / "public"
    / "templates"
)


# ── scaffold static index.html (AC-T3-1) ─────────────────────────────────────


class TestScaffoldIndexHtml:
    """AC-T3-1: scaffold/memory/product/index.html exists with empty catalog."""

    def test_scaffold_product_index_exists(self) -> None:
        """AC-T3-1: index.html must exist in the scaffold."""
        scaffold_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "dadaia_workspace"
            / "public"
            / "scaffold"
        )
        index = scaffold_dir / "memory" / "product" / "index.html"
        assert index.is_file(), (
            "scaffold/memory/product/index.html must exist (AC-T3-1)"
        )

    def test_scaffold_index_is_valid_html(self) -> None:
        """AC-T3-1: index.html is valid HTML with <!DOCTYPE html>."""
        scaffold_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "dadaia_workspace"
            / "public"
            / "scaffold"
        )
        index = scaffold_dir / "memory" / "product" / "index.html"
        content = index.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()
        assert "<html" in content

    def test_scaffold_index_has_catalog_section(self) -> None:
        """AC-T3-1: index.html must contain <section id='catalog'>."""
        scaffold_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "dadaia_workspace"
            / "public"
            / "scaffold"
        )
        index = scaffold_dir / "memory" / "product" / "index.html"
        content = index.read_text(encoding="utf-8")
        assert 'id="catalog"' in content, (
            "index.html must contain <section id='catalog'> (AC-T3-1)"
        )

    def test_scaffold_index_has_zero_feature_entries(self) -> None:
        """AC-T3-1: empty catalog — no <li> items inside the catalog <ol>."""
        scaffold_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "dadaia_workspace"
            / "public"
            / "scaffold"
        )
        index = scaffold_dir / "memory" / "product" / "index.html"
        content = index.read_text(encoding="utf-8")
        # Find the catalog section; it should have an empty <ol>
        # We do a simple check: no .html link inside the catalog section
        import re
        catalog_match = re.search(
            r'<section id="catalog">(.*?)</section>',
            content,
            re.DOTALL,
        )
        assert catalog_match is not None, "catalog section not found"
        catalog_html = catalog_match.group(1)
        # No <a href="*.html"> means no entries
        links = re.findall(r'<a\s+href="[^"]+\.html"', catalog_html)
        assert len(links) == 0, (
            f"Expected 0 feature links in catalog, found {len(links)} (AC-T3-1)"
        )


# ── memory_product_add unit tests (AC-T3-2, AC-T3-3) ──────────────────────────


class TestMemoryProductAdd:
    """Tests for memory_product_add feature function."""

    def test_creates_feature_html(self, tmp_path: Path) -> None:
        """AC-T3-2 / AC-C-6: creates specs/memory/product/<slug>.html."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)

        assert isinstance(result, MemoryProductAddResult)
        feature = specs / "memory" / "product" / "payments.html"
        assert feature.is_file(), "payments.html must be created"
        assert result.created_feature is True
        assert result.feature_html == feature

    def test_feature_html_is_valid_html(self, tmp_path: Path) -> None:
        """The created feature HTML contains DOCTYPE and html tags."""
        specs = tmp_path / "specs"
        specs.mkdir()

        memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)

        content = (specs / "memory" / "product" / "payments.html").read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()
        assert "<html" in content

    def test_regenerates_index_with_new_entry(self, tmp_path: Path) -> None:
        """AC-T3-2 / AC-C-6: index.html is updated to include the new slug."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)

        index_path = specs / "memory" / "product" / "index.html"
        assert index_path.is_file(), "index.html must be (re)created"
        assert result.index_html == index_path
        content = index_path.read_text(encoding="utf-8")
        assert "payments.html" in content, (
            "index.html must contain a link to payments.html (AC-T3-2)"
        )
        assert "payments" in result.slug_entries

    def test_idempotent_index_regeneration(self, tmp_path: Path) -> None:
        """AC-T3-3 / AC-C-7: calling add twice produces identical index.html."""
        specs = tmp_path / "specs"
        specs.mkdir()

        # First call
        memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)
        index_content_1 = (specs / "memory" / "product" / "index.html").read_text(encoding="utf-8")

        # Second call with same slug
        result2 = memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)
        index_content_2 = (specs / "memory" / "product" / "index.html").read_text(encoding="utf-8")

        assert result2.created_feature is False, (
            "Second call must not re-create the existing feature HTML"
        )
        # Both indexes must reference payments.html
        assert "payments.html" in index_content_1
        assert "payments.html" in index_content_2
        # The catalog section content must be identical
        import re
        def extract_catalog(html: str) -> str:
            m = re.search(r'<section id="catalog">(.*?)</section>', html, re.DOTALL)
            assert m, "catalog section not found"
            return m.group(1).strip()
        assert extract_catalog(index_content_1) == extract_catalog(index_content_2), (
            "Catalog section must be identical after idempotent re-run (AC-T3-3)"
        )

    def test_multiple_slugs_sorted_in_index(self, tmp_path: Path) -> None:
        """Index.html must list all slugs in lexicographic order."""
        specs = tmp_path / "specs"
        specs.mkdir()

        memory_product_add(specs, "zebra", templates_dir=_TEMPLATES_DIR)
        memory_product_add(specs, "alpha", templates_dir=_TEMPLATES_DIR)
        memory_product_add(specs, "middle", templates_dir=_TEMPLATES_DIR)

        content = (specs / "memory" / "product" / "index.html").read_text(encoding="utf-8")

        # Verify links appear in lexicographic order
        pos_alpha = content.index("alpha.html")
        pos_middle = content.index("middle.html")
        pos_zebra = content.index("zebra.html")
        assert pos_alpha < pos_middle < pos_zebra, (
            "Catalog entries must be in lexicographic order"
        )

    def test_invalid_slug_raises_value_error(self, tmp_path: Path) -> None:
        """Invalid slug must raise ValueError."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with pytest.raises(ValueError, match=r"Invalid slug"):
            memory_product_add(specs, "INVALID SLUG", templates_dir=_TEMPLATES_DIR)

    def test_slug_starting_with_digit_raises(self, tmp_path: Path) -> None:
        """Slug starting with a digit is invalid."""
        specs = tmp_path / "specs"
        specs.mkdir()

        with pytest.raises(ValueError, match=r"Invalid slug"):
            memory_product_add(specs, "1bad", templates_dir=_TEMPLATES_DIR)

    def test_product_dir_created_if_absent(self, tmp_path: Path) -> None:
        """specs/memory/product/ is created automatically if missing."""
        specs = tmp_path / "specs"
        specs.mkdir()

        assert not (specs / "memory" / "product").exists()
        memory_product_add(specs, "auth", templates_dir=_TEMPLATES_DIR)
        assert (specs / "memory" / "product").is_dir()
