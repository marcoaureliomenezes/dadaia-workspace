"""Integration tests for dadaia_workspace/public/scripts/generate-memory-catalog.py.

Coverage:
  - Empty product dir → empty features list (exit 0)
  - Single atom → catalog with 1 entry, correct shape
  - Multiple atoms → catalog with N entries, ranks 1..N
  - Missing required frontmatter field → error, no catalog written
  - catalog.json output matches expected schema shape
  - depends_on derived from [[slug]] wikilinks in body
  - index.md generated with correct TOC
  - Idempotent: running twice produces same output (except generated_at timestamp)
  - subprocess integration: exit 0 for valid dir; exit 1 for bad frontmatter
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]

# ---------------------------------------------------------------------------
# Locate the script
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts" / "generate-memory-catalog.py"

# ---------------------------------------------------------------------------
# Import module
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location("generate_memory_catalog", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_catalog_mod: types.ModuleType = importlib.util.module_from_spec(_spec)
# Disable bytecode writing across exec_module: CPython's SourceFileLoader decides to
# write the cached .pyc based on sys.dont_write_bytecode at exec time, BEFORE the
# script's own in-module guard line runs — so without this the import pollutes
# dadaia_workspace/public/scripts/__pycache__/ and trips the public-source-hygiene
# contract under full-suite ordering (bug public-source-hygiene-flaky-pycache-pollution).
_prev_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    _spec.loader.exec_module(_catalog_mod)  # type: ignore[union-attr]
finally:
    sys.dont_write_bytecode = _prev_dont_write_bytecode

generate_catalog = _catalog_mod.generate_catalog
generate_index_md = _catalog_mod.generate_index_md
main = _catalog_mod.main

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_FM: dict[str, Any] = {
    "slug": "PLACEHOLDER",
    "title": "Test Feature",
    "category": "product",
    "tldr": "Short description under 160 chars.",
    "summary": "One-sentence summary.",
    "tags": ["test"],
    "agent_tier": "self-pull",
    "token_estimate": 50,
    "last_updated": "2026-06-01",
    "release_origin": "memory-markdown-source-v1",
}


def _make_product_atom(
    product_dir: Path,
    slug: str,
    body: str = "## Propósito\n\nBody.\n",
    fm_overrides: dict[str, Any] | None = None,
    extra_fm: dict[str, Any] | None = None,
) -> Path:
    """Write a minimal valid product atom .md file."""
    fm = {**_REQUIRED_FM, "slug": slug}
    if fm_overrides:
        fm.update(fm_overrides)
    if extra_fm:
        fm.update(extra_fm)

    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v!r}")
    lines.append("---")
    lines.append("")
    content = "\n".join(lines) + "\n" + body

    md_path = product_dir / f"{slug}.md"
    md_path.write_text(content, encoding="utf-8")
    return md_path


def _make_memory_dir(tmp_path: Path) -> tuple[Path, Path]:
    """Create a memory_dir/product/ structure and return (memory_dir, product_dir)."""
    memory_dir = tmp_path / "memory"
    product_dir = memory_dir / "product"
    product_dir.mkdir(parents=True)
    return memory_dir, product_dir


# ---------------------------------------------------------------------------
# Test: empty product dir
# ---------------------------------------------------------------------------


def test_empty_product_dir_returns_empty_catalog(tmp_path: Path) -> None:
    """generate_catalog on an empty product/ dir returns an empty features list."""
    memory_dir, _ = _make_memory_dir(tmp_path)

    catalog, errors = generate_catalog(memory_dir)

    assert not errors, f"Unexpected errors: {errors}"
    assert catalog is not None
    assert catalog["features"] == []


# ---------------------------------------------------------------------------
# Test: single atom
# ---------------------------------------------------------------------------


def test_single_atom_catalog_shape(tmp_path: Path) -> None:
    """Single atom produces catalog with 1 entry matching the expected shape."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="workspace-init")

    catalog, errors = generate_catalog(memory_dir)

    assert not errors, f"Unexpected errors: {errors}"
    assert catalog is not None
    features = catalog["features"]
    assert len(features) == 1

    feat = features[0]
    assert feat["slug"] == "workspace-init"
    assert feat["title"] == "Test Feature"
    assert feat["category"] == "product"
    assert feat["area"] == "product", "top-level product/ atom must carry area='product'"
    assert feat["tldr"] == "Short description under 160 chars."
    assert feat["summary"] == "One-sentence summary."
    assert feat["tags"] == ["test"]
    assert feat["token_estimate"] == 50
    # agent_tier is dropped from catalog output in v0.1.53 (FR3): the input frontmatter
    # still carries it (schema-tolerated), but the renderer must not surface it.
    assert "agent_tier" not in feat
    assert feat["rank"] == 1
    assert feat["depends_on"] == []
    assert "path" in feat
    assert feat["path"].endswith("workspace-init.md")


def test_catalog_top_level_keys(tmp_path: Path) -> None:
    """Catalog dict has required top-level keys."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="test-feature")

    catalog, errors = generate_catalog(memory_dir, context="my-workspace")

    assert not errors
    assert catalog is not None
    assert "generated_at" in catalog
    assert catalog["context"] == "my-workspace"
    assert "features" in catalog


# ---------------------------------------------------------------------------
# Test: multiple atoms
# ---------------------------------------------------------------------------


def test_multiple_atoms_ranks(tmp_path: Path) -> None:
    """Multiple atoms get sequential ranks 1..N (sorted by filename)."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="aaa-feature")
    _make_product_atom(product_dir, slug="bbb-feature")
    _make_product_atom(product_dir, slug="ccc-feature")

    catalog, errors = generate_catalog(memory_dir)

    assert not errors
    assert catalog is not None
    features = catalog["features"]
    assert len(features) == 3
    # Files are sorted alphabetically by the glob
    slugs = [f["slug"] for f in features]
    assert slugs == sorted(slugs)
    ranks = [f["rank"] for f in features]
    assert ranks == [1, 2, 3]


# ---------------------------------------------------------------------------
# Test: missing required frontmatter field
# ---------------------------------------------------------------------------


def test_missing_required_field_returns_error(tmp_path: Path) -> None:
    """Missing a required frontmatter field causes generate_catalog to return errors."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)

    # Atom missing 'title'
    content = (
        "---\n"
        "slug: test-feature\n"
        # 'title' is missing
        "category: product\n"
        "tldr: Short.\n"
        "summary: Summary.\n"
        "tags:\n  - test\n"
        "agent_tier: self-pull\n"
        "token_estimate: 50\n"
        "last_updated: '2026-06-01'\n"
        "release_origin: memory-markdown-source-v1\n"
        "---\n"
        "\n"
        "## Propósito\n\nBody.\n"
    )
    (product_dir / "test-feature.md").write_text(content, encoding="utf-8")

    catalog, errors = generate_catalog(memory_dir)

    assert catalog is None, "Catalog should be None when there are errors"
    assert errors, "Expected at least one error"
    assert any("title" in e.lower() or "required" in e.lower() for e in errors), (
        f"Error should mention missing field. Got: {errors}"
    )


# ---------------------------------------------------------------------------
# Test: depends_on from wikilinks
# ---------------------------------------------------------------------------


def test_depends_on_from_wikilinks(tmp_path: Path) -> None:
    """depends_on is populated from [[slug]] wikilinks in the body."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(
        product_dir,
        slug="feature-a",
        body="## Propósito\n\nSee [[feature-b]] and [[feature-c]] for context.\n",
    )
    # Also create the target atoms
    _make_product_atom(product_dir, slug="feature-b")
    _make_product_atom(product_dir, slug="feature-c")

    catalog, errors = generate_catalog(memory_dir)

    assert not errors, f"Unexpected errors: {errors}"
    assert catalog is not None

    feat_a = next(f for f in catalog["features"] if f["slug"] == "feature-a")
    assert set(feat_a["depends_on"]) == {"feature-b", "feature-c"}


def test_depends_on_empty_when_no_wikilinks(tmp_path: Path) -> None:
    """depends_on is empty when no wikilinks are present in the body."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="standalone")

    catalog, errors = generate_catalog(memory_dir)

    assert not errors
    assert catalog is not None
    feat = catalog["features"][0]
    assert feat["depends_on"] == []


def test_depends_on_deduplicates_wikilinks(tmp_path: Path) -> None:
    """Duplicate wikilinks in the body appear only once in depends_on."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(
        product_dir,
        slug="feature-a",
        body="## Propósito\n\nSee [[other]] and again [[other]].\n",
    )

    catalog, errors = generate_catalog(memory_dir)

    assert not errors
    assert catalog is not None
    feat = catalog["features"][0]
    assert feat["depends_on"].count("other") == 1


# ---------------------------------------------------------------------------
# Test: index.md generation
# ---------------------------------------------------------------------------


def test_generate_index_md_has_expected_sections(tmp_path: Path) -> None:
    """generate_index_md produces a markdown TOC grouped by area (F-75).

    Grouping is by the atom's parent directory under product/ — NOT by the
    frontmatter category: two atoms sharing category land in different sections
    when they live in different area subdirs.
    """
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="feat-a")
    sdd_dir = product_dir / "sdd"
    sdd_dir.mkdir()
    _make_product_atom(sdd_dir, slug="feat-b")

    catalog, errors = generate_catalog(memory_dir)
    assert not errors
    assert catalog is not None

    index_md = generate_index_md(catalog)

    assert "feat-a" in index_md
    assert "feat-b" in index_md
    assert "## Features by area" in index_md
    assert "### product" in index_md
    assert "### sdd" in index_md


# ---------------------------------------------------------------------------
# Test: catalog.json written to disk
# ---------------------------------------------------------------------------


def test_catalog_json_written_to_disk(tmp_path: Path) -> None:
    """main() writes a valid catalog.json to --out path."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="workspace-init")
    out_path = tmp_path / "output" / "catalog.json"

    code = main(
        [
            "--memory-dir",
            str(memory_dir),
            "--out",
            str(out_path),
        ]
    )

    assert code == 0, f"Expected exit 0, got {code}"
    assert out_path.exists(), "catalog.json should be written"

    catalog = json.loads(out_path.read_text(encoding="utf-8"))
    assert "features" in catalog
    assert len(catalog["features"]) == 1
    assert catalog["features"][0]["slug"] == "workspace-init"


def test_catalog_json_idempotent(tmp_path: Path) -> None:
    """Running generate_catalog twice produces the same features (modulo generated_at)."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="test-feature")

    catalog1, _ = generate_catalog(memory_dir)
    catalog2, _ = generate_catalog(memory_dir)

    assert catalog1 is not None
    assert catalog2 is not None
    # Features should be identical
    assert catalog1["features"] == catalog2["features"]


def test_index_md_written_to_disk(tmp_path: Path) -> None:
    """main() with --index-out writes an index.md file."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="test-feature")
    out_path = tmp_path / "catalog.json"
    index_out = tmp_path / "index.md"

    code = main(
        [
            "--memory-dir",
            str(memory_dir),
            "--out",
            str(out_path),
            "--index-out",
            str(index_out),
        ]
    )

    assert code == 0, f"Expected exit 0, got {code}"
    assert index_out.exists(), "index.md should be written"
    content = index_out.read_text(encoding="utf-8")
    assert "test-feature" in content


# ---------------------------------------------------------------------------
# Subprocess integration tests
# ---------------------------------------------------------------------------


def test_subprocess_valid_exits_zero(tmp_path: Path) -> None:
    """Script exits 0 for a directory with valid atoms."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="workspace-init")
    out_path = tmp_path / "catalog.json"

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--memory-dir",
            str(memory_dir),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0.\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert out_path.exists(), "catalog.json should be written"


def test_subprocess_missing_field_exits_one(tmp_path: Path) -> None:
    """Script exits 1 when product atom has missing required frontmatter."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)

    # Atom without 'title'
    content = (
        "---\n"
        "slug: bad-feature\n"
        # title missing
        "category: product\n"
        "tldr: Short.\n"
        "summary: Summary.\n"
        "tags: []\n"
        "agent_tier: self-pull\n"
        "token_estimate: 50\n"
        "last_updated: '2026-06-01'\n"
        "release_origin: test\n"
        "---\n\n## Propósito\n\nBody.\n"
    )
    (product_dir / "bad-feature.md").write_text(content, encoding="utf-8")
    out_path = tmp_path / "catalog.json"

    result = subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--memory-dir",
            str(memory_dir),
            "--out",
            str(out_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, (
        f"Expected exit 1.\nstdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
