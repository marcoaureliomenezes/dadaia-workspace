"""`fake_venv` builds the venv layout of the platform it is told, and the `python` in it runs."""

import subprocess
from pathlib import Path

import pytest

from dadaia_workspace.core.platform import PLATFORM, Capabilities
from tests.fixtures.stores import fake_venv


@pytest.mark.parametrize(
    ("platform", "relative"),
    [("linux", "bin/python"), ("darwin", "bin/python"), ("win32", "Scripts/python.exe")],
)
def test_fake_venv_lays_python_out_as_the_platform_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str, relative: str
) -> None:
    monkeypatch.setattr("tests.fixtures.stores.PLATFORM", Capabilities.detect(platform))
    python = fake_venv(tmp_path)
    assert python == tmp_path / ".dadaia" / ".venv" / relative
    assert python.is_file()
    assert not python.is_symlink()
    assert (tmp_path / ".dadaia" / ".venv" / "pyvenv.cfg").read_text().startswith("home = ")


def test_fake_venv_python_runs_on_this_platform(tmp_path: Path) -> None:
    python = fake_venv(tmp_path)
    run = subprocess.run([str(python), "-c", "print(6 * 7)"], capture_output=True, text=True)
    assert run.stdout.strip() == "42"


def test_fake_venv_cli_is_the_installers_launcher_and_starts_without_a_shell(
    tmp_path: Path,
) -> None:
    fake_venv(tmp_path, cli=True)
    cli = (
        tmp_path / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )
    run = subprocess.run([str(cli), "--help"], capture_output=True, text=True)
    assert run.returncode == 0
    assert "Usage" in run.stdout


def test_fake_venv_cli_source_is_started_as_a_launcher(tmp_path: Path) -> None:
    fake_venv(tmp_path, cli="#!python\nimport sys\nprint('hi', *sys.argv[1:])\n")
    cli = (
        tmp_path / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )
    run = subprocess.run([str(cli), "a"], capture_output=True, text=True)
    assert run.stdout.strip() == "hi a"
