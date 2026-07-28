"""A lifecycle workflow must not run on a context the operator took out of service.

Bug ``r16-lifecycle-allows-dead-context`` (consumer-side validator, R16/PRIORITY-1A):
after ``context alive`` failed for an explicit DEAD context, ``backlog-definition`` still
dispatched and completed. A DEAD context is a deliberate decision — its specs tree may be
un-materialized, stale or archived — so authoring into it produces work in a place nobody
is watching, and the operator is told it succeeded.

The refusal is scoped: an UNREGISTERED context is deliberately not refused, because
``resolve_context_for_cli`` has a documented terminal fallback to the self-hosting slug
for a workspace with nothing registered. Only a context that IS registered and IS dead is
refused — otherwise a bare verb invocation would start erroring.
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
_CTX = "deadctx"
_REPO = "deadrepo"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
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
    monkeypatch.setenv("DADAIA_SESSION_ID", "dead-session")
    created = _runner.invoke(app, ["context", "create", _CTX, "--repo", _REPO, "--url", str(repo)])
    assert created.exit_code == 0, created.output
    return tmp_path


def _backlog(run_id: str):
    return _runner.invoke(
        app,
        [
            "lifecycle",
            "backlog-definition",
            "--context",
            _CTX,
            "--release-id",
            "v0.1.0",
            "--run-id",
            run_id,
            "--harness",
            "fake",
            "--demand",
            "x",
        ],  # fmt: skip
    )


def test_a_dead_context_is_refused_with_the_command_that_revives_it(workspace: Path) -> None:
    result = _backlog("bd-dead")

    assert result.exit_code != 0, (
        "backlog-definition authored into a context the operator had taken out of "
        f"service. Output:\n{result.output}"
    )
    # CliRunner surfaces a raised DadaiaError on .exception; the real CLI renders it as a
    # clean "Error: ..." line (verified by hand). Read both so the test asserts the
    # MESSAGE, not the transport.
    rendered = result.output + str(result.exception or "")
    assert "DEAD" in rendered, rendered
    assert f"dadaia context alive {_CTX}" in rendered, "the refusal must say how to fix it"


def test_an_alive_context_still_runs(workspace: Path) -> None:
    """Guard: the refusal must not become a refusal of everything."""
    assert _runner.invoke(app, ["context", "alive", _CTX]).exit_code == 0
    result = _backlog("bd-alive")
    assert result.exit_code == 0, result.output
