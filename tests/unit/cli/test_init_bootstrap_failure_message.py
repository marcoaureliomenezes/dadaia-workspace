"""init venv-bootstrap failure must be actionable, never a traceback (validation-028).

An unpublished candidate wheel is THE consumer-validation scenario: the workspace venv
bootstrap pins `dadaia-workspace==<running version>` from PyPI and exploded with a raw
CalledProcessError traceback when that version is not published, never naming the
DADAIA_BOOTSTRAP_PACKAGE escape hatch that exists for exactly this case.

The conftest anti-disk-exhaustion backstop fakes ensure_workspace_venv globally, so the
seam is exercised directly (subprocess.run mocked, pre-existing bare venv so
interpreter resolution / creation are not in scope here) plus the CLI mapping.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.infrastructure import python_env as pe

_runner = CliRunner()

# Captured at import (collection) time, BEFORE the autouse conftest backstop replaces
# the method — this is the real seam under test.
_REAL_ENSURE = pe.VenvPythonEnvironmentManager.ensure_workspace_venv


def test_ensure_workspace_venv_raises_actionable_error(tmp_path: Path, monkeypatch) -> None:
    # Pre-existing bare venv (doctor VENV-1 repair shape): isolates this test to the
    # install-failure path under test, independent of venv creation / interpreter
    # resolution (each covered by their own dedicated tests in test_python_env.py).
    from dadaia_workspace.core.platform import PLATFORM

    (tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir).mkdir(parents=True)

    def _boom(cmd, check=False, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(pe.subprocess, "run", _boom)
    mgr = pe.VenvPythonEnvironmentManager()
    with pytest.raises(pe.WorkspaceVenvBootstrapError) as exc:
        _REAL_ENSURE(mgr, str(tmp_path))
    assert "DADAIA_BOOTSTRAP_PACKAGE" in str(exc.value)


def test_init_cli_maps_bootstrap_error_to_clean_exit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        pe.VenvPythonEnvironmentManager,
        "ensure_workspace_venv",
        lambda self, root: (_ for _ in ()).throw(
            pe.WorkspaceVenvBootstrapError(
                "workspace venv bootstrap failed installing 'dadaia-workspace==9.9.9'. "
                "point DADAIA_BOOTSTRAP_PACKAGE at the local wheel file and retry"
            )
        ),
        raising=True,
    )
    result = _runner.invoke(app, ["init", "--harness", "claude"])
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "DADAIA_BOOTSTRAP_PACKAGE" in result.output
