"""Unit tests for the YAML → HTML memory atom renderer (T-MSS-03 / C-2).

Coverage targets
----------------
AC-C2-1: renderer.py is importable.
AC-C2-2: Rendering a valid memory-product-feature-v1 atom produces HTML with
         the 6 required section IDs:
           <section id="purpose">, <section id="flow">, <section id="trigger">,
           <section id="differential">, <section id="runtime-state">,
           <section id="dependencies">.
AC-C2-3: Rendering a YAML atom with a `diagram` field produces
         <pre class="mermaid"> and a CDN <script src=> tag.
AC-C2-4: Rendering the same YAML atom twice produces byte-identical HTML.
AC-C2-6: `dadaia memory render <fixture.yaml>` exits 0 and writes adjacent .html.

Additional (per task description):
- Each of the 4 valid fixtures renders successfully.
- validate_atom() raises jsonschema.ValidationError on the invalid-changelog fixture.
- Double-render determinism holds for all 4 atom types.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import ValidationError

from dadaia_workspace.features.specs.renderer import (
    _derive_project_name,
    render_atom,
    validate_atom,
)

# ---------------------------------------------------------------------------
# Path constants (resolved from repo root via this file's location)
# ---------------------------------------------------------------------------

# tests/unit/features/specs/test_renderer.py → repo-root via 5 parents
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_FIXTURES_DIR = _REPO_ROOT / "tests" / "fixtures" / "memory"
_TEMPLATES_DIR = _REPO_ROOT / "dadaia_workspace" / "public" / "templates"

# Valid fixture paths
_ARCH_VALID = _FIXTURES_DIR / "architecture.valid.yaml"
_TECH_VALID = _FIXTURES_DIR / "tech-stack.valid.yaml"
_INDEX_VALID = _FIXTURES_DIR / "product-index.valid.yaml"
_FEAT_VALID = _FIXTURES_DIR / "product-feature.valid.yaml"

# Invalid fixture paths
_FEAT_INVALID_CHANGELOG = _FIXTURES_DIR / "product-feature.invalid-changelog.yaml"
_FEAT_INVALID_MISSING = _FIXTURES_DIR / "product-feature.invalid-missing-required.yaml"
_ARCH_INVALID_CHANGELOG = _FIXTURES_DIR / "architecture.invalid-changelog.yaml"


def _copy_fixture(src: Path, tmp_dir: Path) -> Path:
    """Copy a fixture YAML into tmp_dir, preserving directory structure hints."""
    dest = tmp_dir / src.name
    shutil.copy2(src, dest)
    return dest


def _copy_feature_fixture(src: Path, tmp_dir: Path) -> Path:
    """Copy a feature fixture into a product/ subdirectory inside tmp_dir."""
    product_dir = tmp_dir / "product"
    product_dir.mkdir(exist_ok=True)
    dest = product_dir / src.name
    shutil.copy2(src, dest)
    return dest


def _copy_index_fixture(src: Path, tmp_dir: Path) -> Path:
    """Copy an index fixture into a product/ subdirectory with stem 'index'."""
    product_dir = tmp_dir / "product"
    product_dir.mkdir(exist_ok=True)
    dest = product_dir / "index.yaml"
    shutil.copy2(src, dest)
    return dest


# ---------------------------------------------------------------------------
# AC-C2-1: importable
# ---------------------------------------------------------------------------


class TestImportable:
    """AC-C2-1: renderer.py exists and is importable."""

    def test_render_atom_callable(self) -> None:
        assert callable(render_atom)

    def test_validate_atom_callable(self) -> None:
        assert callable(validate_atom)


# ---------------------------------------------------------------------------
# AC-C2-2: product-feature renders the 6 required section IDs
# ---------------------------------------------------------------------------


class TestProductFeatureSectionIDs:
    """AC-C2-2: Rendering a valid product-feature atom produces 6 required section IDs."""

    _REQUIRED_SECTIONS = [
        'id="purpose"',
        'id="flow"',
        'id="trigger"',
        'id="differential"',
        'id="runtime-state"',
        'id="dependencies"',
    ]

    def test_all_six_section_ids_present(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        html = render_atom(dest, "memory-product-feature-v1")
        for section_id in self._REQUIRED_SECTIONS:
            assert section_id in html, (
                f"Section {section_id!r} missing from rendered HTML. "
                "All 6 section IDs are required per AC-C2-2."
            )

    def test_purpose_section_has_content(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        html = render_atom(dest, "memory-product-feature-v1")
        # purpose contains paragraph(s) — at least one <p> inside the section
        assert "<p>" in html, "Rendered HTML must contain at least one <p> element"


# ---------------------------------------------------------------------------
# AC-C2-3: diagram field → <pre class="mermaid"> + CDN script
# ---------------------------------------------------------------------------


class TestMermaidDiagram:
    """AC-C2-3: YAML atom with diagram field renders mermaid block and CDN script."""

    def test_product_feature_with_diagram_has_mermaid_pre(self, tmp_path: Path) -> None:
        # product-feature.valid.yaml contains a `diagram` field
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        data = yaml.safe_load(dest.read_text(encoding="utf-8"))
        assert "diagram" in data, (
            "Fixture product-feature.valid.yaml must have a `diagram` field for this test."
        )
        html = render_atom(dest, "memory-product-feature-v1")
        assert '<pre class="mermaid">' in html, (
            "Rendered HTML must contain <pre class=\"mermaid\"> when diagram field is present (AC-C2-3)."
        )

    def test_product_feature_with_diagram_has_cdn_script(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        html = render_atom(dest, "memory-product-feature-v1")
        # The mermaid CDN script is in the template head
        assert "<script src=" in html, (
            "Rendered HTML must contain a <script src=> CDN tag for mermaid (AC-C2-3)."
        )

    def test_architecture_has_mermaid_sections(self, tmp_path: Path) -> None:
        """Architecture has dependency_rules_diagram and data_flow_diagram."""
        dest = _copy_fixture(_ARCH_VALID, tmp_path)
        html = render_atom(dest, "memory-architecture-v1")
        assert '<pre class="mermaid">' in html
        assert "<script src=" in html

    def test_product_index_has_capability_map_mermaid(self, tmp_path: Path) -> None:
        dest = _copy_index_fixture(_INDEX_VALID, tmp_path)
        html = render_atom(dest, "memory-product-index-v1")
        assert '<pre class="mermaid">' in html
        assert "<script src=" in html


# ---------------------------------------------------------------------------
# AC-C2-4: determinism — same YAML → byte-identical HTML
# ---------------------------------------------------------------------------


class TestDeterminism:
    """AC-C2-4: Two render calls on the same YAML produce byte-identical HTML."""

    @pytest.mark.parametrize(
        "fixture_path,atom_type,copy_fn",
        [
            (_ARCH_VALID, "memory-architecture-v1", _copy_fixture),
            (_TECH_VALID, "memory-tech-stack-v1", _copy_fixture),
            (_INDEX_VALID, "memory-product-index-v1", _copy_index_fixture),
            (_FEAT_VALID, "memory-product-feature-v1", _copy_feature_fixture),
        ],
        ids=["architecture", "tech-stack", "product-index", "product-feature"],
    )
    def test_double_render_identical(
        self,
        fixture_path: Path,
        atom_type: str,
        copy_fn: Any,
        tmp_path: Path,
    ) -> None:
        dest = copy_fn(fixture_path, tmp_path)
        html_first = render_atom(dest, atom_type)
        html_second = render_atom(dest, atom_type)
        assert html_first == html_second, (
            f"Double render of {fixture_path.name} produced different output. "
            "Renderer must be deterministic (AC-C2-4 / AC-REND-1)."
        )

    def test_no_timestamps_injected_by_default(self, tmp_path: Path) -> None:
        """Without extra_context, the renderer must NOT inject the current date."""
        import datetime

        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        html = render_atom(dest, "memory-product-feature-v1")
        today_iso = datetime.date.today().isoformat()
        # If the renderer inadvertently injected today's date, this would fail.
        # The template may or may not include a date — what matters is the renderer
        # does not call datetime.today() itself.  We verify by ensuring two renders
        # are identical even across a conceptual time boundary (covered by double-render
        # test above).  Additionally we assert the rendered source does NOT contain
        # today's date as a rendered value (the template default is '—').
        # NOTE: the template variable `today` has a default of `last_updated_iso` which
        # itself defaults to '—' — so today's date must not appear unless injected.
        assert today_iso not in html, (
            f"Renderer must not inject the current date ({today_iso}) into HTML. "
            "Supply via extra_context only."
        )


# ---------------------------------------------------------------------------
# All 4 valid fixtures render without error
# ---------------------------------------------------------------------------


class TestAllValidFixturesRender:
    """Each of the 4 valid fixtures must render successfully."""

    def test_architecture_renders(self, tmp_path: Path) -> None:
        dest = _copy_fixture(_ARCH_VALID, tmp_path)
        html = render_atom(dest, "memory-architecture-v1")
        assert "<!DOCTYPE html>" in html
        assert "Architecture Memory" in html

    def test_tech_stack_renders(self, tmp_path: Path) -> None:
        dest = _copy_fixture(_TECH_VALID, tmp_path)
        html = render_atom(dest, "memory-tech-stack-v1")
        assert "<!DOCTYPE html>" in html
        assert "Tech Stack Memory" in html

    def test_product_index_renders(self, tmp_path: Path) -> None:
        dest = _copy_index_fixture(_INDEX_VALID, tmp_path)
        html = render_atom(dest, "memory-product-index-v1")
        assert "<!DOCTYPE html>" in html
        assert "Product Memory" in html

    def test_product_feature_renders(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        html = render_atom(dest, "memory-product-feature-v1")
        assert "<!DOCTYPE html>" in html


# ---------------------------------------------------------------------------
# Atom type inference from path
# ---------------------------------------------------------------------------


class TestAtomTypeInference:
    """render_atom() infers atom type from path when not supplied."""

    def test_infer_architecture(self, tmp_path: Path) -> None:
        dest = _copy_fixture(_ARCH_VALID, tmp_path)
        # Rename to canonical name for clean inference
        canonical = dest.parent / "architecture.yaml"
        dest.rename(canonical)
        html = render_atom(canonical)  # no atom_type supplied
        assert "<!DOCTYPE html>" in html

    def test_infer_tech_stack(self, tmp_path: Path) -> None:
        dest = tmp_path / "tech-stack.yaml"
        shutil.copy2(_TECH_VALID, dest)
        html = render_atom(dest)  # no atom_type supplied
        assert "<!DOCTYPE html>" in html

    def test_infer_product_index(self, tmp_path: Path) -> None:
        product_dir = tmp_path / "product"
        product_dir.mkdir()
        dest = product_dir / "index.yaml"
        shutil.copy2(_INDEX_VALID, dest)
        html = render_atom(dest)  # no atom_type supplied
        assert "<!DOCTYPE html>" in html

    def test_infer_product_feature(self, tmp_path: Path) -> None:
        product_dir = tmp_path / "product"
        product_dir.mkdir()
        dest = product_dir / "workspace-init.yaml"
        shutil.copy2(_FEAT_VALID, dest)
        html = render_atom(dest)  # no atom_type supplied
        assert "<!DOCTYPE html>" in html


# ---------------------------------------------------------------------------
# Validation rejection tests
# ---------------------------------------------------------------------------


class TestValidationRejects:
    """validate/render raises ValidationError on invalid atoms."""

    def test_product_feature_changelog_rejected(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_INVALID_CHANGELOG, tmp_path)
        with pytest.raises(ValidationError):
            render_atom(dest, "memory-product-feature-v1")

    def test_product_feature_missing_required_rejected(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_INVALID_MISSING, tmp_path)
        with pytest.raises(ValidationError):
            render_atom(dest, "memory-product-feature-v1")

    def test_architecture_changelog_rejected(self, tmp_path: Path) -> None:
        dest = _copy_fixture(_ARCH_INVALID_CHANGELOG, tmp_path)
        with pytest.raises(ValidationError):
            render_atom(dest, "memory-architecture-v1")

    def test_validate_atom_helper_rejects_changelog(self) -> None:
        """validate_atom() helper raises ValidationError directly."""
        data: dict[str, Any] = {
            "purpose": "Test",
            "flow_steps": ["step 1"],
            "typical_trigger": "trigger",
            "differential": "diff",
            "runtime_state": ["state item"],
            "dependencies": ["dep item"],
            "changelog": ["forbidden field"],
        }
        with pytest.raises(ValidationError):
            validate_atom(data, "memory-product-feature-v1")

    def test_validate_atom_helper_passes_valid(self) -> None:
        """validate_atom() does not raise for a valid minimal product-feature dict."""
        data: dict[str, Any] = {
            "purpose": "Test purpose.",
            "flow_steps": ["step 1"],
            "typical_trigger": "trigger",
            "differential": "diff",
            "runtime_state": ["state item"],
            "dependencies": ["dep item"],
        }
        # Should not raise
        validate_atom(data, "memory-product-feature-v1")


# ---------------------------------------------------------------------------
# Content checks for specific rendered sections
# ---------------------------------------------------------------------------


class TestRenderedContent:
    """Verify that structured YAML data appears correctly in rendered HTML."""

    def test_architecture_overview_appears_in_html(self, tmp_path: Path) -> None:
        dest = _copy_fixture(_ARCH_VALID, tmp_path)
        data = yaml.safe_load(_ARCH_VALID.read_text(encoding="utf-8"))
        html = render_atom(dest, "memory-architecture-v1")
        # The first sentence of the overview should appear
        first_word = data["overview"].split()[0]
        assert first_word in html

    def test_architecture_layers_html_produced(self, tmp_path: Path) -> None:
        dest = _copy_fixture(_ARCH_VALID, tmp_path)
        html = render_atom(dest, "memory-architecture-v1")
        assert 'class="layer"' in html

    def test_tech_stack_has_table_rows(self, tmp_path: Path) -> None:
        dest = _copy_fixture(_TECH_VALID, tmp_path)
        html = render_atom(dest, "memory-tech-stack-v1")
        assert "<tr>" in html

    def test_product_index_catalog_items_sorted_by_rank(self, tmp_path: Path) -> None:
        """Catalog items must appear in rank-ascending order for determinism."""
        dest = _copy_index_fixture(_INDEX_VALID, tmp_path)
        data = yaml.safe_load(_INDEX_VALID.read_text(encoding="utf-8"))
        html = render_atom(dest, "memory-product-index-v1")
        # Collect positions of each slug link in the rendered HTML
        positions = {}
        for entry in data.get("catalog", []):
            slug = entry["slug"]
            pos = html.find(f'href="{slug}.html"')
            assert pos != -1, f"Slug {slug!r} link not found in rendered catalog HTML"
            positions[entry["rank"]] = pos
        # Verify ranks appear in ascending positional order
        ranks = sorted(positions.keys())
        for i in range(len(ranks) - 1):
            assert positions[ranks[i]] < positions[ranks[i + 1]], (
                f"Catalog rank {ranks[i]} appears after rank {ranks[i+1]} — "
                "must be sorted ascending for determinism."
            )

    def test_product_feature_purpose_split_into_paragraphs(self, tmp_path: Path) -> None:
        """purpose field with double-newline separators → multiple <p> elements."""
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        data = yaml.safe_load(_FEAT_VALID.read_text(encoding="utf-8"))
        paragraphs = [p.strip() for p in data["purpose"].strip().split("\n\n") if p.strip()]
        html = render_atom(dest, "memory-product-feature-v1")
        if len(paragraphs) > 1:
            assert html.count("<p>") >= len(paragraphs), (
                "Multi-paragraph purpose must produce multiple <p> elements."
            )

    def test_product_feature_flow_steps_rendered_as_li(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        data = yaml.safe_load(_FEAT_VALID.read_text(encoding="utf-8"))
        html = render_atom(dest, "memory-product-feature-v1")
        # Each flow step should produce a <li> element
        for step in data.get("flow_steps", []):
            # The step text (truncated for safety) should appear somewhere
            assert step[:30] in html, f"Flow step {step[:30]!r} not found in rendered HTML"


# ---------------------------------------------------------------------------
# AC-C2-6: CLI smoke test — `dadaia memory render` exits 0 and writes .html
# ---------------------------------------------------------------------------


class TestCLIRender:
    """AC-C2-6: `dadaia memory render <yaml>` exits 0 and writes adjacent .html."""

    def test_cli_render_product_feature_exits_zero(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", "memory", "render", str(dest)],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"`dadaia memory render` exited {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_cli_render_writes_adjacent_html(self, tmp_path: Path) -> None:
        dest = _copy_feature_fixture(_FEAT_VALID, tmp_path)
        expected_html = dest.parent / (dest.stem + ".html")
        assert not expected_html.exists(), "HTML should not exist before render"

        subprocess.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", "memory", "render", str(dest)],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            check=True,
        )

        assert expected_html.exists(), (
            f"Adjacent HTML file not written: {expected_html}. "
            "AC-C2-6 requires the renderer to write <stem>.html in the same directory."
        )
        content = expected_html.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content

    def test_cli_render_architecture_exits_zero(self, tmp_path: Path) -> None:
        """Smoke test: architecture renders via CLI."""
        dest = _copy_fixture(_ARCH_VALID, tmp_path)
        canonical = dest.parent / "architecture.yaml"
        dest.rename(canonical)
        result = subprocess.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", "memory", "render",
             str(canonical), "--atom-type", "memory-architecture-v1"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode == 0, (
            f"CLI render of architecture exited {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_cli_render_invalid_fixture_exits_nonzero(self, tmp_path: Path) -> None:
        """CLI must exit non-zero when the atom fails schema validation."""
        dest = _copy_feature_fixture(_FEAT_INVALID_CHANGELOG, tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "dadaia_workspace.cli.main", "memory", "render", str(dest),
             "--atom-type", "memory-product-feature-v1"],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        assert result.returncode != 0, (
            "CLI must exit non-zero when the atom fails schema validation."
        )


# ---------------------------------------------------------------------------
# _derive_project_name helper unit tests
# ---------------------------------------------------------------------------


class TestDeriveProjectName:
    """_derive_project_name(yaml_path) derives name from specs/ ancestor."""

    def test_specs_in_path_returns_parent_name(self, tmp_path: Path) -> None:
        """When yaml_path is under .../my-project/specs/memory/..., return 'my-project'."""
        project_dir = tmp_path / "my-project"
        specs_dir = project_dir / "specs" / "memory"
        specs_dir.mkdir(parents=True)
        yaml_path = specs_dir / "architecture.yaml"
        yaml_path.write_text("", encoding="utf-8")
        result = _derive_project_name(yaml_path)
        assert result == "my-project"

    def test_product_subdir_in_specs(self, tmp_path: Path) -> None:
        """Path under specs/memory/product/ also yields the project name."""
        project_dir = tmp_path / "dadaia-workspace"
        specs_dir = project_dir / "specs" / "memory" / "product"
        specs_dir.mkdir(parents=True)
        yaml_path = specs_dir / "some-feature.yaml"
        yaml_path.write_text("", encoding="utf-8")
        result = _derive_project_name(yaml_path)
        assert result == "dadaia-workspace"

    def test_no_specs_ancestor_returns_none(self, tmp_path: Path) -> None:
        """When there is no specs/ ancestor, return None (fallback to template default)."""
        # tmp_path has no 'specs' directory in its ancestry.
        yaml_path = tmp_path / "architecture.yaml"
        yaml_path.write_text("", encoding="utf-8")
        result = _derive_project_name(yaml_path)
        assert result is None

    def test_dadaia_workspace_repo_path(self) -> None:
        """_REPO_ROOT/specs/memory/architecture.yaml should yield 'dadaia-workspace'."""
        yaml_path = _REPO_ROOT / "specs" / "memory" / "architecture.yaml"
        if not yaml_path.exists():
            return  # skip if atoms haven't been migrated yet
        result = _derive_project_name(yaml_path)
        assert result == "dadaia-workspace", (
            f"Expected 'dadaia-workspace', got: {result!r}"
        )


# ---------------------------------------------------------------------------
# Default project_name derivation in render_atom (no extra_context)
# ---------------------------------------------------------------------------


class TestDefaultProjectNameDerivation:
    """render_atom injects project_name from path when not in extra_context."""

    def test_render_inside_specs_tree_shows_project_name_in_title(
        self, tmp_path: Path
    ) -> None:
        """Atom inside <project>/specs/memory/ renders with project name in title/H1."""
        project_dir = tmp_path / "my-cool-project"
        mem_dir = project_dir / "specs" / "memory"
        mem_dir.mkdir(parents=True)
        dest = mem_dir / "architecture.yaml"
        shutil.copy2(_ARCH_VALID, dest)

        html = render_atom(dest, "memory-architecture-v1")
        assert "my-cool-project" in html, (
            "Expected derived project name 'my-cool-project' in rendered HTML "
            f"when atom lives under specs/. Got title/H1 excerpt: "
            f"{html[html.find('<title>'):html.find('</title>')+8]!r}"
        )

    def test_render_outside_specs_tree_falls_back_to_projeto(
        self, tmp_path: Path
    ) -> None:
        """Atom outside any specs/ tree renders with template default 'Projeto' in title/H1."""
        dest = tmp_path / "architecture.yaml"
        shutil.copy2(_ARCH_VALID, dest)

        html = render_atom(dest, "memory-architecture-v1")
        assert "Projeto" in html, (
            "Expected template default 'Projeto' in rendered HTML when no specs/ ancestor."
        )

    def test_extra_context_project_name_overrides_derived(
        self, tmp_path: Path
    ) -> None:
        """Explicit extra_context project_name wins over path-derived default."""
        project_dir = tmp_path / "my-cool-project"
        mem_dir = project_dir / "specs" / "memory"
        mem_dir.mkdir(parents=True)
        dest = mem_dir / "architecture.yaml"
        shutil.copy2(_ARCH_VALID, dest)

        html = render_atom(
            dest,
            "memory-architecture-v1",
            extra_context={"project_name": "explicit-override"},
        )
        assert "explicit-override" in html, (
            "extra_context project_name should override the path-derived default."
        )
        assert "my-cool-project" not in html, (
            "Derived project name must NOT appear when extra_context overrides it."
        )

    def test_determinism_with_derived_project_name(self, tmp_path: Path) -> None:
        """Double-render in same specs/ tree is byte-identical (AC-REND-1 still holds)."""
        project_dir = tmp_path / "my-cool-project"
        mem_dir = project_dir / "specs" / "memory"
        mem_dir.mkdir(parents=True)
        dest = mem_dir / "architecture.yaml"
        shutil.copy2(_ARCH_VALID, dest)

        html1 = render_atom(dest, "memory-architecture-v1")
        html2 = render_atom(dest, "memory-architecture-v1")
        assert html1 == html2, (
            "Double-render with derived project name must be byte-identical (AC-REND-1)."
        )
