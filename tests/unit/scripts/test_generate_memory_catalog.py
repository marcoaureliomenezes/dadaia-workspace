"""Unit tests for dadaia_workspace/public/scripts/generate-memory-catalog.py.

Relocated from tests/integration/scripts/test_generate_memory_catalog.py (T-7,
v0.1.75 plan-integration.md): these fns call the imported ``generate_catalog`` /
``generate_index_md`` / ``main`` functions directly, in-process — no subprocess, no
server — so they belong in the unit tier. The two real subprocess-exit-code fns and
the single end-to-end fn stay in tests/integration/scripts/test_generate_memory_catalog.py.

Coverage:
  - Empty product dir -> empty features list (exit 0)
  - Single atom -> catalog with 1 entry, correct shape
  - catalog top-level keys
  - Multiple atoms -> catalog with N entries, ranks 1..N
  - Missing required frontmatter field -> error, no catalog written
  - depends_on derived from [[slug]] wikilinks in body (present, absent, deduped)
  - index.md generated with correct TOC
  - catalog.json / index.md written to disk via main()
  - Idempotent: running twice produces same output (except generated_at timestamp)
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Locate + import the script module
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts" / "generate-memory-catalog.py"

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
    _spec.loader.exec_module(_catalog_mod)
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


def test_empty_dir_single_atom_shape_and_top_level_keys(tmp_path: Path) -> None:
    """generate_catalog on an empty product/ dir returns an empty features list; a single
    atom produces a catalog entry matching the expected shape; the catalog dict carries
    the required top-level keys."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)

    catalog, errors = generate_catalog(memory_dir)
    assert not errors, f"Unexpected errors: {errors}"
    assert catalog is not None
    assert catalog["features"] == []

    _make_product_atom(product_dir, slug="workspace-init")

    catalog2, errors2 = generate_catalog(memory_dir, context="my-workspace")

    assert not errors2, f"Unexpected errors: {errors2}"
    assert catalog2 is not None
    assert "generated_at" in catalog2
    assert catalog2["context"] == "my-workspace"
    assert "features" in catalog2
    features = catalog2["features"]
    assert len(features) == 1

    feat = features[0]
    assert feat["slug"] == "workspace-init"
    assert feat["title"] == "Test Feature"
    assert feat["category"] == "product"
    assert feat["area"] == "product", "top-level product/ atom must carry area='product'"
    assert feat["tldr"] == "Short description under 160 chars."
    assert feat["summary"] == "One-sentence summary."
    assert feat["tags"] == ["test"]
    # SPEC v0.4.2 FR2/GRILL D5: token_estimate is COMPUTED from the body, never read
    # from frontmatter — the fixture atom's frontmatter says 50 (_REQUIRED_FM), but the
    # default body ("## Propósito\n\nBody.\n" — 3 words) computes to round(3 * 1.35) = 4.
    assert feat["token_estimate"] == 4, (
        "token_estimate must be COMPUTED from the body (4), never the stale "
        f"frontmatter value (50) — got {feat['token_estimate']}"
    )
    # agent_tier is dropped from catalog output in v0.1.53 (FR3): the input frontmatter
    # still carries it (schema-tolerated), but the renderer must not surface it.
    assert "agent_tier" not in feat
    assert feat["rank"] == 1
    assert feat["depends_on"] == []
    assert "path" in feat
    assert feat["path"].endswith("workspace-init.md")


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
    slugs = [f["slug"] for f in features]
    assert slugs == sorted(slugs)
    ranks = [f["rank"] for f in features]
    assert ranks == [1, 2, 3]


def test_missing_required_field_returns_error(tmp_path: Path) -> None:
    """Missing a required frontmatter field causes generate_catalog to return errors."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)

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


@pytest.mark.parametrize(
    ("body", "extra_slugs", "target_slug", "expected"),
    [
        pytest.param(
            "## Propósito\n\nSee [[feature-b]] and [[feature-c]] for context.\n",
            ("feature-b", "feature-c"),
            "feature-a",
            {"feature-b", "feature-c"},
            id="from-wikilinks",
        ),
        pytest.param(None, (), "standalone", set(), id="empty-when-no-wikilinks"),
        pytest.param(
            "## Propósito\n\nSee [[other]] and again [[other]].\n",
            (),
            "feature-a",
            {"other"},
            id="deduplicates-wikilinks",
        ),
    ],
)
def test_depends_on_matrix(
    tmp_path: Path,
    body: str | None,
    extra_slugs: tuple[str, ...],
    target_slug: str,
    expected: set[str],
) -> None:
    """depends_on is derived from [[slug]] wikilinks in the body: populated, empty, deduped."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    if body is not None:
        _make_product_atom(product_dir, slug=target_slug, body=body)
    else:
        _make_product_atom(product_dir, slug=target_slug)
    for slug in extra_slugs:
        _make_product_atom(product_dir, slug=slug)

    catalog, errors = generate_catalog(memory_dir)

    assert not errors, f"Unexpected errors: {errors}"
    assert catalog is not None
    feat = next(f for f in catalog["features"] if f["slug"] == target_slug)
    assert set(feat["depends_on"]) == expected


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
    assert "## Catálogo de features" in index_md
    assert "### product" in index_md
    assert "### sdd" in index_md


def test_catalog_json_written_to_disk(tmp_path: Path) -> None:
    """main() writes a valid catalog.json to --out path."""
    memory_dir, product_dir = _make_memory_dir(tmp_path)
    _make_product_atom(product_dir, slug="workspace-init")
    out_path = tmp_path / "output" / "catalog.json"

    code = main(["--memory-dir", str(memory_dir), "--out", str(out_path)])

    assert code == 0, f"Expected exit 0, got {code}"
    assert out_path.exists(), "catalog.json should be written"

    import json

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
