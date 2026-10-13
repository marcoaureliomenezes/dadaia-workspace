"""`dadaia --version` / `-V` prints the version read from the fake dist-info, never from the code's own reader."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from tests.fixtures.provider_dist import install_fake_dist

_runner = CliRunner()


def test_version_flag_prints_distribution_version(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_dist(monkeypatch, "9.8.7")
    result = _runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "dadaia-workspace 9.8.7"
