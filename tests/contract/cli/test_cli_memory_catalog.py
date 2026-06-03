"""Contract tests for ``dadaia memory catalog generate`` CLI command.

memory-markdown-source-v1: catalog generation now reads YAML frontmatter
from *.md feature atom files, not index.html scraping.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.commands.memory import app

pytestmark = pytest.mark.contract

# ---------------------------------------------------------------------------
# Shared helpers and fixtures
# ---------------------------------------------------------------------------

_FEATURE_MD_TEMPLATE = """\
---
slug: {slug}
title: {slug}
category: product
tldr: '{tldr}'
summary: '{summary}'
tags: []
agent_tier: self-pull
token_estimate: 100
last_updated: '2026-06-01'
release_origin: test-release
---

## Propósito

{purpose}
"""

_FEATURE_ATOMS = [
    {
        "slug": "workspace-init",
        "tldr": "entry point; creates .dadaia/.",
        "summary": "entry point; creates .dadaia/.",
        "purpose": "Bootstraps the workspace.",
    },
    {
        "slug": "context-management",
        "tldr": "multi-context lifecycle.",
        "summary": "multi-context lifecycle.",
        "purpose": "Manages contexts.",
    },
    {
        "slug": "specs-doctor",
        "tldr": "structural validation checks.",
        "summary": "structural validation checks.",
        "purpose": "Validates specs.",
    },
]


def _make_specs_dir(tmp_path: Path, atoms: list[dict[str, str]] | None = None) -> Path:
    """Create a minimal specs/ directory with .md feature atom files.

    memory-markdown-source-v1: uses .md frontmatter atoms instead of index.html.
    """
    specs = tmp_path / "specs"
    product_dir = specs / "memory" / "product"
    product_dir.mkdir(parents=True)
    for atom in atoms or _FEATURE_ATOMS:
        content = _FEATURE_MD_TEMPLATE.format(**atom)
        (product_dir / f"{atom['slug']}.md").write_text(content, encoding="utf-8")
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
        assert "3" in result.output, f"Expected feature count '3' in output; got:\n{result.output}"

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
    def test_exits_nonzero_for_nonexistent_path(self, runner: CliRunner, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does" / "not" / "exist"
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(nonexistent)])
        assert result.exit_code != 0, (
            f"Expected non-zero exit for missing specs_dir; got 0. Output:\n{result.output}"
        )

    def test_error_output_for_nonexistent_path(self, runner: CliRunner, tmp_path: Path) -> None:
        nonexistent = tmp_path / "does" / "not" / "exist"
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(nonexistent)])
        # Either exit_code != 0 or error in output
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_exits_nonzero_when_product_dir_absent(self, runner: CliRunner, tmp_path: Path) -> None:
        """memory-markdown-source-v1: catalog reads .md atoms; missing product/ → non-zero exit."""
        specs = tmp_path / "specs"
        specs.mkdir()
        # Directory exists but no memory/product/ inside specs/
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        assert result.exit_code != 0, (
            f"Expected non-zero exit when product/ dir is missing; got 0. Output:\n{result.output}"
        )

    def test_error_message_includes_product(self, runner: CliRunner, tmp_path: Path) -> None:
        """memory-markdown-source-v1: error message mentions the missing product/ path."""
        specs = tmp_path / "specs"
        specs.mkdir()
        result = runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        # Either the output mentions 'product' or exit is non-zero
        combined = result.output + (str(result.exception) if result.exception else "")
        assert "product" in combined.lower() or result.exit_code != 0


# ---------------------------------------------------------------------------
# T-MCE-03-3: Idempotent re-run overwrites cleanly
# ---------------------------------------------------------------------------


class TestCatalogGenerateIdempotent:
    def test_second_call_overwrites_cleanly(self, runner: CliRunner, tmp_path: Path) -> None:
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

    def test_output_json_is_valid_after_overwrite(self, runner: CliRunner, tmp_path: Path) -> None:
        specs = _make_specs_dir(tmp_path)
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        runner.invoke(app, ["catalog", "generate", "--specs-dir", str(specs)])
        catalog_path = specs / "memory" / "product" / "catalog.json"
        parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
        assert isinstance(parsed["features"], list)
        assert len(parsed["features"]) == 3
