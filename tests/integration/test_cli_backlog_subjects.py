"""Integration tests for ``dadaia backlog subjects`` (T-25-03, SPEC §3.4a).

Drives the real CLI via Typer's ``CliRunner`` over a fixture specs tree. The surface is
read-only: it lists live anchors and resolves a proposed ref, never writing a backlog file or
the alias map. All roots come from ``--specs-dir`` (injected), never cwd.

Merged per plan-integration.md into one fn: list + kind filter + resolve RESOLVED +
resolve UNRESOLVED exit!=0 with alias suggestion (4 invocations, one fixture).
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
    src = tmp_path / "dadaia_workspace"
    src.mkdir()
    (src / "sample.py").write_text("class Sample:\n    pass\n", encoding="utf-8")
    return specs


def test_backlog_subjects_list_filter_and_resolve(tmp_path: Path) -> None:
    specs = _build_fixture_specs(tmp_path)
    source_root = tmp_path / "dadaia_workspace"

    list_result = runner.invoke(
        app,
        ["backlog", "subjects", "--specs-dir", str(specs), "--source-root", str(source_root)],
    )
    assert list_result.exit_code == 0, list_result.output
    assert "alpha-feature" in list_result.output

    filtered_result = runner.invoke(
        app,
        [
            "backlog",
            "subjects",
            "--specs-dir",
            str(specs),
            "--source-root",
            str(source_root),
            "--kind",
            "code",
        ],
    )
    assert filtered_result.exit_code == 0, filtered_result.output
    assert "sample.py#Sample" in filtered_result.output
    # A catalog slug must NOT appear in a code-filtered listing.
    assert "alpha-feature" not in filtered_result.output

    resolved_result = runner.invoke(
        app,
        [
            "backlog",
            "subjects",
            "--specs-dir",
            str(specs),
            "--source-root",
            str(source_root),
            "--resolve",
            "sample.py#Sample",
            "--kind",
            "code",
        ],
    )
    assert resolved_result.exit_code == 0, resolved_result.output
    assert "RESOLVED" in resolved_result.output
    assert "sample.py#Sample" in resolved_result.output

    unresolved_result = runner.invoke(
        app,
        [
            "backlog",
            "subjects",
            "--specs-dir",
            str(specs),
            "--source-root",
            str(source_root),
            "--resolve",
            "sample.py#Ghost",
            "--kind",
            "code",
        ],
    )
    assert unresolved_result.exit_code != 0, unresolved_result.output
    assert "UNRESOLVED" in unresolved_result.output
    # Carries an actionable alias suggestion.
    assert "->" in unresolved_result.output
