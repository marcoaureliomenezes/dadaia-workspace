"""`fake_venv` builds the venv layout of the platform it is told, and the `python` in it runs."""

import sys
from pathlib import Path

import pytest
import typer

from dadaia_workspace.core.platform import PLATFORM
from tests.fixtures.stores import fake_venv
from tests.helpers.oslib import run as os_run


def test_fake_venv_is_a_venv_whose_python_is_the_base_interpreter(tmp_path: Path) -> None:
    python = fake_venv(tmp_path)
    assert python == tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / (
        f"python{PLATFORM.venv_exe_suffix}"
    )
    assert "home = " in (tmp_path / ".dadaia" / ".venv" / "pyvenv.cfg").read_text()
    code = "import sys; print(sys.prefix, sys._base_executable)"
    prefix, base = os_run([str(python), "-c", code]).stdout.split()
    assert Path(prefix) == tmp_path / ".dadaia" / ".venv"
    assert Path(base).resolve() == Path(sys._base_executable).resolve()
    assert not (tmp_path / ".dadaia" / ".venv" / PLATFORM.venv_scripts_dir / "pip").exists()


def test_fake_venv_python_runs_on_this_platform(tmp_path: Path) -> None:
    python = fake_venv(tmp_path)
    ran = os_run([str(python), "-c", "print(6 * 7)"])
    assert ran.stdout.strip() == "42"


def test_fake_venv_cli_is_the_installers_launcher_and_starts_without_a_shell(
    tmp_path: Path,
) -> None:
    fake_venv(tmp_path, cli=True)
    cli = (
        tmp_path / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )
    ran = os_run([str(cli), "--help"])
    assert ran.returncode == 0
    assert "Usage" in ran.stdout


def test_fake_venv_cli_source_is_started_as_a_launcher(tmp_path: Path) -> None:
    fake_venv(tmp_path, cli="#!python\nimport sys\nprint('hi', *sys.argv[1:])\n")
    cli = (
        tmp_path / ".dadaia/.venv" / PLATFORM.venv_scripts_dir / f"dadaia{PLATFORM.venv_exe_suffix}"
    )
    ran = os_run([str(cli), "a"])
    assert ran.stdout.strip() == "hi a"


@pytest.mark.parametrize("name", ["ws", "a workspace"])
def test_fake_venv_cli_entrypoint_is_bound_to_the_venv_python_at_any_path(
    tmp_path: Path, name: str
) -> None:
    root = tmp_path / name
    root.mkdir()
    python = fake_venv(root, cli="#!python\nimport sys\nprint(sys.executable)\n")
    cli = python.with_name(f"dadaia{PLATFORM.venv_exe_suffix}")
    ran = os_run([str(cli)])
    assert ran.stdout.strip() == str(python)


def test_fake_venv_pth_puts_the_running_packages_on_the_venv_python(tmp_path: Path) -> None:
    python = fake_venv(tmp_path, pth=True)
    code = "import typer; print(typer.__file__)"
    ran = os_run([str(python), "-c", code])
    assert Path(ran.stdout.strip()) == Path(typer.__file__)
    bare = os_run([str(fake_venv(tmp_path / "bare")), "-c", code])
    assert bare.returncode != 0
