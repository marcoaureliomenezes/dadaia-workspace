"""Integration tests for `dadaia memory product add` CLI command.

Tests use Typer's CliRunner on a real tmp_path filesystem.

Covers:
- AC-T3-2: dadaia memory product add payments creates feature HTML + updates index
- AC-T3-3: idempotent index regeneration
- AC-C-6: feature HTML + index regenerated
- AC-C-7: idempotent
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
    def test_creates_feature_html_and_index(self, specs: Path) -> None:
        """AC-T3-2 / AC-C-6: creates feature HTML and regenerates index."""
        result = _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        assert (specs / "memory" / "product" / "payments.html").is_file()
        assert (specs / "memory" / "product" / "index.html").is_file()
        assert "payments.html" in (specs / "memory" / "product" / "index.html").read_text(
            encoding="utf-8"
        )

    def test_feature_html_is_valid_html(self, specs: Path) -> None:
        """Feature HTML contains DOCTYPE."""
        _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )
        content = (specs / "memory" / "product" / "payments.html").read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()

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
