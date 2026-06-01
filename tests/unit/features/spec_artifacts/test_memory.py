"""Unit tests for dadaia_workspace.features.spec_artifacts.memory.

Covers:
- AC-T3-1: scaffold has index.yaml (T-MSS-06) with minimal catalog
- AC-T3-2 (updated T-MMS-04): memory_product_add creates feature .md + updates index
- AC-T3-3: idempotent index regeneration
- AC-C-6 (updated T-MMS-04): dadaia memory product add <slug> creates .md + regenerates index
- AC-C-7: idempotent on index regeneration
- T-MMS-04: born-markdown scaffold — .md files with valid frontmatter; lint passes
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from dadaia_workspace.features.spec_artifacts.memory import (
    MemoryProductAddResult,
    memory_product_add,
)
from dadaia_workspace.features.specs.renderer import validate_atom

# ── templates directory for rendering ─────────────────────────────────────────
_TEMPLATES_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "dadaia_workspace" / "public" / "templates"
)

_SCAFFOLD_DIR = (
    Path(__file__).parent.parent.parent.parent.parent / "dadaia_workspace" / "public" / "scaffold"
)


# ── scaffold YAML stub (AC-T3-1 updated for T-MSS-06) ────────────────────────


class TestScaffoldIndexHtml:
    """AC-T3-1 (updated T-MSS-06): scaffold/memory/product/ now ships index.yaml (not index.html).

    The scaffold function renders YAML→HTML during scaffolding. Tests updated to
    reflect the YAML-source reality while verifying AC-C5-1..6 compliance.
    """

    def test_scaffold_product_index_yaml_exists(self) -> None:
        """AC-C5-3 / T-MSS-06: index.yaml must exist in the scaffold (replaces index.html)."""
        index = _SCAFFOLD_DIR / "memory" / "product" / "index.yaml"
        assert index.is_file(), "scaffold/memory/product/index.yaml must exist (AC-C5-3 / T-MSS-06)"

    def test_scaffold_product_index_html_removed(self) -> None:
        """AC-C5-4 / T-MSS-06: old index.html scaffold file must be removed (REPLACE is complete)."""
        old_html = _SCAFFOLD_DIR / "memory" / "product" / "index.html"
        assert not old_html.exists(), (
            "scaffold/memory/product/index.html must be removed (AC-C5-4 / T-MSS-06); "
            "the scaffold now ships index.yaml"
        )

    def test_scaffold_index_yaml_is_valid_against_schema(self) -> None:
        """AC-C5-3: index.yaml must be valid against memory-product-index-v1 schema."""
        index = _SCAFFOLD_DIR / "memory" / "product" / "index.yaml"
        data = yaml.safe_load(index.read_text(encoding="utf-8"))
        # Should not raise; raises jsonschema.ValidationError on failure.
        validate_atom(data, "memory-product-index-v1")

    def test_scaffold_index_rendered_html_has_catalog_section(self, tmp_path: Path) -> None:
        """AC-T3-1 / T-MSS-06: scaffolded specs/memory/product/index.html contains <section id='catalog'>."""
        from dadaia_workspace.features.specs.scaffolder import scaffold

        specs_dir = tmp_path / "specs"
        result = scaffold(
            specs_dir=specs_dir,
            project_name="test-project",
            force=False,
            templates_dir=_TEMPLATES_DIR,
        )
        assert result.errors == [], f"Scaffold errors: {result.errors}"

        index = specs_dir / "memory" / "product" / "index.html"
        assert index.is_file(), "specs/memory/product/index.html must exist after scaffold"
        content = index.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content or "<!doctype html>" in content.lower()
        assert "<html" in content
        assert 'id="catalog"' in content, "index.html must contain <section id='catalog'> (AC-T3-1)"

    def test_scaffold_index_rendered_html_has_placeholder_entry(self, tmp_path: Path) -> None:
        """T-MSS-06: scaffolded index.html has the placeholder catalog entry from the YAML stub.

        The minimal-valid product-index stub requires at least 1 catalog entry (schema minItems:1).
        The rendered HTML therefore contains a link to placeholder.html, which also ships in scaffold.
        """
        from dadaia_workspace.features.specs.scaffolder import scaffold

        specs_dir = tmp_path / "specs"
        result = scaffold(
            specs_dir=specs_dir,
            project_name="test-project",
            force=False,
            templates_dir=_TEMPLATES_DIR,
        )
        assert result.errors == [], f"Scaffold errors: {result.errors}"

        index = specs_dir / "memory" / "product" / "index.html"
        content = index.read_text(encoding="utf-8")
        catalog_match = re.search(
            r'<section id="catalog">(.*?)</section>',
            content,
            re.DOTALL,
        )
        assert catalog_match is not None, "catalog section not found"
        catalog_html = catalog_match.group(1)
        # The placeholder entry generates exactly 1 link
        links = re.findall(r'<a\s+href="[^"]+\.html"', catalog_html)
        assert len(links) == 1, (
            f"Expected 1 placeholder entry in catalog, found {len(links)} (T-MSS-06)"
        )
        assert "placeholder.html" in catalog_html


# ── memory_product_add unit tests (AC-T3-2, AC-T3-3, T-MMS-04) ───────────────

# Path to lint-memory-atoms.py script (used in T-MMS-04 gate assertions).
_LINT_SCRIPT = (
    Path(__file__).parent.parent.parent.parent.parent
    / "dadaia_workspace"
    / "public"
    / "scripts"
    / "lint-memory-atoms.py"
)


class TestMemoryProductAdd:
    """Tests for memory_product_add feature function.

    Updated in T-MMS-04: the function now writes <slug>.md (born-markdown)
    instead of <slug>.html.  The index.html regeneration path is unchanged.
    """

    def test_creates_feature_md(self, tmp_path: Path) -> None:
        """T-MMS-04 / AC-C-6 (updated): creates specs/memory/product/<slug>.md."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)

        assert isinstance(result, MemoryProductAddResult)
        feature = specs / "memory" / "product" / "payments.md"
        assert feature.is_file(), "payments.md must be created (T-MMS-04)"
        assert result.created_feature is True
        assert result.feature_html == feature

    def test_feature_md_has_valid_frontmatter(self, tmp_path: Path) -> None:
        """T-MMS-04: the created .md file has YAML frontmatter with required fields."""
        specs = tmp_path / "specs"
        specs.mkdir()

        memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)

        content = (specs / "memory" / "product" / "payments.md").read_text(encoding="utf-8")
        # Must start with frontmatter delimiter
        assert content.startswith("---\n"), "Markdown atom must start with --- frontmatter"

        import yaml as _yaml

        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        assert fm_match, "No valid YAML frontmatter block found"
        fm = _yaml.safe_load(fm_match.group(1))

        required = {
            "slug",
            "title",
            "category",
            "tldr",
            "summary",
            "tags",
            "agent_tier",
            "token_estimate",
            "last_updated",
            "release_origin",
        }
        missing = required - set(fm.keys())
        assert not missing, f"Frontmatter missing required fields: {missing}"

    def test_feature_md_slug_matches_filename(self, tmp_path: Path) -> None:
        """T-MMS-04: frontmatter slug must equal the file stem (payments)."""
        import yaml as _yaml

        specs = tmp_path / "specs"
        specs.mkdir()

        memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)

        content = (specs / "memory" / "product" / "payments.md").read_text(encoding="utf-8")
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        assert fm_match
        fm = _yaml.safe_load(fm_match.group(1))
        assert fm["slug"] == "payments", f"Expected slug='payments', got {fm['slug']!r}"

    def test_feature_md_passes_lint(self, tmp_path: Path) -> None:
        """T-MMS-04 gate: the scaffolded .md passes lint-memory-atoms.py (exit 0 or 2 warn-only)."""
        specs = tmp_path / "specs"
        specs.mkdir()

        memory_product_add(specs, "my-feature", templates_dir=_TEMPLATES_DIR)

        memory_dir = specs / "memory"
        proc = subprocess.run(
            [sys.executable, str(_LINT_SCRIPT), "--memory-dir", str(memory_dir)],
            capture_output=True,
            text=True,
        )
        # Exit 0 = clean, exit 2 = warnings only. Exit 1 = ERROR (must not happen).
        assert proc.returncode != 1, (
            f"lint-memory-atoms.py returned ERROR (exit 1) for scaffolded atom.\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    def test_regenerates_index_with_new_entry(self, tmp_path: Path) -> None:
        """AC-T3-2 / AC-C-6 (updated): index.html is updated to include the new slug."""
        specs = tmp_path / "specs"
        specs.mkdir()

        result = memory_product_add(specs, "payments", templates_dir=_TEMPLATES_DIR)

        index_path = specs / "memory" / "product" / "index.html"
        assert index_path.is_file(), "index.html must be (re)created"
        assert result.index_html == index_path
        content = index_path.read_text(encoding="utf-8")
        assert "payments" in content, "index.html must reference payments slug (AC-T3-2)"
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
            "Second call must not re-create the existing feature Markdown atom"
        )
        # Both indexes must reference payments
        assert "payments" in index_content_1
        assert "payments" in index_content_2
        # The catalog section content must be identical

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

        # Verify slugs appear in lexicographic order (via .html links in index)
        pos_alpha = content.index("alpha")
        pos_middle = content.index("middle")
        pos_zebra = content.index("zebra")
        assert pos_alpha < pos_middle < pos_zebra, "Catalog entries must be in lexicographic order"

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


# ── T-MMS-04: born-markdown scaffold file assertions ─────────────────────────


class TestBornMarkdownScaffolds:
    """T-MMS-04: verify .md scaffold files exist and pass lint."""

    def test_architecture_md_scaffold_exists(self) -> None:
        """T-MMS-04: public/scaffold/memory/architecture.md must exist."""
        path = _SCAFFOLD_DIR / "memory" / "architecture.md"
        assert path.is_file(), f"architecture.md scaffold missing at {path}"

    def test_tech_stack_md_scaffold_exists(self) -> None:
        """T-MMS-04: public/scaffold/memory/tech-stack.md must exist."""
        path = _SCAFFOLD_DIR / "memory" / "tech-stack.md"
        assert path.is_file(), f"tech-stack.md scaffold missing at {path}"

    def test_product_index_md_scaffold_exists(self) -> None:
        """T-MMS-04: public/scaffold/memory/product/index.md must exist."""
        path = _SCAFFOLD_DIR / "memory" / "product" / "index.md"
        assert path.is_file(), f"product/index.md scaffold missing at {path}"

    def test_feature_md_scaffold_exists(self) -> None:
        """T-MMS-04: public/scaffold/memory/product/feature.md must exist."""
        path = _SCAFFOLD_DIR / "memory" / "product" / "feature.md"
        assert path.is_file(), f"product/feature.md scaffold missing at {path}"

    def test_architecture_md_has_frontmatter(self) -> None:
        """T-MMS-04: architecture.md scaffold has valid YAML frontmatter."""
        import yaml as _yaml

        path = _SCAFFOLD_DIR / "memory" / "architecture.md"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        assert fm_match, "No frontmatter block found in architecture.md scaffold"
        fm = _yaml.safe_load(fm_match.group(1))
        assert fm.get("slug") == "architecture"
        assert fm.get("category") == "core"

    def test_tech_stack_md_has_frontmatter(self) -> None:
        """T-MMS-04: tech-stack.md scaffold has valid YAML frontmatter."""
        import yaml as _yaml

        path = _SCAFFOLD_DIR / "memory" / "tech-stack.md"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        assert fm_match
        fm = _yaml.safe_load(fm_match.group(1))
        assert fm.get("slug") == "tech-stack"
        assert fm.get("category") == "core"

    def test_product_index_md_has_frontmatter(self) -> None:
        """T-MMS-04: product/index.md scaffold has valid YAML frontmatter."""
        import yaml as _yaml

        path = _SCAFFOLD_DIR / "memory" / "product" / "index.md"
        content = path.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        assert fm_match
        fm = _yaml.safe_load(fm_match.group(1))
        assert fm.get("slug") == "index"
        assert fm.get("category") == "product"

    def test_architecture_md_passes_lint(self, tmp_path: Path) -> None:
        """T-MMS-04 gate: architecture.md scaffold passes lint-memory-atoms.py."""
        import shutil

        # Copy scaffold to a temp memory dir so the linter can find it.
        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        shutil.copy(_SCAFFOLD_DIR / "memory" / "architecture.md", mem_dir / "architecture.md")

        proc = subprocess.run(
            [sys.executable, str(_LINT_SCRIPT), "--memory-dir", str(mem_dir)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 1, (
            f"architecture.md scaffold failed lint (exit 1).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    def test_tech_stack_md_passes_lint(self, tmp_path: Path) -> None:
        """T-MMS-04 gate: tech-stack.md scaffold passes lint-memory-atoms.py."""
        import shutil

        mem_dir = tmp_path / "memory"
        mem_dir.mkdir()
        shutil.copy(_SCAFFOLD_DIR / "memory" / "tech-stack.md", mem_dir / "tech-stack.md")

        proc = subprocess.run(
            [sys.executable, str(_LINT_SCRIPT), "--memory-dir", str(mem_dir)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 1, (
            f"tech-stack.md scaffold failed lint (exit 1).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )

    def test_product_index_md_passes_lint(self, tmp_path: Path) -> None:
        """T-MMS-04 gate: product/index.md scaffold passes lint-memory-atoms.py."""
        import shutil

        mem_dir = tmp_path / "memory"
        product_dir = mem_dir / "product"
        product_dir.mkdir(parents=True)
        shutil.copy(
            _SCAFFOLD_DIR / "memory" / "product" / "index.md",
            product_dir / "index.md",
        )

        proc = subprocess.run(
            [sys.executable, str(_LINT_SCRIPT), "--memory-dir", str(mem_dir)],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 1, (
            f"product/index.md scaffold failed lint (exit 1).\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
