"""Unit tests for dadaia_workspace.features.specs.catalog (T-MCE-01).

Adapted for memory-markdown-source-v1: catalog.py now reads YAML frontmatter
from *.md feature atom files (not index.html scraping).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.catalog import (
    generate_catalog,
    render_index_md,
    write_catalog,
    write_index,
)

# ---------------------------------------------------------------------------
# Helpers — build .md atoms with frontmatter
# ---------------------------------------------------------------------------

_FRONTMATTER_TEMPLATE = """\
---
slug: {slug}
title: {title}
category: product
tldr: '{tldr}'
summary: '{summary}'
tags: {tags}
agent_tier: self-pull
token_estimate: 100
last_updated: '2026-06-01'
release_origin: test-release
---

## Propósito

{purpose}
"""

_ATOMS_3 = [
    {
        "slug": "workspace-init",
        "title": "workspace-init",
        "tldr": "entry point; creates .dadaia/.",
        "summary": "entry point; creates .dadaia/.",
        "tags": "[]",
        "purpose": "Bootstraps the workspace.",
    },
    {
        "slug": "context-management",
        "title": "context-management",
        "tldr": "multi-context lifecycle.",
        "summary": "multi-context lifecycle.",
        "tags": "[]",
        "purpose": "Manages contexts.",
    },
    {
        "slug": "specs-doctor",
        "title": "specs-doctor",
        "tldr": "structural validation checks.",
        "summary": "structural validation checks.",
        "tags": "[]",
        "purpose": "Validates specs.",
    },
]


def _write_atom(product_dir: Path, atom: dict[str, str]) -> Path:
    md_path = product_dir / f"{atom['slug']}.md"
    md_path.write_text(_FRONTMATTER_TEMPLATE.format(**atom), encoding="utf-8")
    return md_path


def _make_specs_dir(tmp_path: Path, atoms: list[dict[str, str]] | None = None) -> Path:
    """Create a minimal specs/ directory with .md feature atom files."""
    specs = tmp_path / "specs"
    product_dir = specs / "memory" / "product"
    product_dir.mkdir(parents=True)
    for atom in atoms or _ATOMS_3:
        _write_atom(product_dir, atom)
    return specs


# ---------------------------------------------------------------------------
# T-MCE-01-1: Valid parse produces N entries with all required fields
# ---------------------------------------------------------------------------


class TestGenerateCatalogValidParse:
    def test_returns_dict_with_envelope_fields(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)

        assert isinstance(catalog, dict)
        assert "generated_at" in catalog
        assert "context" in catalog
        assert "features" in catalog

    def test_generated_at_is_iso8601_utc(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime

        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        ts = catalog["generated_at"]
        parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        assert parsed is not None

    def test_context_is_parent_directory_name(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        specs = project_dir / "specs"
        product_dir = specs / "memory" / "product"
        product_dir.mkdir(parents=True)
        for atom in _ATOMS_3:
            _write_atom(product_dir, atom)
        catalog = generate_catalog(specs)
        assert catalog["context"] == "my-project"

    def test_three_entries_parsed(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        assert len(catalog["features"]) == 3

    def test_each_entry_has_all_required_fields(self, tmp_path: Path) -> None:
        required_fields = {
            "rank",
            "slug",
            "title",
            "category",
            "tldr",
            "summary",
            "path",
            "tags",
            "token_estimate",
            "agent_tier",
            "depends_on",
        }
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        for entry in catalog["features"]:
            assert set(entry.keys()) >= required_fields, (
                f"Entry is missing fields: {required_fields - set(entry.keys())}"
            )

    def test_rank_is_one_based_and_sequential(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        for i, entry in enumerate(features, start=1):
            assert entry["rank"] == i

    def test_tags_and_depends_on_are_lists(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        for entry in features:
            assert isinstance(entry["tags"], list)
            assert isinstance(entry["depends_on"], list)

    def test_result_is_json_serialisable(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        serialised = json.dumps(catalog)
        reparsed = json.loads(serialised)
        assert reparsed["features"][0]["rank"] == 1


# ---------------------------------------------------------------------------
# T-MCE-01-2: slug ↔ path stem consistency
# ---------------------------------------------------------------------------


class TestSlugPathConsistency:
    def test_slug_matches_frontmatter_slug(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        expected_slugs = sorted(a["slug"] for a in _ATOMS_3)
        actual_slugs = sorted(e["slug"] for e in features)
        assert actual_slugs == expected_slugs

    def test_path_contains_slug(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        for entry in features:
            assert entry["path"].endswith(f"/{entry['slug']}.md"), (
                f"path {entry['path']!r} does not end with /{entry['slug']}.md"
            )

    def test_path_prefix_is_specs_memory_product(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        for entry in features:
            assert entry["path"].startswith("specs/memory/product/"), (
                f"path {entry['path']!r} does not start with 'specs/memory/product/'"
            )

    def test_path_stem_equals_slug(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        for entry in features:
            stem = Path(entry["path"]).stem
            assert stem == entry["slug"], (
                f"Path stem {stem!r} does not match slug {entry['slug']!r}"
            )


# ---------------------------------------------------------------------------
# T-MCE-01-3: Missing product directory → clear error
# ---------------------------------------------------------------------------


class TestMissingProductDir:
    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        with pytest.raises(FileNotFoundError):
            generate_catalog(specs)

    def test_error_message_includes_product(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        with pytest.raises(FileNotFoundError) as exc_info:
            generate_catalog(specs)
        assert "product" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# T-MCE-01-4: Empty product/ → empty features list
# ---------------------------------------------------------------------------


class TestEmptyCatalog:
    def test_empty_product_dir_produces_empty_features(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        product_dir = specs / "memory" / "product"
        product_dir.mkdir(parents=True)
        # Write only index.md (which is excluded from feature discovery)
        (product_dir / "index.md").write_text(
            "---\nslug: index\n---\n\n## Index\n", encoding="utf-8"
        )
        catalog = generate_catalog(specs)
        assert catalog["features"] == []

    def test_envelope_fields_still_present_when_empty(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        product_dir = specs / "memory" / "product"
        product_dir.mkdir(parents=True)
        catalog = generate_catalog(specs)
        assert "generated_at" in catalog
        assert "context" in catalog
        assert catalog["features"] == []


# ---------------------------------------------------------------------------
# T-MCE-01-5: write_catalog — output path and JSON validity
# ---------------------------------------------------------------------------


class TestWriteCatalog:
    def test_writes_to_correct_path(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        out_path = write_catalog(specs, catalog)
        expected = specs / "memory" / "product" / "catalog.json"
        assert out_path == expected
        assert out_path.exists()

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        out_path = write_catalog(specs, catalog)
        reparsed = json.loads(out_path.read_text(encoding="utf-8"))
        first_slug = reparsed["features"][0]["slug"]
        assert first_slug in {a["slug"] for a in _ATOMS_3}

    def test_output_ends_with_newline(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        out_path = write_catalog(specs, catalog)
        raw = out_path.read_bytes()
        assert raw.endswith(b"\n"), "catalog.json must end with a trailing newline"

    def test_idempotent_overwrite(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        out1 = write_catalog(specs, catalog)
        out2 = write_catalog(specs, catalog)
        assert out1 == out2
        reparsed = json.loads(out1.read_text(encoding="utf-8"))
        assert len(reparsed["features"]) == 3

    def test_no_trailing_commas_in_json(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        out_path = write_catalog(specs, catalog)
        parsed = json.loads(out_path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# T-PIO-10 (F10): the CLI catalog path must ALSO emit index.md (single source).
# Closes bug memory-catalog-cli-skips-index-md.
# ---------------------------------------------------------------------------


class TestIndexMdParity:
    def test_render_index_md_contains_all_slugs(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        index_md = render_index_md(catalog)
        for atom in _ATOMS_3:
            assert atom["slug"] in index_md, f"slug {atom['slug']} missing from index.md"

    def test_render_index_md_uses_catalog_tldr(self, tmp_path: Path) -> None:
        """index.md rows are sourced from the catalog (single source of truth)."""
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        index_md = render_index_md(catalog)
        for feature in catalog["features"]:
            assert feature["tldr"] in index_md, (
                f"index.md row for {feature['slug']} does not carry catalog tldr"
            )

    def test_write_index_writes_to_product_index_md(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        out_path = write_index(specs, catalog)
        expected = specs / "memory" / "product" / "index.md"
        assert out_path == expected
        assert out_path.exists()
        assert out_path.read_text(encoding="utf-8").endswith("\n")

    def test_cli_generate_emits_both_catalog_and_index(self, tmp_path: Path) -> None:
        """`dadaia memory catalog generate` writes BOTH catalog.json and index.md.

        This is the regression the bug describes: the CLI used to write only
        catalog.json, letting index.md silently drift. Both must now be emitted from
        the same atom-frontmatter source, and the index must reflect the catalog tldr.
        """
        from typer.testing import CliRunner

        from dadaia_workspace.cli.commands.memory import app as memory_app

        specs = _make_specs_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(memory_app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert result.exit_code == 0, result.output

        catalog_path = specs / "memory" / "product" / "catalog.json"
        index_path = specs / "memory" / "product" / "index.md"
        assert catalog_path.exists(), "catalog.json must be written"
        assert index_path.exists(), "index.md must ALSO be written (bug fix)"

        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        index_text = index_path.read_text(encoding="utf-8")
        for feature in catalog["features"]:
            assert feature["tldr"] in index_text, (
                f"index.md is out of sync with catalog for {feature['slug']}"
            )


# ---------------------------------------------------------------------------
# T-MCE-RGLOB: Regression — atoms in subdirectories ARE discovered (rglob fix)
#
# This test FAILS against the old glob("*.md") implementation and
# PASSES with the rglob("*.md") fix.
# ---------------------------------------------------------------------------


class TestSubdirectoryAtomDiscovery:
    """Regression test for the catalog-empty bug.

    Before the fix, product_dir.glob("*.md") only matched direct children of
    specs/memory/product/, missing ALL atoms stored in subdirectories
    (agents/, sdd/, platform/, distribution/, panel/, philosophy/).
    The fix uses rglob("*.md") to recurse into subdirectories.
    """

    def _write_subdir_atom(self, product_dir: Path, subdir: str, slug: str) -> Path:
        """Write a valid atom .md file inside product_dir/<subdir>/."""
        atom_dir = product_dir / subdir
        atom_dir.mkdir(parents=True, exist_ok=True)
        md_path = atom_dir / f"{slug}.md"
        md_path.write_text(
            _FRONTMATTER_TEMPLATE.format(
                slug=slug,
                title=slug,
                tldr=f"{slug} feature.",
                summary=f"{slug} summary.",
                tags="[]",
                purpose=f"Describes {slug}.",
            ),
            encoding="utf-8",
        )
        return md_path

    def test_subdir_atom_is_in_catalog(self, tmp_path: Path) -> None:
        """An atom in a subdirectory must appear in the generated catalog."""
        specs = tmp_path / "specs"
        product_dir = specs / "memory" / "product"
        product_dir.mkdir(parents=True)

        # index.md at root must be excluded
        (product_dir / "index.md").write_text(
            "---\nslug: index\ntitle: index\ncategory: core\ntldr: index\nsummary: index\n"
            "tags: []\nagent_tier: inject\ntoken_estimate: 0\n---\n\n## Index\n",
            encoding="utf-8",
        )

        # One atom directly at root (ensures root atoms still work)
        _write_atom(
            product_dir,
            {
                "slug": "workspace-init",
                "title": "workspace-init",
                "tldr": "root-level atom.",
                "summary": "root-level atom.",
                "tags": "[]",
                "purpose": "Root atom.",
            },
        )

        # One atom in a subdirectory (the case that was broken)
        self._write_subdir_atom(product_dir, "philosophy", "spec-context-project")

        catalog = generate_catalog(specs)
        slugs = {f["slug"] for f in catalog["features"]}

        # Subdir atom MUST be found
        assert "spec-context-project" in slugs, (
            "spec-context-project in philosophy/ subdir was not discovered; "
            "glob('*.md') only matches direct children — use rglob('*.md')"
        )
        # Root atom still present
        assert "workspace-init" in slugs
        # index.md excluded at every depth
        assert "index" not in slugs

    def test_index_md_excluded_at_any_depth(self, tmp_path: Path) -> None:
        """index.md files are excluded whether at root or in a subdirectory."""
        specs = tmp_path / "specs"
        product_dir = specs / "memory" / "product"
        product_dir.mkdir(parents=True)

        # index.md at root
        (product_dir / "index.md").write_text(
            "---\nslug: index\ntitle: index\ncategory: core\ntldr: t\nsummary: s\n"
            "tags: []\nagent_tier: inject\ntoken_estimate: 0\n---\n\n## Index\n",
            encoding="utf-8",
        )
        # index.md inside a subdir (should also be excluded)
        subdir = product_dir / "philosophy"
        subdir.mkdir()
        (subdir / "index.md").write_text(
            "---\nslug: index\ntitle: index\ncategory: core\ntldr: t\nsummary: s\n"
            "tags: []\nagent_tier: inject\ntoken_estimate: 0\n---\n\n## Subdir index\n",
            encoding="utf-8",
        )
        # A real atom in the subdir
        self._write_subdir_atom(product_dir, "philosophy", "spec-context-project")

        catalog = generate_catalog(specs)
        slugs = {f["slug"] for f in catalog["features"]}

        assert "index" not in slugs, "index.md must be excluded at every depth"
        assert "spec-context-project" in slugs

    def test_subdir_atom_rel_path_is_correct(self, tmp_path: Path) -> None:
        """rel_path for a subdirectory atom is specs/memory/product/<subdir>/<slug>.md."""
        specs = tmp_path / "specs"
        product_dir = specs / "memory" / "product"
        product_dir.mkdir(parents=True)

        self._write_subdir_atom(product_dir, "philosophy", "spec-context-project")

        catalog = generate_catalog(specs)
        assert len(catalog["features"]) == 1

        entry = catalog["features"][0]
        expected_path = "specs/memory/product/philosophy/spec-context-project.md"
        assert entry["path"] == expected_path, (
            f"Expected rel_path {expected_path!r}, got {entry['path']!r}"
        )

    def test_multiple_subdirs_all_discovered(self, tmp_path: Path) -> None:
        """Atoms in multiple subdirectories (agents/, sdd/, platform/) are all found."""
        specs = tmp_path / "specs"
        product_dir = specs / "memory" / "product"
        product_dir.mkdir(parents=True)

        subdirs_and_slugs = [
            ("agents", "agent-orchestration"),
            ("sdd", "specs-doctor"),
            ("platform", "workspace-init"),
            ("philosophy", "spec-context-project"),
        ]
        for subdir, slug in subdirs_and_slugs:
            self._write_subdir_atom(product_dir, subdir, slug)

        catalog = generate_catalog(specs)
        slugs = {f["slug"] for f in catalog["features"]}

        for _, slug in subdirs_and_slugs:
            assert slug in slugs, f"Atom {slug!r} from subdir was not discovered"

        assert len(catalog["features"]) == len(subdirs_and_slugs)
