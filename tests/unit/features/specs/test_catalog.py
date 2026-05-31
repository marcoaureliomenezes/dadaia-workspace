"""Unit tests for dadaia_workspace.features.specs.catalog (T-MCE-01)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.specs.catalog import generate_catalog, write_catalog

# ---------------------------------------------------------------------------
# Fixtures: HTML fragments used across tests
# ---------------------------------------------------------------------------

_INDEX_HTML_3_ENTRIES = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Product</title>
</head>
<body>
<h1>Product Memory — test-project</h1>
<section id="catalog">
  <h2>Feature catalog</h2>
  <ol class="catalog">
    <li><a href="workspace-init.html">workspace-init</a><span class="desc">— entry point; creates .dadaia/.</span></li>
    <li><a href="context-management.html">context-management</a><span class="desc">— multi-context lifecycle.</span></li>
    <li><a href="specs-doctor.html">specs-doctor</a><span class="desc">— structural validation checks.</span></li>
  </ol>
</section>
</body>
</html>
"""

_INDEX_HTML_EMPTY_CATALOG = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Product</title></head>
<body>
<h1>Product Memory</h1>
<ol class="catalog">
</ol>
</body>
</html>
"""

_INDEX_HTML_NO_CATALOG_OL = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Product</title></head>
<body>
<h1>Product Memory</h1>
<ol>
  <li><a href="workspace-init.html">workspace-init</a></li>
</ol>
</body>
</html>
"""

_FEATURE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Feature</title></head>
<body><h1>Feature</h1><p>Content.</p></body>
</html>
"""


def _make_specs_dir(tmp_path: Path, index_html: str = _INDEX_HTML_3_ENTRIES) -> Path:
    """Create a minimal specs/ directory with the given index.html content."""
    specs = tmp_path / "specs"
    product_dir = specs / "memory" / "product"
    product_dir.mkdir(parents=True)
    (product_dir / "index.html").write_text(index_html, encoding="utf-8")
    return specs


# ---------------------------------------------------------------------------
# T-MCE-01-1: Valid parse produces N entries with all 7 required fields
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
        # Must parse as a valid datetime
        parsed = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        assert parsed is not None

    def test_context_is_parent_directory_name(self, tmp_path: Path) -> None:
        # Create specs inside a known directory name
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        specs = project_dir / "specs"
        (specs / "memory" / "product").mkdir(parents=True)
        (specs / "memory" / "product" / "index.html").write_text(
            _INDEX_HTML_3_ENTRIES, encoding="utf-8"
        )
        catalog = generate_catalog(specs)
        assert catalog["context"] == "my-project"

    def test_three_entries_parsed(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        assert len(catalog["features"]) == 3

    def test_each_entry_has_all_seven_fields(self, tmp_path: Path) -> None:
        required_fields = {"rank", "slug", "title", "summary", "path", "tags", "depends_on"}
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

    def test_tags_and_depends_on_are_empty_lists(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        for entry in features:
            assert entry["tags"] == []
            assert entry["depends_on"] == []

    def test_result_is_json_serialisable(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        # Must not raise
        serialised = json.dumps(catalog)
        reparsed = json.loads(serialised)
        assert reparsed["features"][0]["rank"] == 1


# ---------------------------------------------------------------------------
# T-MCE-01-2: slug ↔ path stem consistency
# ---------------------------------------------------------------------------


class TestSlugPathConsistency:
    def test_slug_matches_href_stem(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        expected_slugs = ["workspace-init", "context-management", "specs-doctor"]
        for entry, expected_slug in zip(features, expected_slugs, strict=True):
            assert entry["slug"] == expected_slug

    def test_path_contains_slug(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        features = generate_catalog(specs)["features"]
        for entry in features:
            assert entry["path"].endswith(f"/{entry['slug']}.html"), (
                f"path {entry['path']!r} does not end with /{entry['slug']}.html"
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
# T-MCE-01-3: Missing index.html raises a clear error
# ---------------------------------------------------------------------------


class TestMissingIndexHtml:
    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        with pytest.raises(FileNotFoundError, match="index.html"):
            generate_catalog(specs)

    def test_error_message_includes_path(self, tmp_path: Path) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        with pytest.raises(FileNotFoundError) as exc_info:
            generate_catalog(specs)
        assert "index.html" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T-MCE-01-4: Empty catalog <ol> → empty features list
# ---------------------------------------------------------------------------


class TestEmptyCatalog:
    def test_empty_ol_produces_empty_features(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path, index_html=_INDEX_HTML_EMPTY_CATALOG)
        catalog = generate_catalog(specs)
        assert catalog["features"] == []

    def test_envelope_fields_still_present_when_empty(self, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path, index_html=_INDEX_HTML_EMPTY_CATALOG)
        catalog = generate_catalog(specs)
        assert "generated_at" in catalog
        assert "context" in catalog
        assert catalog["features"] == []

    def test_ol_without_catalog_class_is_ignored(self, tmp_path: Path) -> None:
        """An <ol> without class="catalog" must NOT be parsed."""
        specs = _make_specs_dir(tmp_path, index_html=_INDEX_HTML_NO_CATALOG_OL)
        catalog = generate_catalog(specs)
        # The plain <ol> (no catalog class) has one entry but should not be picked up
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
        assert reparsed["features"][0]["slug"] == "workspace-init"

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
        # Content should be identical (same catalog)
        text1 = out1.read_text(encoding="utf-8")
        # Re-generate to check content stability (generated_at may differ by a second)
        reparsed = json.loads(text1)
        assert reparsed["features"][0]["slug"] == "workspace-init"

    def test_no_trailing_commas_in_json(self, tmp_path: Path) -> None:
        """stdlib json.dumps never produces trailing commas — verify the file
        round-trips cleanly (no JSON parse errors)."""
        specs = _make_specs_dir(tmp_path)
        catalog = generate_catalog(specs)
        out_path = write_catalog(specs, catalog)
        # json.loads will raise if there are trailing commas or syntax errors
        parsed = json.loads(out_path.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict)
