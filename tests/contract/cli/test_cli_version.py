"""`dadaia --version` top-level flag (bug cli-missing-version-flag, F-01)."""

from __future__ import annotations

from importlib import metadata

from typer.testing import CliRunner

from dadaia_workspace.cli.main import app

_runner = CliRunner()


def test_version_flag_prints_distribution_version() -> None:
    result = _runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert metadata.version("dadaia-workspace") in result.output


def test_version_short_flag() -> None:
    result = _runner.invoke(app, ["-V"])
    assert result.exit_code == 0, result.output
    assert metadata.version("dadaia-workspace") in result.output
