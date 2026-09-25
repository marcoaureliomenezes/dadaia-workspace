"""No test can resolve the workspace its runner happens to sit in.

Intent: CONTRACT — doctor-tests-walk-the-real-workspace-tmp-zone.

Owner: dd-software-engineer.

Every in-process CLI verb resolves its workspace by walking up from the cwd. The suite
runs from a checkout that usually lives INSIDE an operator instance, so a verb invoked
without an explicit workspace scanned that live instance (its TTL zones grew to 124k
files and the doctor tests timed out). The root conftest starts every test in an empty
directory; these tests pin that envelope.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.core.exceptions import WorkspaceNotInitializedError
from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

_REPO_ROOT = Path(__file__).resolve().parents[2]


def test_the_cwd_walk_resolves_no_workspace() -> None:
    with pytest.raises(WorkspaceNotInitializedError):
        resolve_workspace_root()


def test_a_test_starts_outside_the_checkout() -> None:
    assert not Path.cwd().resolve().is_relative_to(_REPO_ROOT)


def test_a_bare_doctor_finds_no_instance_to_scan() -> None:
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "No initialized workspace found" in result.output
