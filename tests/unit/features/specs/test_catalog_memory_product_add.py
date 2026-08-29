"""Unit tests for memory product atom creation.

Moved verbatim from the retired ``features.spec_artifacts.memory`` (v0.5.1 K4): the
writer now lives in ``features.specs.catalog`` alongside the catalog generator it
feeds — the package existed only to dodge a features -> features cross-feature edge
that never applied to this writer (both live in ``features/specs/`` now).

Bug memory-product-add-writes-a-flat-atom-path-outside-the-canon-area-layout: the
writer used to mint ``memory/product/<slug>.md`` (flat) while the v6 canon (and the
live tree) place every atom under ``memory/product/<area>/<slug>.md`` — a shape
``canon.scaffold_entry`` refuses outright. ``memory_product_add`` now takes a
required ``area`` and validates the resulting path through
``canon.is_canon_path`` — the SAME decider ``doctor``/the pre-push gate use, never a
second, hand-kept area regex.

Intent: CONTRACT — bug memory-product-add-writes-a-flat-atom-path-outside-the-canon-area-layout
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.canon import is_canon_path
from dadaia_workspace.features.specs.catalog import (
    MemoryProductAddResult,
    _build_feature_md,
    memory_product_add,
)


def _scaffold_dir(tmp_path: Path) -> Path:
    scaffold = tmp_path / "scaffold"
    scaffold.mkdir()
    (scaffold / "feature.md").write_text(
        "\n".join(
            [
                "---",
                "slug: SLUG_PLACEHOLDER",
                "title: TITLE_PLACEHOLDER",
                "---",
                "",
                "# TITLE_PLACEHOLDER",
            ]
        ),
        encoding="utf-8",
    )
    return scaffold


def test_memory_product_add_writes_the_canon_nested_area_path(tmp_path: Path) -> None:
    """The regression test for the bug: the written path must be
    memory/product/<area>/<slug>.md AND pass the one canon decider
    (canon.is_canon_path) — never a flat memory/product/<slug>.md."""
    specs = tmp_path / "specs"
    scaffold = _scaffold_dir(tmp_path)

    result = memory_product_add(specs, "alpha", area="platform", scaffold_dir=scaffold)

    assert result.feature_html == specs / "memory" / "product" / "platform" / "alpha.md"
    rel = result.feature_html.relative_to(specs).as_posix()
    assert is_canon_path(rel), f"{rel!r} must be canon-conformant (v6 area layout)"


def test_memory_product_add_creates_markdown_atom_and_sorted_slug_index(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    scaffold = _scaffold_dir(tmp_path)

    memory_product_add(specs, "zebra", area="platform", scaffold_dir=scaffold)
    result = memory_product_add(specs, "alpha", area="platform", scaffold_dir=scaffold)

    assert isinstance(result, MemoryProductAddResult)
    assert result.created_feature is True
    assert result.feature_html == specs / "memory" / "product" / "platform" / "alpha.md"
    assert result.slug_entries == ["alpha", "zebra"]
    assert result.feature_html.read_text(encoding="utf-8").startswith("---\n")


def test_slug_entries_span_every_area(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    scaffold = _scaffold_dir(tmp_path)

    memory_product_add(specs, "zebra", area="platform", scaffold_dir=scaffold)
    result = memory_product_add(specs, "alpha", area="harness", scaffold_dir=scaffold)

    assert result.slug_entries == ["alpha", "zebra"]


def test_invalid_area_is_refused(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    scaffold = _scaffold_dir(tmp_path)

    for bad_area in ("", "Bad", "1bad", "bad area", "bad/area"):
        with pytest.raises(ValueError):
            memory_product_add(specs, "payments", area=bad_area, scaffold_dir=scaffold)


def test_placeholders_idempotence_and_invalid_slug(tmp_path: Path) -> None:
    """Canonical placeholder substitution, idempotent re-add (no dup on existing atom),
    and invalid slugs raise ValueError with the shared regex message."""
    scaffold = _scaffold_dir(tmp_path)
    content = _build_feature_md("payment-links", "2026-06-03", scaffold)
    assert "slug: payment-links" in content
    assert "title: Payment Links" in content
    assert "release_origin" not in content
    assert "last_updated" not in content
    assert "SLUG_PLACEHOLDER" not in content
    assert "TITLE_PLACEHOLDER" not in content

    specs = tmp_path / "specs"
    first = memory_product_add(specs, "payments", area="platform", scaffold_dir=scaffold)
    second = memory_product_add(specs, "payments", area="platform", scaffold_dir=scaffold)
    assert first.created_feature is True
    assert second.created_feature is False
    assert second.feature_html == first.feature_html
    assert second.slug_entries == ["payments"]

    for bad_slug in ("", "1bad", "Bad", "bad_slug", "-bad"):
        with pytest.raises(ValueError, match=re.escape("Must match ^[a-z][a-z0-9-]+$")):
            memory_product_add(specs, bad_slug, area="platform", scaffold_dir=scaffold)
