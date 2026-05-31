"""Integration tests for `dadaia migrate tree-v2` CLI command.

Tests use Typer's CliRunner on a real tmp_path filesystem.
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


# ---------------------------------------------------------------------------
# dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    def test_dry_run_shows_move_without_writing(self, specs: Path) -> None:
        _make_foundation(specs)
        _make_root_spec(specs)

        result = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "MOVE" in result.output
        # filesystem unchanged
        assert (specs / "foundation").is_dir()
        assert (specs / "SPEC.md").is_file()

    def test_dry_run_nothing_to_migrate(self, specs: Path) -> None:
        result = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "nothing" in result.output.lower() or "SKIP" in result.output


# ---------------------------------------------------------------------------
# --yes flag (skip confirmation)
# ---------------------------------------------------------------------------


class TestYesFlag:
    def test_moves_foundation_with_yes(self, specs: Path) -> None:
        _make_foundation(specs)

        result = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--yes"])

        assert result.exit_code == 0, result.output
        assert not (specs / "foundation").exists()
        assert (specs / "releases" / "legacy" / "foundation").is_dir()

    def test_moves_root_spec_with_yes(self, specs: Path) -> None:
        _make_root_spec(specs)

        result = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--yes"])

        assert result.exit_code == 0, result.output
        assert not (specs / "SPEC.md").exists()
        assert (specs / "releases" / "legacy" / "SPEC.md").is_file()

    def test_moves_both_with_yes(self, specs: Path) -> None:
        _make_foundation(specs)
        _make_root_spec(specs)

        result = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--yes"])

        assert result.exit_code == 0, result.output
        assert not (specs / "foundation").exists()
        assert not (specs / "SPEC.md").exists()
        legacy = specs / "releases" / "legacy"
        assert (legacy / "foundation").is_dir()
        assert (legacy / "SPEC.md").is_file()


# ---------------------------------------------------------------------------
# idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_second_run_is_noop(self, specs: Path) -> None:
        """Running migrate twice does not fail."""
        _make_foundation(specs)
        _make_root_spec(specs)

        first = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--yes"])
        assert first.exit_code == 0, first.output

        second = _runner.invoke(app, ["migrate", "tree-v2", "--specs-dir", str(specs), "--yes"])
        assert second.exit_code == 0, second.output
        # Second run should say "nothing to migrate"
        assert "nothing" in second.output.lower()


# ---------------------------------------------------------------------------
# error path
# ---------------------------------------------------------------------------


class TestErrorPath:
    def test_missing_specs_dir_exits_nonzero(self, tmp_path: Path) -> None:
        result = _runner.invoke(
            app,
            ["migrate", "tree-v2", "--specs-dir", str(tmp_path / "nonexistent")],
        )
        assert result.exit_code != 0
