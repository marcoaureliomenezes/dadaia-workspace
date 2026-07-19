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


def _write_subdir_atom(product_dir: Path, subdir: str, slug: str) -> Path:
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


def _make_specs_dir(tmp_path: Path, atoms: list[dict[str, str]] | None = None) -> Path:
    """Create a minimal specs/ directory with .md feature atom files."""
    specs = tmp_path / "specs"
    product_dir = specs / "memory" / "product"
    product_dir.mkdir(parents=True)
    for atom in atoms or _ATOMS_3:
        _write_atom(product_dir, atom)
    return specs


# ---------------------------------------------------------------------------
# Entry parsing + slug/path consistency — 1 test
# ---------------------------------------------------------------------------


def test_entry_parsing_and_slug_path_consistency(tmp_path: Path) -> None:
    specs = _make_specs_dir(tmp_path)
    catalog = generate_catalog(specs)
    features = catalog["features"]

    assert isinstance(catalog, dict)
    assert "generated_at" in catalog and "context" in catalog and "features" in catalog
    assert len(features) == 3

    # context = parent directory name.
    assert catalog["context"] == tmp_path.name

    # every entry carries the required field set; agent_tier is NOT emitted (v0.1.53 FR3 drop).
    required_fields = {
        "rank",
        "slug",
        "title",
        "category",
        "area",
        "tldr",
        "summary",
        "path",
        "tags",
        "token_estimate",
        "depends_on",
    }
    for entry in features:
        assert set(entry.keys()) >= required_fields
        assert "agent_tier" not in entry

    # rank is 1-based and sequential.
    for i, entry in enumerate(features, start=1):
        assert entry["rank"] == i

    # slug ↔ path stem consistency.
    expected_slugs = sorted(a["slug"] for a in _ATOMS_3)
    actual_slugs = sorted(e["slug"] for e in features)
    assert actual_slugs == expected_slugs
    for entry in features:
        assert entry["path"].endswith(f"/{entry['slug']}.md")
        assert entry["path"].startswith("specs/memory/product/")
        assert Path(entry["path"]).stem == entry["slug"]

    # Missing product dir → clear FileNotFoundError, error message names it.
    empty_specs = tmp_path.parent / (tmp_path.name + "-missing") / "specs"
    empty_specs.mkdir(parents=True)
    with pytest.raises(FileNotFoundError) as exc_info:
        generate_catalog(empty_specs)
    assert "product" in str(exc_info.value).lower()

    # Empty product/ → empty features list, envelope still present.
    bare_specs = tmp_path.parent / (tmp_path.name + "-bare") / "specs"
    (bare_specs / "memory" / "product").mkdir(parents=True)
    empty_catalog = generate_catalog(bare_specs)
    assert "generated_at" in empty_catalog and "context" in empty_catalog
    assert empty_catalog["features"] == []


# ---------------------------------------------------------------------------
# Subdirectory discovery + area derivation — 1 test
# ---------------------------------------------------------------------------


def test_subdirectory_discovery_and_area_derivation(tmp_path: Path) -> None:
    """Regression for the catalog-empty bug: product_dir.glob('*.md') only matched
    direct children; the fix uses rglob('*.md') to recurse into subdirectories.
    F-75 (v0.1.48 W3): `area` = the atom's parent directory name under product/
    ('product' at root)."""
    specs = tmp_path / "specs"
    product_dir = specs / "memory" / "product"
    product_dir.mkdir(parents=True)

    # index.md at root AND at a subdirectory depth must be excluded at every depth.
    (product_dir / "index.md").write_text(
        "---\nslug: index\ntitle: index\ncategory: core\ntldr: t\nsummary: s\n"
        "tags: []\nagent_tier: inject\ntoken_estimate: 0\n---\n\n## Index\n",
        encoding="utf-8",
    )
    subdir = product_dir / "philosophy"
    subdir.mkdir()
    (subdir / "index.md").write_text(
        "---\nslug: index\ntitle: index\ncategory: core\ntldr: t\nsummary: s\n"
        "tags: []\nagent_tier: inject\ntoken_estimate: 0\n---\n\n## Subdir index\n",
        encoding="utf-8",
    )

    # A root atom, and atoms in multiple subdirectories.
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
    subdirs_and_slugs = [
        ("agents", "agent-orchestration"),
        ("sdd", "specs-doctor"),
        ("platform", "workspace-init-2"),
        ("philosophy", "spec-context-project"),
    ]
    for sd, slug in subdirs_and_slugs:
        _write_subdir_atom(product_dir, sd, slug)

    catalog = generate_catalog(specs)
    slugs = {f["slug"] for f in catalog["features"]}
    by_slug = {f["slug"]: f for f in catalog["features"]}

    # Every subdir atom discovered; root atom still present; index.md excluded at every depth.
    for _, slug in subdirs_and_slugs:
        assert slug in slugs, f"Atom {slug!r} from subdir was not discovered"
    assert "workspace-init" in slugs
    assert "index" not in slugs
    assert len(catalog["features"]) == 1 + len(subdirs_and_slugs)

    # rel_path for a subdirectory atom is specs/memory/product/<subdir>/<slug>.md.
    assert (
        by_slug["spec-context-project"]["path"]
        == "specs/memory/product/philosophy/spec-context-project.md"
    )

    # area derivation: root atom's area is "product"; subdir atoms use the parent dir name;
    # area is a separate field and does not override category.
    assert by_slug["workspace-init"]["area"] == "product"
    assert by_slug["specs-doctor"]["area"] == "sdd"
    assert by_slug["spec-context-project"]["area"] == "philosophy"
    assert by_slug["specs-doctor"]["category"] == "product"

    # index.md groups by area, not a single "product" bucket.
    index_md = render_index_md(catalog)
    assert "## Catálogo de features" in index_md
    assert "### sdd" in index_md
    assert "### platform" in index_md


# ---------------------------------------------------------------------------
# write/idempotence/error — 1 test
# ---------------------------------------------------------------------------


def test_write_catalog_and_index_idempotent(tmp_path: Path) -> None:
    specs = _make_specs_dir(tmp_path)
    catalog = generate_catalog(specs)

    out1 = write_catalog(specs, catalog)
    expected = specs / "memory" / "product" / "catalog.json"
    assert out1 == expected
    assert out1.exists()
    reparsed = json.loads(out1.read_text(encoding="utf-8"))
    assert reparsed["features"][0]["slug"] in {a["slug"] for a in _ATOMS_3}

    # Idempotent overwrite.
    out2 = write_catalog(specs, catalog)
    assert out1 == out2
    reparsed2 = json.loads(out2.read_text(encoding="utf-8"))
    assert len(reparsed2["features"]) == 3

    # index.md: every catalog slug/tldr present, correct target path.
    index_md = render_index_md(catalog)
    for atom in _ATOMS_3:
        assert atom["slug"] in index_md
    for feature in catalog["features"]:
        assert feature["tldr"] in index_md

    index_path = write_index(specs, catalog)
    expected_index = specs / "memory" / "product" / "index.md"
    assert index_path == expected_index
    assert index_path.exists()


# ---------------------------------------------------------------------------
# T-PIO-10 (F10): CLI generate emits BOTH catalog.json and index.md — kept
# ---------------------------------------------------------------------------


def test_cli_generate_emits_both_catalog_and_index(tmp_path: Path) -> None:
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


# ── bug closure-breaks-canonical-backlog-anchor (Hermes real game cycle) ────────────
#
# `memory catalog generate` used to REPLACE index.md wholesale with a template whose
# headings differ from the scaffold's — destroying canonical doc anchors
# (memory/product/index.md#Catálogo de features) that accepted backlog intents bind.
# Regeneration now surgically updates ONLY the `## Catálogo de features` section and
# preserves every other heading/anchor; a fresh file is born with the canonical heading.


def _scaffold_index(specs_dir) -> str:
    text = (
        "---\nslug: index\ntitle: Catálogo de Produtos\ncategory: product\n---\n\n"
        "## Visão atômica\n\nVisão do produto.\n\n"
        "## Usuários\n\n| Usuário | Descrição |\n|---|---|\n| dev | usa |\n\n"
        "## Catálogo de features\n\n"
        "| Slug | Título | TL;DR |\n|------|--------|-------|\n"
        "| placeholder | placeholder | placeholder |\n\n"
        "## Mapa de capacidades\n\nmapa\n\n"
        "## Limites conhecidos\n\nnenhum\n"
    )
    out = specs_dir / "memory" / "product" / "index.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return text


def test_write_index_preserves_existing_headings_and_updates_catalog_section(
    tmp_path,
) -> None:
    from dadaia_workspace.features.specs.catalog import write_index

    specs = tmp_path / "specs"
    _scaffold_index(specs)
    catalog = {
        "context": "valgame",
        "features": [{"slug": "ttt", "title": "Tic Tac Toe", "tldr": "CLI game", "area": "core"}],
    }

    write_index(specs, catalog)

    text = (specs / "memory" / "product" / "index.md").read_text(encoding="utf-8")
    # Every pre-existing heading/anchor survives regeneration.
    for heading in (
        "## Visão atômica",
        "## Usuários",
        "## Catálogo de features",
        "## Mapa de capacidades",
        "## Limites conhecidos",
    ):
        assert heading in text, heading
    # The catalog section carries the regenerated table (placeholder gone).
    assert "`ttt`" in text
    assert "| placeholder | placeholder | placeholder |" not in text
    # Section order intact: catalog table sits between Usuários and Mapa.
    assert text.index("## Usuários") < text.index("`ttt`") < text.index("## Mapa de capacidades")


def test_write_index_fresh_file_carries_canonical_catalog_heading(tmp_path) -> None:
    from dadaia_workspace.features.specs.catalog import write_index

    specs = tmp_path / "specs"
    catalog = {"context": "valgame", "features": []}

    write_index(specs, catalog)

    text = (specs / "memory" / "product" / "index.md").read_text(encoding="utf-8")
    assert "## Catálogo de features" in text
