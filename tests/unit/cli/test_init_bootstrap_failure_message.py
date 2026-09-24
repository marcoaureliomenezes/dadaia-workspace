"""init venv-bootstrap failure must be actionable, never a traceback (validation-028).

An unpublished candidate wheel is THE consumer-validation scenario: the workspace venv
bootstrap exploded with a raw CalledProcessError traceback, never naming the
DADAIA_BOOTSTRAP_PACKAGE escape hatch that exists for exactly this case. (The index pin
it used to explode on is gone — bug
init-venv-installs-index-version-not-running-distribution — but the refusal it left
behind is the same promise: actionable, never a traceback.)

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

    # The validation-028 shape, restated for the post-index bootstrap (bug
    # init-venv-installs-index-version-not-running-distribution): a consumer running an
    # installed distribution that cannot be re-packed. There is no index pin to fall
    # back to any more, so the refusal itself must name the escape hatch.
    site = tmp_path / "site-packages" / "dadaia_workspace"
    site.mkdir(parents=True)
    (site / "__init__.py").write_text("")
    monkeypatch.setattr(pe.dadaia_workspace, "__file__", str(site / "__init__.py"))
    monkeypatch.setattr(pe.metadata, "version", lambda name: "9.9.9")
    monkeypatch.setattr(pe, "repack_installed_wheel", lambda dest_dir, dist=None: None)

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
    result = _runner.invoke(app, ["init", "ws", "--harness", "claude"])
    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "DADAIA_BOOTSTRAP_PACKAGE" in result.output


def test_install_failure_names_pypi_and_shows_whole_lines(tmp_path: Path, monkeypatch) -> None:
    """Bug init-offline-error-truncated-mid-string: the refusal says the venv resolves
    from PyPI (network required) and quotes whole installer lines, never a cut one."""
    from dadaia_workspace.core.platform import PLATFORM

    (tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir).mkdir(parents=True)
    wheel = tmp_path / "dadaia_workspace-9.9.9-py3-none-any.whl"
    wheel.write_bytes(b"")
    monkeypatch.setenv("DADAIA_BOOTSTRAP_PACKAGE", str(wheel))
    monkeypatch.setattr(
        pe.VenvPythonEnvironmentManager, "version_change", lambda s, r: (None, "9", "install")
    )
    monkeypatch.setattr(
        pe.VenvPythonEnvironmentManager, "_assert_child_interpreter_version", lambda s, r: None
    )
    lines = [
        f"WARNING: Retrying (Retry(total={n}, connect=None, read=None, status=None)) " + "x" * 60
        for n in range(9)
    ]
    lines.append("ERROR: Could not find a version that satisfies the requirement typer")

    def _boom(cmd, check=False, **kwargs):
        raise subprocess.CalledProcessError(1, cmd, stderr="\n".join(lines))

    monkeypatch.setattr(pe.subprocess, "run", _boom)
    with pytest.raises(pe.WorkspaceVenvBootstrapError) as exc:
        _REAL_ENSURE(pe.VenvPythonEnvironmentManager(), str(tmp_path))
    message = str(exc.value)
    assert "PyPI" in message and "network" in message
    assert lines[-1] in message
    quoted = message.split("Installer output:\n", 1)[1].splitlines()
    assert all(line in lines for line in quoted), quoted
