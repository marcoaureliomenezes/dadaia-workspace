"""Integration tests for `dadaia memory product add` CLI command.

Tests use Typer's CliRunner on a real tmp_path filesystem.

Covers:
- AC-T3-2: dadaia memory product add payments creates feature Markdown atom
- AC-T3-3: idempotent — repeated call does not re-create the file
- AC-C-6: feature Markdown atom created
- AC-C-7: idempotent

memory-markdown-source-v1 (T-MMS-10/11): `memory product add <slug>` creates
`<slug>.md` (born-markdown scaffold with YAML frontmatter). The index.html
generation path was retired when the Jinja templates were deleted.
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
    def test_creates_feature_md(self, specs: Path) -> None:
        """AC-T3-2 / AC-C-6: creates feature Markdown atom.

        T-MMS-10/11: feature file is <slug>.md (born-markdown).
        index.html is no longer generated.
        """
        result = _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )

        assert result.exit_code == 0, result.output
        # T-MMS-04/T-MMS-10: feature atom is .md
        assert (specs / "memory" / "product" / "payments.md").is_file()
        # No index.html — the HTML index pipeline was retired
        assert not (specs / "memory" / "product" / "index.html").exists(), (
            "index.html must NOT be generated (T-MMS-10/11 retired the HTML index)"
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
        """AC-T3-3 / AC-C-7: second call with same slug does not re-create the file."""
        result1 = _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )
        assert result1.exit_code == 0, result1.output
        assert "created" in result1.output

        result2 = _runner.invoke(
            app,
            ["memory", "product", "add", "payments", "--specs-dir", str(specs)],
        )
        assert result2.exit_code == 0, result2.output
        assert "already exists" in result2.output

    def test_multiple_slugs_all_created(self, specs: Path) -> None:
        """All added slugs produce .md files in product dir."""
        for slug in ("zebra", "alpha", "middle"):
            result = _runner.invoke(
                app,
                ["memory", "product", "add", slug, "--specs-dir", str(specs)],
            )
            assert result.exit_code == 0, result.output

        for slug in ("zebra", "alpha", "middle"):
            assert (specs / "memory" / "product" / f"{slug}.md").is_file(), (
                f"{slug}.md must exist after add"
            )


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
