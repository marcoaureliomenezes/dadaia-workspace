"""VenvPythonEnvironmentManager — venv bootstrap installs the package (VENV-1 coherence).

Bug init-venv-never-installs-dadaia-workspace: ``ensure_workspace_venv`` used to create a
bare venv and bail when the dir existed, so ``.dadaia/.venv/bin/dadaia`` never existed and
doctor VENV-1 was unfixable by its own remediation (re-running init).

The suite-wide conftest backstop no-ops ``ensure_workspace_venv`` (no real venvs in
tests), so the REAL method is captured at import time — before the autouse monkeypatch
fires — and exercised here with ``venv.create``/``subprocess.run`` stubbed.
"""

from pathlib import Path

import pytest

import dadaia_workspace.infrastructure.python_env as python_env_module
from dadaia_workspace.core.platform import PLATFORM
from dadaia_workspace.infrastructure.python_env import VenvPythonEnvironmentManager

# Captured at collection/import time — the conftest autouse monkeypatch only applies
# while a test runs, so this is the unpatched production method.
_REAL_ENSURE = VenvPythonEnvironmentManager.ensure_workspace_venv


class _Recorder:
    def __init__(self) -> None:
        self.venv_created: list[str] = []
        self.commands: list[list[str]] = []


@pytest.fixture()
def recorder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> _Recorder:
    rec = _Recorder()

    def fake_venv_create(path: str, with_pip: bool = False) -> None:
        rec.venv_created.append(path)
        (Path(path) / PLATFORM.venv_scripts_dir).mkdir(parents=True, exist_ok=True)

    def fake_run(cmd: list[str], check: bool = False) -> None:
        rec.commands.append(list(cmd))

    monkeypatch.setattr(python_env_module.venv, "create", fake_venv_create)
    monkeypatch.setattr(python_env_module.subprocess, "run", fake_run)
    # Undo the suite-wide no-op backstop for these tests only.
    monkeypatch.setattr(
        VenvPythonEnvironmentManager, "ensure_workspace_venv", _REAL_ENSURE, raising=True
    )
    return rec


def _entrypoint(ws: Path) -> Path:
    return (
        ws / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )


def test_fresh_bootstrap_creates_venv_and_installs_package(
    tmp_path: Path, recorder: _Recorder
) -> None:
    mgr = VenvPythonEnvironmentManager()
    result = mgr.ensure_workspace_venv(str(tmp_path))

    assert result == str(tmp_path / ".dadaia" / ".venv")
    assert recorder.venv_created == [str(tmp_path / ".dadaia" / ".venv")]
    assert len(recorder.commands) == 1
    cmd = recorder.commands[0]
    assert cmd[0] == mgr.pip_executable(str(tmp_path))
    assert cmd[1] == "install"
    # Running from the source checkout in this repo → editable install of that checkout.
    assert "--editable" in cmd
    assert (Path(cmd[-1]) / "pyproject.toml").is_file()


def test_existing_bare_venv_is_repaired_not_skipped(tmp_path: Path, recorder: _Recorder) -> None:
    """The exact state doctor VENV-1 flags: venv dir present, entrypoint missing."""
    (tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir).mkdir(parents=True)

    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))

    assert recorder.venv_created == []  # no re-create
    assert len(recorder.commands) == 1  # but the package IS installed


def test_healthy_venv_is_a_noop(tmp_path: Path, recorder: _Recorder) -> None:
    entry = _entrypoint(tmp_path)
    entry.parent.mkdir(parents=True)
    entry.write_text("#!stub")

    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path))

    assert recorder.venv_created == []
    assert recorder.commands == []


def test_install_spec_pins_version_when_not_a_source_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wheel-installed distribution (no pyproject.toml next to the package) → pinned pin."""
    site = tmp_path / "site-packages" / "dadaia_workspace"
    site.mkdir(parents=True)
    (site / "__init__.py").write_text("")
    monkeypatch.setattr(python_env_module.dadaia_workspace, "__file__", str(site / "__init__.py"))
    monkeypatch.setattr(python_env_module.metadata, "version", lambda name: "9.9.9")

    spec = VenvPythonEnvironmentManager()._install_spec()

    assert spec == "dadaia-workspace==9.9.9"


def test_local_candidate_wheel_overrides_index_pin_without_editable(
    tmp_path: Path, recorder: _Recorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    wheel = tmp_path / "dadaia_workspace-9.9.9-py3-none-any.whl"
    wheel.write_bytes(b"candidate")
    monkeypatch.setenv("DADAIA_BOOTSTRAP_PACKAGE", str(wheel))

    VenvPythonEnvironmentManager().ensure_workspace_venv(str(tmp_path / "workspace"))

    command = recorder.commands[0]
    assert command[-1] == str(wheel)
    assert "--editable" not in command
