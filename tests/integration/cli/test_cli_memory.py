"""Integration tests for `dadaia memory product add` CLI command.

Tests use Typer's CliRunner on a real tmp_path filesystem.

Covers:
- AC-T3-2: dadaia memory product add payments creates feature Markdown atom + updates index
- AC-T3-3: idempotent index regeneration
- AC-C-6: feature Markdown atom + index regenerated
- AC-C-7: idempotent

T-MMS-04 change: `memory product add <slug>` now creates `<slug>.md` (born-markdown
scaffold with YAML frontmatter) instead of `<slug>.html`.  The index is still
regenerated as `index.html` (that stays until W4 / T-MMS-11).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    """Return an empty specs/ directory."""
    s = tmp_path / "specs"
    s.mkdir()
    return s


# ── happy path ────────────────────────────────────────────────────────────────


class TestMemoryProductAdd:
    def test_creates_feature_md_and_index(self, specs: Path) -> None:
        """AC-T3-2 / AC-C-6: creates feature Markdown atom and regenerates index.html.

        T-MMS-04: feature file is now <slug>.md (born-markdown), not <slug>.html.
        index.html is still regenerated (html index stays until W4).
        """
        result = _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        # T-MMS-04: feature atom is now .md, not .html
        assert (specs / "memory" / "product" / "payments.md").is_file()
        assert (specs / "memory" / "product" / "index.html").is_file()
        # index.html still links to the slug HTML path for backwards-compat
        assert "payments.html" in (specs / "memory" / "product" / "index.html").read_text(
            encoding="utf-8"
        )

    def test_feature_md_has_valid_frontmatter(self, specs: Path) -> None:
        """Feature Markdown atom starts with YAML frontmatter (T-MMS-04 born-markdown)."""
        _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )
        content = (specs / "memory" / "product" / "payments.md").read_text(encoding="utf-8")
        # Must start with frontmatter delimiter
        assert content.startswith("---"), "Feature .md must start with YAML frontmatter '---'"
        # Slug must be injected into the frontmatter
        assert "slug: payments" in content, "Frontmatter must contain 'slug: payments'"

    def test_idempotent_on_second_run(self, specs: Path) -> None:
        """AC-T3-3 / AC-C-7: second call produces identical index.html catalog section."""
        _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )
        index_after_first = (specs / "memory" / "product" / "index.html").read_text(
            encoding="utf-8"
        )

        result = _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        index_after_second = (specs / "memory" / "product" / "index.html").read_text(
            encoding="utf-8"
        )
        # Catalog section must be identical
        import re

        def catalog(html: str) -> str:
            m = re.search(r'<section id="catalog">(.*?)</section>', html, re.DOTALL)
            assert m
            return m.group(1).strip()

        assert catalog(index_after_first) == catalog(index_after_second), (
            "Catalog section must be identical after idempotent re-run (AC-T3-3)"
        )

    def test_multiple_slugs_appear_in_index(self, specs: Path) -> None:
        """All added slugs appear in index.html in lexicographic order."""
        for slug in ("zebra", "alpha", "middle"):
            _runner.invoke(
                app,
                ["memory", "product", "add", slug, "--specs-dir", str(specs)],
            )

        content = (specs / "memory" / "product" / "index.html").read_text(encoding="utf-8")
        pos_alpha = content.index("alpha.html")
        pos_middle = content.index("middle.html")
        pos_zebra = content.index("zebra.html")
        assert pos_alpha < pos_middle < pos_zebra


# ── error paths ───────────────────────────────────────────────────────────────


class TestMemoryProductAddErrors:
    def test_invalid_slug_exits_nonzero(self, specs: Path) -> None:
        """Invalid slug causes non-zero exit."""
        result = _runner.invoke(
            app,
            ["memory", "product", "add", "INVALID SLUG", "--specs-dir", str(specs)],
        )
        assert result.exit_code != 0

    def test_missing_specs_dir_exits_nonzero(self, tmp_path: Path) -> None:
        """Non-existent specs_dir causes non-zero exit."""
        result = _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(tmp_path / "nonexistent")],
        )
        assert result.exit_code != 0
