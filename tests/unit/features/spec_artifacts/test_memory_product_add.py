"""Unit tests for memory product atom creation."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_artifacts.memory import (
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
                "release_origin: RELEASE_PLACEHOLDER",
                'last_updated: "2026-01-01"',
                "---",
                "",
                "# TITLE_PLACEHOLDER",
            ]
        ),
        encoding="utf-8",
    )
    return scaffold


def test_memory_product_add_creates_markdown_atom_and_sorted_slug_index(tmp_path: Path) -> None:
    specs = tmp_path / "specs"
    scaffold = _scaffold_dir(tmp_path)

    memory_product_add(specs, "zebra", scaffold_dir=scaffold)
    result = memory_product_add(specs, "alpha", scaffold_dir=scaffold)

    assert isinstance(result, MemoryProductAddResult)
    assert result.created_feature is True
    assert result.feature_html == specs / "memory" / "product" / "alpha.md"
    assert result.slug_entries == ["alpha", "zebra"]
    assert result.feature_html.read_text(encoding="utf-8").startswith("---\n")


def test_placeholders_idempotence_and_invalid_slug(tmp_path: Path) -> None:
    """Canonical placeholder substitution, idempotent re-add (no dup on existing atom),
    and invalid slugs raise ValueError with the shared regex message."""
    scaffold = _scaffold_dir(tmp_path)
    content = _build_feature_md("payment-links", "2026-06-03", scaffold)
    assert "slug: payment-links" in content
    assert "title: Payment Links" in content
    assert "release_origin: none" in content
    assert 'last_updated: "2026-06-03"' in content
    assert "SLUG_PLACEHOLDER" not in content
    assert "TITLE_PLACEHOLDER" not in content

    specs = tmp_path / "specs"
    first = memory_product_add(specs, "payments", scaffold_dir=scaffold)
    second = memory_product_add(specs, "payments", scaffold_dir=scaffold)
    assert first.created_feature is True
    assert second.created_feature is False
    assert second.feature_html == first.feature_html
    assert second.slug_entries == ["payments"]

    for bad_slug in ("", "1bad", "Bad", "bad_slug", "-bad"):
        with pytest.raises(ValueError, match=re.escape("Must match ^[a-z][a-z0-9-]+$")):
            memory_product_add(specs, bad_slug, scaffold_dir=scaffold)
