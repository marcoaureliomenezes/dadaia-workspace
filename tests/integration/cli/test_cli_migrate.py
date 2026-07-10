"""Integration tests for `dadaia migrate tree-v2` CLI command.

Merged per plan-integration.md (7 -> 1): dry-run no-write -> --yes moves
foundation+root SPEC -> second run noop. Deleted the missing-specs-dir and
nothing-to-migrate wording greps.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


@pytest.fixture()
def specs(tmp_path: Path) -> Path:
    """Return an empty specs/ directory."""
    s = tmp_path / "specs"
    s.mkdir()
    return s


def _make_foundation(specs_dir: Path) -> None:
    foundation = specs_dir / "foundation"
    foundation.mkdir(parents=True, exist_ok=True)
    (foundation / "SPEC.md").write_text("# Foundation\n", encoding="utf-8")


def _make_root_spec(specs_dir: Path) -> None:
    (specs_dir / "SPEC.md").write_text("# Root\n", encoding="utf-8")


def test_migrate_dry_run_then_yes_moves_both_then_second_run_noop(specs: Path) -> None:
    _make_foundation(specs)
    _make_root_spec(specs)

    dry_run_result = _runner.invoke(
        app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--dry-run"]
    )
    assert dry_run_result.exit_code == 0, dry_run_result.output
    assert "MOVE" in dry_run_result.output
    # filesystem unchanged
    assert (specs / "foundation").is_dir()
    assert (specs / "SPEC.md").is_file()

    first = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--yes"])
    assert first.exit_code == 0, first.output
    assert not (specs / "foundation").exists()
    assert not (specs / "SPEC.md").exists()
    legacy = specs / "releases" / "legacy"
    assert (legacy / "foundation").is_dir()
    assert (legacy / "SPEC.md").is_file()

    second = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--yes"])
    assert second.exit_code == 0, second.output
    assert "nothing" in second.output.lower()
