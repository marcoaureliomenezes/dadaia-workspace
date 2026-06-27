"""Integration tests for ``dadaia backlog subjects`` (T-25-03, SPEC §3.4a).

Drives the real CLI via Typer's ``CliRunner`` over a fixture specs tree. The surface is
read-only: it lists live anchors and resolves a proposed ref, never writing a backlog file or
the alias map. All roots come from ``--specs-dir`` (injected), never cwd.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

pytestmark = pytest.mark.integration

runner = CliRunner()


def _build_fixture_specs(tmp_path: Path) -> Path:
    """A minimal specs tree + a sibling source root for code-anchor derivation."""
    specs = tmp_path / "specs"
    (specs / "backlog").mkdir(parents=True)
    (specs / "memory" / "product").mkdir(parents=True)
    (specs / "memory" / "product" / "catalog.json").write_text(
        json.dumps({"features": [{"slug": "alpha-feature"}]}), encoding="utf-8"
    )
    (specs / "memory" / "architecture.md").write_text(
        "# Arch\n\n## INV-fixture-rule\n", encoding="utf-8"
    )
    # A source tree the CLI will scan for code anchors.
    src = tmp_path / "dadaia_workspace"
    src.mkdir()
    (src / "sample.py").write_text("class Sample:\n    pass\n", encoding="utf-8")
    return specs


def test_backlog_subjects_lists_anchors(tmp_path: Path) -> None:
    specs = _build_fixture_specs(tmp_path)
    result = runner.invoke(
        app,
        [
            "backlog",
            "subjects",
            "--specs-dir",
            str(specs),
            "--source-root",
            str(tmp_path / "dadaia_workspace"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "alpha-feature" in result.output


def test_backlog_subjects_filter_kind(tmp_path: Path) -> None:
    specs = _build_fixture_specs(tmp_path)
    result = runner.invoke(
        app,
        [
            "backlog",
            "subjects",
            "--specs-dir",
            str(specs),
            "--source-root",
            str(tmp_path / "dadaia_workspace"),
            "--kind",
            "code",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "sample.py#Sample" in result.output
    # A catalog slug must NOT appear in a code-filtered listing.
    assert "alpha-feature" not in result.output


def test_backlog_subjects_resolve_resolved(tmp_path: Path) -> None:
    specs = _build_fixture_specs(tmp_path)
    result = runner.invoke(
        app,
        [
            "backlog",
            "subjects",
            "--specs-dir",
            str(specs),
            "--source-root",
            str(tmp_path / "dadaia_workspace"),
            "--resolve",
            "sample.py#Sample",
            "--kind",
            "code",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "RESOLVED" in result.output
    assert "sample.py#Sample" in result.output


def test_backlog_subjects_resolve_unresolved_exits_nonzero(tmp_path: Path) -> None:
    specs = _build_fixture_specs(tmp_path)
    result = runner.invoke(
        app,
        [
            "backlog",
            "subjects",
            "--specs-dir",
            str(specs),
            "--source-root",
            str(tmp_path / "dadaia_workspace"),
            "--resolve",
            "sample.py#Ghost",
            "--kind",
            "code",
        ],
    )
    assert result.exit_code != 0, result.output
    assert "UNRESOLVED" in result.output
    # Carries an actionable alias suggestion.
    assert "->" in result.output
