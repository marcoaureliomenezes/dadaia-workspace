"""Consistency contract — the two memory-catalog renderer implementations (v0.1.48 W3).

Hand-maintained pairing under contract: ``dadaia_workspace/features/specs/catalog.py``
(the ``dadaia memory catalog generate`` CLI path) and
``dadaia_workspace/public/scripts/generate-memory-catalog.py`` (the projected,
importless consumer-workspace fallback). Both read the same atom frontmatter and both
emit ``catalog.json`` + ``index.md``; they cannot import each other, so their output
shape is kept aligned by THIS contract instead of by convention.

Pinned invariants:

- **F-73 (bug memory-index-table-broken-gfm):** the rendered ``index.md`` table is a
  contiguous GFM block — header row, separator row, and first data row with NO blank
  line in between — for BOTH renderers.
- **F-84:** for the same atom tree the two implementations emit byte-identical
  ``features`` JSON (same fields, same order, same values) and the same
  ``generated_at`` timestamp shape (``YYYY-MM-DDTHH:MM:SSZ``); the rendered
  ``index.md`` is identical except for the tool named on the "re-run" line.
- **F-75:** every catalog entry carries ``area`` = the atom's parent directory name
  under ``product/`` (top-level ``product/`` files → ``"product"``), and ``index.md``
  sections group by area.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import types
from pathlib import Path

import pytest

from dadaia_workspace.features.specs import catalog as lib_catalog_mod

pytestmark = pytest.mark.contract

# ---------------------------------------------------------------------------
# Load the standalone script module (it is not importable as a package module)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "dadaia_workspace" / "public" / "scripts" / "generate-memory-catalog.py"

_spec = importlib.util.spec_from_file_location("generate_memory_catalog_contract", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_script_mod: types.ModuleType = importlib.util.module_from_spec(_spec)
# Never pollute dadaia_workspace/public/scripts/__pycache__/ (public-source hygiene):
# the loader decides on .pyc caching BEFORE the script's own in-module guard runs.
_prev_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    _spec.loader.exec_module(_script_mod)
finally:
    sys.dont_write_bytecode = _prev_dont_write_bytecode


# ---------------------------------------------------------------------------
# Fixture tree — atoms at product/ root AND inside <area>/ subdirs
# ---------------------------------------------------------------------------

_ATOM_TEMPLATE = """\
---
slug: {slug}
title: {slug}
category: product
tldr: 'tldr for {slug}.'
summary: 'summary for {slug}.'
tags: []
agent_tier: self-pull
token_estimate: 100
last_updated: '2026-07-01'
release_origin: v0.1.48
---

## Purpose

Body of {slug}. See [[{dep}]].
"""

#: (relative dir under product/, slug) — "" means directly under product/.
_FIXTURE_ATOMS: tuple[tuple[str, str], ...] = (
    ("", "root-atom"),
    ("sdd", "sdd-atom"),
    ("platform", "platform-atom"),
    ("platform", "second-platform-atom"),
)

_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _make_specs_tree(tmp_path: Path, context: str = "ctx-under-contract") -> Path:
    """Create <tmp>/<context>/specs/memory/product/... and return the specs dir."""
    specs = tmp_path / context / "specs"
    product = specs / "memory" / "product"
    for rel_dir, slug in _FIXTURE_ATOMS:
        atom_dir = product / rel_dir if rel_dir else product
        atom_dir.mkdir(parents=True, exist_ok=True)
        (atom_dir / f"{slug}.md").write_text(
            _ATOM_TEMPLATE.format(slug=slug, dep="root-atom"), encoding="utf-8"
        )
    return specs


def _both_catalogs(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Generate the catalog through BOTH implementations for the same tree."""
    specs = _make_specs_tree(tmp_path)
    lib_cat = lib_catalog_mod.generate_catalog(specs)
    script_cat, errors = _script_mod.generate_catalog(
        specs / "memory", context="ctx-under-contract"
    )
    assert not errors, f"standalone script reported errors: {errors}"
    assert script_cat is not None
    return lib_cat, script_cat


def _both_indexes(tmp_path: Path) -> tuple[str, str]:
    lib_cat, script_cat = _both_catalogs(tmp_path)
    return (
        lib_catalog_mod.render_index_md(lib_cat),
        _script_mod.generate_index_md(script_cat),
    )


# ---------------------------------------------------------------------------
# F-73 — the GFM table block is contiguous (no blank line inside the table)
# ---------------------------------------------------------------------------


def _assert_contiguous_gfm_tables(index_md: str, renderer: str) -> int:
    """Assert every table block is contiguous; return the number of tables found."""
    lines = index_md.split("\n")
    tables = 0
    for i, line in enumerate(lines):
        if line != "| slug | title | tldr |":
            continue
        tables += 1
        separator = lines[i + 1]
        assert re.fullmatch(r"\|[-| ]+\|", separator), (
            f"[{renderer}] header row must be immediately followed by the GFM "
            f"separator row, got: {separator!r}"
        )
        first_data = lines[i + 2]
        assert first_data.startswith("| `"), (
            f"[{renderer}] separator row must be immediately followed by the first "
            f"data row (bug memory-index-table-broken-gfm), got: {first_data!r}"
        )
        # No blank line anywhere inside the table block: walk until the block ends.
        j = i + 2
        while j < len(lines) and lines[j].startswith("|"):
            j += 1
        block = lines[i:j]
        assert all(row.strip() for row in block), (
            f"[{renderer}] blank line inside table block: {block!r}"
        )
    assert tables > 0, f"[{renderer}] no GFM table found in index.md"
    return tables


def test_lib_renderer_emits_contiguous_gfm_table(tmp_path: Path) -> None:
    lib_index, _ = _both_indexes(tmp_path)
    _assert_contiguous_gfm_tables(lib_index, "features/specs/catalog.py")


def test_script_renderer_emits_contiguous_gfm_table(tmp_path: Path) -> None:
    _, script_index = _both_indexes(tmp_path)
    _assert_contiguous_gfm_tables(script_index, "generate-memory-catalog.py")


# ---------------------------------------------------------------------------
# F-84 — identical features JSON (field order pinned) + timestamp shape
# ---------------------------------------------------------------------------


def test_both_implementations_emit_identical_features_json(tmp_path: Path) -> None:
    """json.dumps comparison pins values AND insertion (field) order."""
    lib_cat, script_cat = _both_catalogs(tmp_path)
    lib_features = json.dumps(lib_cat["features"], ensure_ascii=False, indent=2)
    script_features = json.dumps(script_cat["features"], ensure_ascii=False, indent=2)
    assert lib_features == script_features, (
        "features/specs/catalog.py and generate-memory-catalog.py diverge in the "
        "features they emit (field order, field set, or values) — F-84 regression"
    )
    assert lib_cat["context"] == script_cat["context"]


def test_neither_renderer_emits_agent_tier(tmp_path: Path) -> None:
    """v0.1.53 FR3 'drop': agent_tier is NOT emitted by either renderer.

    The fixture atoms still CARRY ``agent_tier`` in their frontmatter (the schema retains
    it as an optional/tolerated property until the CLOSURE strip), yet neither renderer may
    surface it in the generated catalog — the field has zero runtime consumers.
    """
    lib_cat, script_cat = _both_catalogs(tmp_path)
    for name, cat in (("lib", lib_cat), ("script", script_cat)):
        features = cat["features"]
        assert isinstance(features, list) and features
        for feat in features:
            assert isinstance(feat, dict)
            assert "agent_tier" not in feat, (
                f"[{name}] entry {feat.get('slug')!r} still emits 'agent_tier' — FR3 requires "
                "it dropped from catalog output"
            )


def test_both_renderers_tolerate_atom_without_agent_tier(tmp_path: Path) -> None:
    """v0.1.53 FR3 'tolerate': an atom missing agent_tier still generates cleanly.

    After the CLOSURE strip the atoms lose the field entirely; the renderers (frozen here in
    W3) must already tolerate its absence — no required-field error, byte-identical output.
    """
    specs = tmp_path / "no-tier" / "specs"
    product = specs / "memory" / "product"
    product.mkdir(parents=True)
    atom = _ATOM_TEMPLATE.format(slug="tierless-atom", dep="tierless-atom").replace(
        "agent_tier: self-pull\n", ""
    )
    (product / "tierless-atom.md").write_text(atom, encoding="utf-8")

    lib_cat = lib_catalog_mod.generate_catalog(specs)
    script_cat, errors = _script_mod.generate_catalog(specs / "memory", context="no-tier")
    assert not errors, f"standalone script rejected a tier-less atom: {errors}"
    assert script_cat is not None
    lib_features = json.dumps(lib_cat["features"], ensure_ascii=False, indent=2)
    script_features = json.dumps(script_cat["features"], ensure_ascii=False, indent=2)
    assert lib_features == script_features
    assert "agent_tier" not in lib_features


def test_both_implementations_emit_same_timestamp_shape(tmp_path: Path) -> None:
    lib_cat, script_cat = _both_catalogs(tmp_path)
    for name, cat in (("lib", lib_cat), ("script", script_cat)):
        ts = cat["generated_at"]
        assert isinstance(ts, str) and _TS_RE.fullmatch(ts), (
            f"[{name}] generated_at must be YYYY-MM-DDTHH:MM:SSZ, got: {ts!r}"
        )


def test_index_md_identical_modulo_rerun_tool_line(tmp_path: Path) -> None:
    """The two renderers differ ONLY on the tool named in the 're-run' line."""
    lib_index, script_index = _both_indexes(tmp_path)
    normalized_lib = lib_index.replace("`dadaia memory catalog generate`", "`<TOOL>`")
    normalized_script = script_index.replace("`generate-memory-catalog.py`", "`<TOOL>`")
    assert normalized_lib == normalized_script, (
        "index.md output diverges beyond the re-run tool name — F-84 regression"
    )


# ---------------------------------------------------------------------------
# F-75 — area derived from the parent directory; index groups by area
# ---------------------------------------------------------------------------


def test_every_entry_carries_area_matching_parent_dir(tmp_path: Path) -> None:
    lib_cat, script_cat = _both_catalogs(tmp_path)
    expected = {slug: (rel_dir or "product") for rel_dir, slug in _FIXTURE_ATOMS}
    for name, cat in (("lib", lib_cat), ("script", script_cat)):
        features = cat["features"]
        assert isinstance(features, list) and features
        for feat in features:
            assert isinstance(feat, dict)
            assert "area" in feat, f"[{name}] entry {feat.get('slug')!r} has no 'area'"
            assert feat["area"] == expected[feat["slug"]], (
                f"[{name}] {feat['slug']!r}: area {feat['area']!r} != parent dir "
                f"{expected[feat['slug']]!r}"
            )


def test_index_md_groups_sections_by_area(tmp_path: Path) -> None:
    lib_index, script_index = _both_indexes(tmp_path)
    for name, index_md in (("lib", lib_index), ("script", script_index)):
        for area in ("product", "sdd", "platform"):
            assert f"### {area}" in index_md, f"[{name}] missing '### {area}' area section"
        # Grouping is by area, not by the single frontmatter category bucket:
        # all fixture atoms share category=product, yet three sections must exist.
        assert index_md.count("### ") == 3, (
            f"[{name}] expected exactly 3 area sections, got:\n{index_md}"
        )


def test_area_does_not_touch_category(tmp_path: Path) -> None:
    """`category` stays sourced from frontmatter, untouched by area derivation."""
    lib_cat, _ = _both_catalogs(tmp_path)
    features = lib_cat["features"]
    assert isinstance(features, list)
    for feat in features:
        assert isinstance(feat, dict)
        assert feat["category"] == "product"
