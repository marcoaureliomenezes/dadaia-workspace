"""Unit tests for ``dadaia memory catalog generate`` CLI command (T-MCE-03)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands.memory import app

# ---------------------------------------------------------------------------
# Shared helpers and fixtures
# ---------------------------------------------------------------------------

_INDEX_HTML_VALID = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Product</title></head>
<body>
<h1>Product Memory — test-repo</h1>
<ol class="catalog">
  <li><a href="workspace-init.html">workspace-init</a><span class="desc">— entry point.</span></li>
  <li><a href="context-management.html">context-management</a><span class="desc">— lifecycle.</span></li>
  <li><a href="specs-doctor.html">specs-doctor</a><span class="desc">— validation checks.</span></li>
</ol>
</body>
</html>
"""


def _make_specs_dir(tmp_path: Path, index_html: str = _INDEX_HTML_VALID) -> Path:
    """Create a minimal specs/ directory with the given index.html."""
    specs = tmp_path / "specs"
    product_dir = specs / "memory" / "product"
    product_dir.mkdir(parents=True)
    (product_dir / "index.html").write_text(index_html, encoding="utf-8")
    return specs


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# T-MCE-03-1: Successful generation
# ---------------------------------------------------------------------------


class TestCatalogGenerateSuccess:
    def test_exits_zero_on_success(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Output:\n{result.output}"
        )

    def test_catalog_json_created(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        catalog_path = specs / "memory" / "product" / "catalog.json"
        assert catalog_path.exists(), "catalog.json was not created"

    def test_output_mentions_catalog_path(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert "catalog.json" in result.output

    def test_output_is_valid_json(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        catalog_path = specs / "memory" / "product" / "catalog.json"
        parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
        assert "features" in parsed

    def test_generates_correct_entry_count(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        catalog_path = specs / "memory" / "product" / "catalog.json"
        parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
        assert len(parsed["features"]) == 3

    def test_output_mentions_feature_count(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert "3" in result.output, (
            f"Expected feature count '3' in output; got:\n{result.output}"
        )

    def test_each_entry_has_required_fields(self, runner: CliRunner, tmp_path: Path) -> None:
        required = {"rank", "slug", "title", "summary", "path", "tags", "depends_on"}
        specs = _make_specs_dir(tmp_path)
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        catalog_path = specs / "memory" / "product" / "catalog.json"
        parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
        for entry in parsed["features"]:
            missing = required - set(entry.keys())
            assert not missing, f"Entry missing fields {missing}: {entry}"


# ---------------------------------------------------------------------------
# T-MCE-03-2: Missing specs_dir → clear error
# ---------------------------------------------------------------------------


class TestCatalogGenerateMissingSpecsDir:
    def test_exits_nonzero_for_nonexistent_path(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        nonexistent = tmp_path / "does" / "not" / "exist"
        result = runner.invoke(
            app, ["catalog", "generate", "--specs-dir", str(nonexistent)]
        )
        assert result.exit_code != 0, (
            f"Expected non-zero exit for missing specs_dir; got 0. Output:\n{result.output}"
        )

    def test_error_output_for_nonexistent_path(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        nonexistent = tmp_path / "does" / "not" / "exist"
        result = runner.invoke(
            app, ["catalog", "generate", "--specs-dir", str(nonexistent)]
        )
        # Either exit_code != 0 or error in output
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_exits_nonzero_when_index_html_absent(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        # Directory exists but no index.html inside memory/product/
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert result.exit_code != 0, (
            f"Expected non-zero exit when index.html is missing; "
            f"got 0. Output:\n{result.output}"
        )

    def test_error_message_includes_index_html(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs = tmp_path / "specs"
        specs.mkdir()
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        # Either the output mentions the missing file or the exception is printed
        combined = result.output + (str(result.exception) if result.exception else "")
        assert "index.html" in combined or result.exit_code != 0


# ---------------------------------------------------------------------------
# T-MCE-03-3: Idempotent re-run overwrites cleanly
# ---------------------------------------------------------------------------


class TestCatalogGenerateIdempotent:
    def test_second_call_overwrites_cleanly(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs = _make_specs_dir(tmp_path)
        # First call
        r1 = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert r1.exit_code == 0
        catalog_path = specs / "memory" / "product" / "catalog.json"
        first_features = json.loads(catalog_path.read_text(encoding="utf-8"))["features"]

        # Second call
        r2 = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert r2.exit_code == 0
        second_features = json.loads(catalog_path.read_text(encoding="utf-8"))["features"]

        # Feature list must be identical (same slugs, same rank, same paths)
        assert len(first_features) == len(second_features)
        for f1, f2 in zip(first_features, second_features, strict=True):
            assert f1["slug"] == f2["slug"]
            assert f1["rank"] == f2["rank"]
            assert f1["path"] == f2["path"]

    def test_second_call_exits_zero(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        r2 = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert r2.exit_code == 0

    def test_output_json_is_valid_after_overwrite(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        specs = _make_specs_dir(tmp_path)
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        catalog_path = specs / "memory" / "product" / "catalog.json"
        parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
        assert isinstance(parsed["features"], list)
        assert len(parsed["features"]) == 3
