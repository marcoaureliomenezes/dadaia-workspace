"""A preflight that blocks must print the command that unblocks it.

Bug ``r17-r20-preflight-block-missing-recovery`` (consumer-side validator, R17/R-20):
the lifecycle preflight printed ``BLOCKED preflight blocked: context is not bound`` and
stopped there. The remedy existed in the payload — every preflight block carries an
``operator_command`` — but the preflight has its OWN output path, so it never reached the
terminal.

This is the FIFTH report of one class: a remedy that exists and is not shown. The
structural ratchet added for the fourth report guarantees every ``BlockedState`` CARRIES
a command; it cannot guarantee every printer SHOWS it. This test covers the other half,
on the path a real operator hits first — an unbound context is the most common way to
meet the lifecycle.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.workspace.service import WorkspaceService
from dadaia_workspace.infrastructure.public_assets import FileSystemPublicAssetManager
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

pytestmark = pytest.mark.integration

_runner = CliRunner()
_CTX = "pfctx"
_REPO = "pfrepo"


@pytest.fixture
def alive_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    WorkspaceService(
        public_assets=FileSystemPublicAssetManager(),
        python_env=VenvPythonEnvironmentManager(),
    ).init(tmp_path)
    repo = tmp_path / "repos" / _REPO
    repo.mkdir(parents=True)
    for args in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
        ["commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DADAIA_SESSION_ID", "preflight-session")
    assert (
        _runner.invoke(
            app, ["context", "create", _CTX, "--repo", _REPO, "--url", str(repo)]
        ).exit_code
        == 0
    )
    assert _runner.invoke(app, ["context", "alive", _CTX]).exit_code == 0
    # Define a release first. Without one, the preflight now (correctly) reports the
    # UNDEFINED release before it ever looks at the binding — so a fixture with no release
    # would test a different block than this file is about.
    for args in (
        ["lifecycle", "backlog-definition", "--context", _CTX, "--release-id", "v0.1.0",
         "--run-id", "bd", "--harness", "fake", "--demand", "x"],
        ["lifecycle", "release-definition", "--context", _CTX, "--release-id", "v0.1.0",
         "--run-id", "rd", "--harness", "fake", "--backlog-run-id", "bd"],
    ):  # fmt: skip
        result = _runner.invoke(app, args)
        assert result.exit_code == 0, result.output
    return tmp_path


def test_an_unbound_preflight_block_prints_the_bind_command(alive_context: Path) -> None:
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--context",
            _CTX,
            "--release-id",
            "v0.1.0",
            "--run-id",
            "ir",
            "--harness",
            "fake",
        ],  # fmt: skip
    )

    assert result.exit_code != 0
    assert "not bound" in result.output
    assert "Recovery:" in result.output, (
        f"the preflight stopped the operator and kept the remedy to itself:\n{result.output}"
    )
    assert f"dadaia context bind {_CTX}" in result.output, result.output


def test_the_reason_is_not_printed_twice(alive_context: Path) -> None:
    """Repeating the reason under a Recovery heading trains the reader to skim."""
    result = _runner.invoke(
        app,
        [
            "lifecycle",
            "implementation-reviews",
            "--context",
            _CTX,
            "--release-id",
            "v0.1.0",
            "--run-id",
            "ir2",
            "--harness",
            "fake",
        ],  # fmt: skip
    )
    assert result.output.count("context is not bound") == 1, result.output
